"""Back up and merge public forks without discarding their conflicting edits.

Git operates on objects in an isolated bare repository. No downloaded hooks,
merge drivers, builds or project tests are executed; pushes are fast-forward only.
"""
from __future__ import annotations

import base64
import datetime as dt
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
import time
from typing import Any, Callable


SHA = re.compile(r"^[0-9a-f]{40}$")
NAME = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
MAX_CONFLICT_FILES = 1000
MAX_BLOB_BYTES = 2 * 1024 * 1024


class Deferred(Exception):
    def __init__(self, message: str, *, retryable: bool = False):
        self.retryable = retryable
        super().__init__(message)


def public_url(name: str) -> str:
    if not NAME.fullmatch(name):
        raise Deferred("無效的公開倉庫名稱")
    return f"https://github.com/{name}.git"


def ref_path(name: str, branch: str) -> str:
    from urllib.parse import quote
    return f"/repos/{name}/git/ref/heads/{quote(branch, safe='')}"


def ref_sha(value: dict[str, Any]) -> str:
    sha = value.get("object", {}).get("sha", "")
    if not SHA.fullmatch(sha):
        raise Deferred("無法確認遠端分支的提交", retryable=True)
    return sha


class GitMerge:
    def __init__(self, folder: Path, deadline: float):
        self.folder = folder
        self.deadline = deadline
        self.conflict_files: list[str] = []
        # A caller's credentials/configuration must not reach downloaded code.
        self.env = {key: value for key, value in os.environ.items()
                    if not key.startswith("GIT_") and key not in {
                        "FORK_PAT", "GH_TOKEN", "GITHUB_TOKEN", "GH_DEBUG", "SSH_ASKPASS"}}
        self.env.update({"GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull,
                         "GIT_ATTR_NOSYSTEM": "1", "GIT_TERMINAL_PROMPT": "0"})
        self.run("init", "--bare", "--template=", str(folder))
        for key, value in {"user.name": "magi-fork-catalog[bot]",
                           "user.email": "magi-fork-catalog[bot]@users.noreply.github.com",
                           "commit.gpgSign": "false", "core.autocrlf": "false",
                           "core.attributesFile": os.devnull,
                           "credential.helper": "", "http.lowSpeedLimit": "1024",
                           "http.lowSpeedTime": "30"}.items():
            self.run("config", key, value)

    def run(self, *args: str, data: bytes | None = None, accepted: tuple[int, ...] = (0,),
            push_token: str | None = None) -> subprocess.CompletedProcess:
        remaining = self.deadline - time.monotonic()
        if remaining <= 0:
            raise Deferred("本次自動合併已達時間上限，下次再試", retryable=True)
        env = dict(self.env)
        if push_token:
            auth = base64.b64encode(f"x-access-token:{push_token}".encode()).decode()
            env.update({"GIT_CONFIG_COUNT": "1", "GIT_CONFIG_KEY_0": "http.https://github.com/.extraheader",
                        "GIT_CONFIG_VALUE_0": f"AUTHORIZATION: basic {auth}"})
        result = subprocess.run(["git", "-C", str(self.folder), *args], input=data,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env, timeout=remaining)
        if result.returncode not in accepted:
            detail = result.stderr.decode("utf-8", errors="replace").strip()[-400:]
            raise Deferred(f"Git {args[0]} 未完成：{detail}", retryable=True)
        return result

    def fetch(self, remote: str, name: str, sha: str) -> None:
        self.run("remote", "add", remote, public_url(name))
        self.run("config", f"remote.{remote}.promisor", "true")
        self.run("config", f"remote.{remote}.partialclonefilter", "blob:none")
        self.run("fetch", "--filter=blob:none", "--no-tags", remote, f"{sha}:refs/heads/{remote}")

    def tree(self, commit: str) -> dict[bytes, tuple[bytes, bytes]]:
        entries = self.run("ls-tree", "-r", "-z", commit).stdout.rstrip(b"\0")
        result = {}
        for entry in entries.split(b"\0") if entries else []:
            metadata, path = entry.split(b"\t", 1)
            mode, kind, sha = metadata.split()
            result[path] = mode, sha
        return result

    def blob(self, sha: bytes | None) -> bytes:
        if sha is None:
            return b""
        value = sha.decode("ascii")
        size = int(self.run("cat-file", "-s", value).stdout)
        if size > MAX_BLOB_BYTES:
            raise Deferred("衝突檔案超過 2 MiB，保留原分支供人工檢查")
        content = self.run("cat-file", "blob", value).stdout
        if b"\0" in content:
            raise Deferred("二進位檔案衝突，保留原分支供人工檢查")
        try:
            content.decode("utf-8-sig")
        except UnicodeDecodeError as exc:
            raise Deferred("非 UTF-8 文字衝突，保留原分支供人工檢查") from exc
        return content

    def merge(self, original: str, upstream: str) -> tuple[str, list[str]]:
        bases = self.run("merge-base", "--all", original, upstream, accepted=(0, 1)).stdout.splitlines()
        if len(bases) != 1:
            raise Deferred("沒有單一共同祖先，保留原分支供人工檢查")
        result = self.run("merge-tree", "--write-tree", "--name-only", "-z", original, upstream, accepted=(0, 1))
        parts = result.stdout.split(b"\0")
        tree = parts[0].decode("ascii").strip()
        if not SHA.fullmatch(tree):
            raise Deferred("Git 沒有產生可驗證的合併樹", retryable=True)
        conflicts = []
        for path in parts[1:]:
            if not path:
                break
            conflicts.append(path)
        if result.returncode and not conflicts:
            raise Deferred("無法辨識 Git 回報的衝突", retryable=True)
        if len(conflicts) > MAX_CONFLICT_FILES:
            raise Deferred("衝突超過 1000 個檔案，保留原分支供人工檢查")
        names = [path.decode("utf-8") for path in conflicts]
        self.conflict_files = names
        self.run("read-tree", tree)
        if conflicts:
            ours, theirs, base = self.tree(original), self.tree(upstream), self.tree(bases[0].decode())
            updates = []
            for index, path in enumerate(conflicts):
                own, incoming, ancestor = ours.get(path), theirs.get(path), base.get(path)
                if (not own or not incoming or any(item and item[0] not in (b"100644", b"100755")
                                                  for item in (own, incoming, ancestor))):
                    raise Deferred("刪除、重新命名或符號連結衝突，保留原分支供人工檢查")
                contents = [self.blob(own[1]), self.blob(ancestor[1] if ancestor else None), self.blob(incoming[1])]
                files = [self.folder / f"merge-{index}-{side}.txt" for side in range(3)]
                for file, content in zip(files, contents):
                    file.write_bytes(content)
                merged = self.run("merge-file", "--ours", "-p", "--", *(str(file) for file in files)).stdout
                if path.lower().endswith(b".json"):
                    try:
                        json.loads(merged.decode("utf-8-sig"))
                    except (ValueError, UnicodeError) as exc:
                        raise Deferred("保留修改後的 JSON 無法解析，保留原分支供人工檢查") from exc
                blob = self.run("hash-object", "-w", "--stdin", data=merged).stdout.strip()
                updates.append(own[0] + b" " + blob + b"\t" + path + b"\0")
            self.run("update-index", "-z", "--index-info", data=b"".join(updates))
            tree = self.run("write-tree").stdout.decode().strip()
        message = ("Merge upstream, preserving fork edits in conflicting text\n\n"
                   f"Original: {original}\nUpstream: {upstream}\n"
                   f"Backup: refs/heads/backup/auto-sync/{original}\n"
                   f"Resolved text files: {len(names)}\nNo project code or tests were executed.\n")
        commit = self.run("commit-tree", tree, "-p", original, "-p", upstream, "-F", "-", data=message.encode()).stdout.decode().strip()
        for ancestor in (original, upstream):
            self.run("merge-base", "--is-ancestor", ancestor, commit)
        return commit, names

    def push(self, commit: str, branch: str, token: str) -> None:
        if not token:
            raise Deferred("沒有可用的推送憑證", retryable=True)
        # No force option: a concurrent update must reject this push.
        self.run("push", "--no-verify", "--porcelain", "origin", f"{commit}:refs/heads/{branch}", push_token=token)
        advertised = self.run("ls-remote", "--refs", "origin", f"refs/heads/{branch}").stdout.split()
        if not advertised or advertised[0].decode() != commit:
            raise Deferred("推送後遠端分支已有變動，留待下次重新核對", retryable=True)


