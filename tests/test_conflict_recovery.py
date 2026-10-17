import contextlib
import io
import json
import os
from pathlib import Path
import subprocess
import tempfile
import time
import unittest
from unittest import mock
from urllib.parse import unquote

import catalog
from conflict_recovery import ConflictRecovery, GitMerge, ref_path


def git(folder, *args, check=True):
    result = subprocess.run(["git", "-C", str(folder), *args], capture_output=True,
                            encoding="utf-8", env={**os.environ, "GIT_CONFIG_GLOBAL": os.devnull,
                                                   "GIT_CONFIG_NOSYSTEM": "1", "GIT_TERMINAL_PROMPT": "0"})
    if check and result.returncode:
        raise AssertionError(result.stderr)
    return result.stdout.strip()


class History:
    def __init__(self, root, kind="text"):
        self.work = root / "work"
        self.work.mkdir()
        git(self.work, "init", "--initial-branch=main", "--template=")
        for key, value in {"user.name": "Test", "user.email": "test@example.invalid",
                           "commit.gpgSign": "false", "core.autocrlf": "false"}.items():
            git(self.work, "config", key, value)
        base = [f"line {index}\n" for index in range(24)]
        base[5] = "value = base\n"
        self.ours = list(base)
        self.ours[5] = "value = mine\n"
        theirs = list(base)
        theirs[5] = "value = upstream\n"
        theirs[19] = "upstream nonconflicting change\n"
        (self.work / "note.txt").write_bytes(b"\0base" if kind == "binary" else "".join(base).encode())
        git(self.work, "add", ".")
        git(self.work, "commit", "-m", "base")
        git(self.work, "switch", "-c", "upstream")
        if kind == "delete":
            (self.work / "note.txt").unlink()
        else:
            (self.work / "note.txt").write_bytes(b"\0upstream" if kind == "binary" else "".join(theirs).encode())
        (self.work / "upstream-only.txt").write_text("upstream addition\n", encoding="utf-8")
        git(self.work, "add", "-A")
        git(self.work, "commit", "-m", "upstream change")
        self.upstream_sha = git(self.work, "rev-parse", "HEAD")
        git(self.work, "switch", "main")
        (self.work / "note.txt").write_bytes(b"\0mine" if kind == "binary" else "".join(self.ours).encode())
        (self.work / "my-only.txt").write_text("my addition\n", encoding="utf-8")
        git(self.work, "add", "-A")
        git(self.work, "commit", "-m", "my edits")
        self.original = git(self.work, "rev-parse", "HEAD")
        self.origin, self.upstream = root / "origin.git", root / "upstream.git"
        git(root, "clone", "--bare", "--template=", str(self.work), str(self.origin))
        git(root, "clone", "--bare", "--template=", str(self.work), str(self.upstream))
        git(self.upstream, "update-ref", "refs/heads/main", self.upstream_sha)
        self.fork = {"full_name": "WhaleChao/project", "fork": True, "private": False,
                     "default_branch": "main", "parent": {"full_name": "upstream/project", "default_branch": "main", "private": False}}

    def url(self, name):
        return {"WhaleChao/project": self.origin.as_uri(), "upstream/project": self.upstream.as_uri()}[name]

    def head(self):
        return git(self.origin, "rev-parse", "refs/heads/main")

    def backup(self):
        return git(self.origin, "rev-parse", f"refs/heads/backup/auto-sync/{self.original}")

    def concurrent_edit(self):
        git(self.work, "switch", "main")
        (self.work / "new-user-edit.txt").write_text("concurrent personal change\n", encoding="utf-8")
        git(self.work, "add", ".")
        git(self.work, "commit", "-m", "concurrent user change")
        git(self.work, "push", str(self.origin), "main")
        return self.head()

    def upstream_fixes_binary(self):
        git(self.work, "switch", "upstream")
        (self.work / "note.txt").write_bytes(b"\0mine")
        git(self.work, "add", ".")
        git(self.work, "commit", "-m", "upstream converges with fork")
        git(self.work, "push", str(self.upstream), "HEAD:refs/heads/main")


class RepoAPI:
    token = "private-test-token"

    def __init__(self, history):
        self.history = history
        self.calls = []
        self.fail_backup = False
        self.deny_second_guard = False
        self.guard_reads = 0

    def get_repo(self, name):
        return dict(self.history.fork)

    def request(self, method, path, payload=None):
        self.calls.append((method, path, payload))
        if path.endswith("/actions/permissions"):
            self.guard_reads += 1
            if self.deny_second_guard and self.guard_reads == 2:
                raise catalog.APIError(403, "guard denied")
            return {"enabled": False}
        if path.endswith("/merge-upstream"):
            raise catalog.APIError(409, "Merge conflict")
        if method == "POST" and path.endswith("/git/refs"):
            if self.fail_backup:
                raise catalog.APIError(403, "backup denied")
            git(self.history.origin, "update-ref", payload["ref"], payload["sha"])
            return {"object": {"sha": payload["sha"]}}
        for name, repo in (("WhaleChao/project", self.history.origin), ("upstream/project", self.history.upstream)):
            prefix = f"/repos/{name}/git/ref/heads/"
            if method == "GET" and path.startswith(prefix):
                branch = unquote(path[len(prefix):])
                value = git(repo, "rev-parse", "--verify", f"refs/heads/{branch}", check=False)
                if not value:
                    raise catalog.APIError(404, "Not Found")
                return {"object": {"sha": value}}
        raise AssertionError((method, path, payload))