class ConflictRecovery:
    def __init__(self, api: Any, state: dict[str, Any], reports: dict[str, Any], *, owner: str,
                 per_repo_seconds: float = 180, total_seconds: float = 900):
        self.api, self.state, self.reports, self.owner = api, state, reports, owner
        self.per_repo_seconds, self.remaining_seconds = per_repo_seconds, total_seconds

    def backup(self, name: str, original: str) -> str:
        branch = f"backup/auto-sync/{original}"
        path = ref_path(name, branch)
        try:
            ref = self.api.request("GET", path)
        except Exception as exc:
            if getattr(exc, "status", None) != 404:
                raise
            try:
                ref = self.api.request("POST", f"/repos/{name}/git/refs", {"ref": f"refs/heads/{branch}", "sha": original})
            except Exception as create_exc:
                if getattr(create_exc, "status", None) != 422:
                    raise
                ref = self.api.request("GET", path)
        if ref_sha(ref) != original:
            raise Deferred("備份分支不符合原提交，未修改預設分支", retryable=True)
        return branch

    def resolve(self, fork: dict[str, Any], before_push: Callable[[], None] | None = None) -> str:
        started = time.monotonic()
        name = fork["full_name"]
        record: dict[str, Any] = {"checked_at": dt.datetime.now(dt.timezone.utc).isoformat()}
        try:
            current = self.api.get_repo(name)
            parent = current.get("parent") or {}
            if (current.get("fork") is not True or current.get("private") is not False or parent.get("private") is not False
                    or current.get("full_name", "").lower() != name.lower()
                    or name.split("/", 1)[0].lower() != self.owner.lower()
                    or not parent.get("full_name") or not parent.get("default_branch")):
                raise Deferred("自動合併只允許本帳戶的公開 fork 與公開直接上游")
            branch = current["default_branch"]
            original = ref_sha(self.api.request("GET", ref_path(name, branch)))
            upstream = ref_sha(self.api.request("GET", ref_path(parent["full_name"], parent["default_branch"])))
            record.update({"original_sha": original, "upstream_sha": upstream,
                           "upstream": parent["full_name"], "branch": branch})
            record["backup_branch"] = self.backup(name, original)
            record["backup_url"] = f"https://github.com/{name}/tree/{record['backup_branch']}"
            previous = self.state.get(name, {})
            if (previous.get("status") == "deferred" and previous.get("retryable") is False
                    and previous.get("original_sha") == original and previous.get("upstream_sha") == upstream):
                record.update({"unchanged_conflict": True, "conflict_files": previous.get("conflict_files", [])})
                raise Deferred(previous["reason"])
            if self.remaining_seconds <= 0:
                raise Deferred("本次衝突修復時間已用完，下次再試", retryable=True)
            with tempfile.TemporaryDirectory(prefix="magi-merge-", ignore_cleanup_errors=True) as folder:
                store = GitMerge(Path(folder), time.monotonic() + min(self.per_repo_seconds, self.remaining_seconds))
                store.fetch("origin", name, original)
                store.fetch("upstream", parent["full_name"], upstream)
                try:
                    commit, files = store.merge(original, upstream)
                finally:
                    record["conflict_files"] = store.conflict_files
                record.update({"merge_commit": commit, "resolved_files": files})
                if ref_sha(self.api.request("GET", ref_path(name, branch))) != original:
                    raise Deferred("預設分支已在其他地方更新，下次重新合併", retryable=True)
                if before_push:
                    before_push()
                store.push(commit, branch, self.api.token)
            record.update({"status": "merged", "commit_url": f"https://github.com/{name}/commit/{commit}"})
            return "已自動合併：衝突保留我的修改，原提交已備份"
        except Exception as exc:
            record.update({"status": "deferred", "reason": str(exc)[:500],
                           "retryable": getattr(exc, "retryable", True)})
            return f"需處理：合併衝突（保留原分支；{record['reason']}）"
        finally:
            self.remaining_seconds -= time.monotonic() - started
            self.state[name] = record
            self.reports[name] = record