class RecoveryTests(unittest.TestCase):
    def test_private_or_redirected_repositories_are_never_backed_up_or_merged(self):
        base = {"full_name": "WhaleChao/project", "fork": True, "private": False,
                "default_branch": "main", "parent": {"full_name": "upstream/project", "private": False, "default_branch": "main"}}
        for change in ({"private": True}, {"fork": False}, {"full_name": "another/project"},
                       {"parent": {**base["parent"], "private": True}}):
            with self.subTest(change=change):
                api = mock.Mock()
                api.get_repo.return_value = {**base, **change}
                with mock.patch("conflict_recovery.GitMerge") as store:
                    status = ConflictRecovery(api, {}, {}, owner="WhaleChao").resolve(base)
                    store.assert_not_called()
                api.request.assert_not_called()
                self.assertTrue(status.startswith("需處理：合併衝突"))

    def test_real_merge_backs_up_keeps_our_conflicts_and_upstream_other_changes(self):
        with tempfile.TemporaryDirectory() as folder:
            history = History(Path(folder))
            api = RepoAPI(history)
            state, reports = {}, {}
            recovery = ConflictRecovery(api, state, reports, owner="WhaleChao")
            real_push = GitMerge.push

            def verified_push(store, commit, branch, token):
                self.assertEqual(history.backup(), history.original)
                self.assertEqual(api.guard_reads, 2)
                return real_push(store, commit, branch, token)

            with mock.patch("conflict_recovery.public_url", side_effect=history.url), mock.patch.object(GitMerge, "push", new=verified_push), contextlib.redirect_stdout(io.StringIO()):
                statuses = catalog.sync_forks(api, [history.fork], actions_targets={"whalechao/project"}, conflict_recovery=recovery)
            self.assertTrue(statuses["WhaleChao/project"].startswith("已自動合併"))
            self.assertEqual(catalog.sync_problem_counts(statuses), (0, 0))
            self.assertEqual(history.backup(), history.original)
            content = git(history.origin, "show", "main:note.txt")
            self.assertIn("value = mine", content)
            self.assertNotIn("value = upstream", content)
            self.assertIn("upstream nonconflicting change", content)
            self.assertEqual(git(history.origin, "show", "main:my-only.txt"), "my addition")
            self.assertEqual(git(history.origin, "show", "main:upstream-only.txt"), "upstream addition")
            for ancestor in (history.original, history.upstream_sha):
                git(history.origin, "merge-base", "--is-ancestor", ancestor, history.head())
            self.assertEqual(reports["WhaleChao/project"]["resolved_files"], ["note.txt"])
            self.assertEqual(reports["WhaleChao/project"]["status"], "merged")
            self.assertNotIn(api.token, json.dumps(reports))

    def test_unsupported_conflicts_keep_branch_and_cache_same_commits_without_failure(self):
        for kind in ("binary", "delete"):
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as folder:
                history = History(Path(folder), kind)
                api = RepoAPI(history)
                state, reports = {}, {}
                with mock.patch("conflict_recovery.public_url", side_effect=history.url):
                    status = ConflictRecovery(api, state, reports, owner="WhaleChao").resolve(history.fork)
                self.assertEqual(history.head(), history.original)
                self.assertEqual(history.backup(), history.original)
                self.assertEqual(catalog.sync_problem_counts({"project": status}), (1, 0))
                self.assertIs(state["WhaleChao/project"]["retryable"], False)
                self.assertEqual(state["WhaleChao/project"]["conflict_files"], ["note.txt"])
                saved = json.loads(json.dumps(state))
                with mock.patch("conflict_recovery.GitMerge") as store:
                    again = ConflictRecovery(api, saved, {}, owner="WhaleChao").resolve(history.fork)
                    store.assert_not_called()
                self.assertEqual(catalog.sync_problem_counts({"project": again}), (1, 0))
                self.assertTrue(saved["WhaleChao/project"]["unchanged_conflict"])
                self.assertEqual(sum(method == "POST" for method, path, payload in api.calls), 1)

    def test_changed_upstream_retries_previously_deferred_conflict(self):
        with tempfile.TemporaryDirectory() as folder:
            history = History(Path(folder), "binary")
            api = RepoAPI(history)
            state, reports = {}, {}
            with mock.patch("conflict_recovery.public_url", side_effect=history.url):
                recovery = ConflictRecovery(api, state, reports, owner="WhaleChao")
                self.assertTrue(recovery.resolve(history.fork).startswith("需處理：合併衝突"))
                history.upstream_fixes_binary()
                self.assertTrue(recovery.resolve(history.fork).startswith("已自動合併"))
            self.assertNotEqual(history.head(), history.original)
            self.assertEqual(history.backup(), history.original)

    def test_backup_failure_prevents_fetch_and_push(self):
        with tempfile.TemporaryDirectory() as folder:
            history = History(Path(folder))
            api = RepoAPI(history)
            api.fail_backup = True
            with mock.patch("conflict_recovery.GitMerge") as store:
                status = ConflictRecovery(api, {}, {}, owner="WhaleChao").resolve(history.fork)
                store.assert_not_called()
            self.assertIn("backup denied", status)
            self.assertEqual(history.head(), history.original)
            self.assertEqual(catalog.sync_problem_counts({"project": status}), (1, 0))

    def test_concurrent_user_commit_rejects_push_without_overwriting(self):
        with tempfile.TemporaryDirectory() as folder:
            history = History(Path(folder))
            api = RepoAPI(history)
            concurrent = []
            with mock.patch("conflict_recovery.public_url", side_effect=history.url):
                status = ConflictRecovery(api, {}, {}, owner="WhaleChao").resolve(history.fork, before_push=lambda: concurrent.append(history.concurrent_edit()))
            self.assertTrue(status.startswith("需處理：合併衝突"))
            self.assertEqual(history.head(), concurrent[0])
            self.assertEqual(git(history.origin, "show", "main:new-user-edit.txt"), "concurrent personal change")
            self.assertEqual(history.backup(), history.original)

    def test_second_actions_guard_failure_prevents_recovery_push(self):
        with tempfile.TemporaryDirectory() as folder:
            history = History(Path(folder))
            api = RepoAPI(history)
            api.deny_second_guard = True
            with mock.patch("conflict_recovery.public_url", side_effect=history.url), mock.patch.object(GitMerge, "push") as push, contextlib.redirect_stdout(io.StringIO()):
                statuses = catalog.sync_forks(api, [history.fork], actions_targets={"whalechao/project"},
                                              conflict_recovery=ConflictRecovery(api, {}, {}, owner="WhaleChao"))
                push.assert_not_called()
            self.assertEqual(catalog.sync_problem_counts(statuses), (1, 0))
            self.assertEqual(history.head(), history.original)
            self.assertEqual(history.backup(), history.original)

    def test_exhausted_budget_still_backs_up_without_mutating_branch(self):
        with tempfile.TemporaryDirectory() as folder:
            history = History(Path(folder))
            api = RepoAPI(history)
            with mock.patch("conflict_recovery.GitMerge") as store:
                status = ConflictRecovery(api, {}, {}, owner="WhaleChao", total_seconds=0).resolve(history.fork)
                store.assert_not_called()
            self.assertEqual(history.backup(), history.original)
            self.assertEqual(history.head(), history.original)
            self.assertIn("下次再試", status)

    def test_git_read_processes_do_not_inherit_authentication_or_trace_config(self):
        with tempfile.TemporaryDirectory() as folder, mock.patch.dict(os.environ, {
            "FORK_PAT": "private-test-token", "GIT_TRACE_CURL": "1", "GIT_CONFIG_COUNT": "1",
            "GIT_CONFIG_KEY_0": "http.extraHeader", "GIT_CONFIG_VALUE_0": "private-header",
        }):
            store = GitMerge(Path(folder), time.monotonic() + 15)
            self.assertNotIn("FORK_PAT", store.env)
            self.assertNotIn("GIT_TRACE_CURL", store.env)
            self.assertNotIn("GIT_CONFIG_VALUE_0", store.env)
            self.assertEqual(store.env["GIT_CONFIG_GLOBAL"], os.devnull)


if __name__ == "__main__":
    unittest.main()
