#!/usr/bin/env python3
"""Discover, fork, sync, and describe public repositories for MAGI research.

Only GitHub's REST API and the Python standard library are used. The preview mode
never writes to GitHub or to the checkout.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import math
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
OWNER = "WhaleChao"
CATALOG_REPO = "ai-fork-catalog"
MIN_STARS = 1000
MAX_DAILY = 3
ACTIVE_DAYS = 180
TOPIC_QUERIES = {
    "inference": ["llm-inference", "llm-serving", "kv-cache", "mlx", "quantization"],
    "transcription": ["speech-to-text", "automatic-speech-recognition", "speaker-diarization"],
    "translation": ["machine-translation", "translation"],
    "agent": ["agent-framework", "ai-agent", "mcp-server", "model-context-protocol"],
}
CATEGORY_LABELS = {
    "inference": "推論速度與記憶體",
    "transcription": "逐字稿與語者辨識",
    "translation": "翻譯",
    "agent": "Agent 與 MCP 架構",
    "other": "其他既有 Fork",
}
CATEGORY_TOPICS = {
    "inference": "llm-inference",
    "transcription": "speech-to-text",
    "translation": "machine-translation",
    "agent": "agent-framework",
    "other": "personal-reference",
}
PATTERNS = {
    "inference": re.compile(r"llm|language model|inference|quantiz|kv.?cache|mlx|vram|gpu|model serving|transformer", re.I),
    "transcription": re.compile(r"speech.?to.?text|transcri|whisper|\basr\b|speaker diariz|voice activity|audio model", re.I),
    "translation": re.compile(r"translat|subtit|dubbing|machine translation", re.I),
    "agent": re.compile(r"\bagent\b|\bagents\b|\bmcp\b|model context protocol|harness", re.I),
}
EXCLUDE_PATTERN = re.compile(
    r"\bawesome\b|curated list|reading list|tutorial|course|book|papers|benchmark collection",
    re.I,
)
MANUAL_ACTIVITY_EXCEPTIONS = {"SYSTRAN/faster-whisper"}
OPEN_SOURCE_LICENSES = {
    "0BSD", "AFL-3.0", "AGPL-3.0", "Apache-2.0", "Artistic-2.0", "BSD-2-Clause",
    "BSD-3-Clause", "BSD-3-Clause-Clear", "BSL-1.0", "CC0-1.0",
    "CDDL-1.0", "CDDL-1.1", "CPL-1.0", "ECL-2.0", "EPL-1.0",
    "EPL-2.0", "EUPL-1.1", "EUPL-1.2", "GPL-2.0", "GPL-3.0",
    "ISC", "LGPL-2.1", "LGPL-3.0", "MIT", "MIT-0", "MPL-2.0", "MS-PL",
    "NCSA", "OFL-1.1", "OSL-3.0", "PostgreSQL", "Unlicense",
    "UPL-1.0", "Zlib",
}


def read_json(path: Path, default: Any) -> Any:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def iso_now() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


class APIError(Exception):
    def __init__(self, status: int, message: str):
        self.status = status
        super().__init__(message)


class GitHub:
    def __init__(self, token: str):
        self.token = token
        self.last_search = 0.0
        self.last_write = 0.0

    def request(self, method: str, path: str, payload: Any = None) -> Any:
        if path.startswith("http"):
            url = path
        else:
            url = "https://api.github.com" + path
        if path.startswith("/search/"):
            # The authenticated search bucket is 30 requests/minute. Avoid bursts.
            delay = 2.2 - (time.monotonic() - self.last_search)
            if delay > 0:
                time.sleep(delay)
            self.last_search = time.monotonic()
        if method != "GET":
            delay = 1.2 - (time.monotonic() - self.last_write)
            if delay > 0:
                time.sleep(delay)
            self.last_write = time.monotonic()
        body = json.dumps(payload).encode("utf-8") if payload is not None else None
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2026-03-10",
            "User-Agent": "magi-fork-catalog",
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        if body is not None:
            headers["Content-Type"] = "application/json"
        for attempt in range(4):
            req = urllib.request.Request(url, data=body, headers=headers, method=method)
            try:
                with urllib.request.urlopen(req, timeout=35) as response:
                    raw = response.read()
                    return json.loads(raw) if raw else None
            except urllib.error.HTTPError as exc:
                raw = exc.read().decode("utf-8", errors="replace")
                try:
                    message = json.loads(raw).get("message", raw)
                except json.JSONDecodeError:
                    message = raw
                retryable = exc.code in {429, 500, 502, 503, 504} or (
                    exc.code == 403 and ("rate limit" in message.lower() or "abuse" in message.lower())
                )
                if retryable and attempt < 3:
                    retry_after = exc.headers.get("Retry-After")
                    delay = min(90, int(retry_after)) if retry_after and retry_after.isdigit() else 5 * (2 ** attempt)
                    time.sleep(delay)
                    continue
                raise APIError(exc.code, message) from exc
            except urllib.error.URLError as exc:
                if attempt < 3:
                    time.sleep(3 * (2 ** attempt))
                    continue
                raise APIError(0, str(exc)) from exc
        raise RuntimeError("unreachable")

    def get_repo(self, full_name: str) -> dict[str, Any]:
        return self.request("GET", f"/repos/{full_name}")

    def owned_forks(self) -> list[dict[str, Any]]:
        forks: list[dict[str, Any]] = []
        page = 1
        while True:
            repos = self.request("GET", f"/users/{OWNER}/repos?type=owner&per_page=100&page={page}")
            forks.extend(self.get_repo(repo["full_name"]) for repo in repos if repo.get("fork") and not repo.get("private"))
            if len(repos) < 100:
                break
            page += 1
        return forks

    def search(self, query: str, page: int = 1) -> dict[str, Any]:
        params = urllib.parse.urlencode({"q": query, "sort": "updated", "order": "desc", "per_page": 100, "page": page})
        return self.request("GET", f"/search/repositories?{params}")


def source_root(repo: dict[str, Any]) -> str:
    return (repo.get("source") or repo).get("full_name", repo["full_name"]).lower()


def remaining_daily_budget(
    forks: list[dict[str, Any]], seeds: list[dict[str, str]], bootstrap_day: str | None, now: dt.datetime | None = None
) -> int:
    taipei = dt.timezone(dt.timedelta(hours=8))
    today = (now or dt.datetime.now(dt.timezone.utc)).astimezone(taipei).date()
    bootstrap_roots = {item["source"].lower() for item in seeds} if today.isoformat() == bootstrap_day else set()
    added_today = {
        source_root(fork)
        for fork in forks
        if fork.get("created_at")
        and dt.datetime.fromisoformat(fork["created_at"].replace("Z", "+00:00")).astimezone(taipei).date() == today
        and source_root(fork) not in bootstrap_roots
    }
    return max(0, MAX_DAILY - len(added_today))


def valid_source(repo: dict[str, Any], *, allow_old: bool = False) -> tuple[bool, str]:
    if repo.get("fork") or repo.get("archived") or repo.get("disabled") or repo.get("private"):
        return False, "非公開原始專案或已封存"
    if repo.get("stargazers_count", 0) < MIN_STARS:
        return False, "未達千星"
    license_id = (repo.get("license") or {}).get("spdx_id")
    if license_id not in OPEN_SOURCE_LICENSES:
        return False, "GitHub 未辨識或非開源授權"
    pushed = repo.get("pushed_at")
    if not pushed:
        return False, "缺少最近更新日期"
    age = dt.datetime.now(dt.timezone.utc) - dt.datetime.fromisoformat(pushed.replace("Z", "+00:00"))
    if age.days > ACTIVE_DAYS and not allow_old:
        return False, "最近 180 天未更新"
    return True, ""


def category_match(repo: dict[str, Any], category: str) -> bool:
    text = " ".join(filter(None, [repo.get("name"), repo.get("description")]))
    topics = set(repo.get("topics") or [])
    if EXCLUDE_PATTERN.search(text):
        return False
    return bool(PATTERNS[category].search(text)) and bool(topics.intersection(TOPIC_QUERIES[category]))


def classify(repo: dict[str, Any], override: dict[str, Any] | None = None) -> str:
    if override and override.get("category") in CATEGORY_LABELS:
        return override["category"]
    for category in ("inference", "transcription", "translation", "agent"):
        if category_match(repo, category):
            return category
    text = (repo.get("description") or "") + " " + repo.get("name", "")
    for category in ("inference", "transcription", "translation", "agent"):
        if PATTERNS[category].search(text):
            return category
    return "other"


def score(repo: dict[str, Any]) -> float:
    stars = repo.get("stargazers_count", 0)
    pushed = dt.datetime.fromisoformat(repo["pushed_at"].replace("Z", "+00:00"))
    age_days = max(0, (dt.datetime.now(dt.timezone.utc) - pushed).days)
    return math.log10(stars + 1) * 10 - age_days / 45


def discover(api: GitHub, existing_roots: set[str], max_count: int) -> tuple[list[tuple[str, dict[str, Any]]], list[str]]:
    pools: dict[str, list[dict[str, Any]]] = {category: [] for category in TOPIC_QUERIES}
    errors: list[str] = []
    seen: set[str] = set()
    for category, topics in TOPIC_QUERIES.items():
        for topic in topics:
            query = f"topic:{topic} stars:>={MIN_STARS} fork:false archived:false"
            try:
                result = api.search(query)
                if result.get("incomplete_results"):
                    errors.append(f"搜尋結果不完整：{topic}")
                    continue
                # The first page of recently updated results is enough for a
                # three-repository daily budget; query topics separately.
                for repo in result.get("items", []):
                    name = repo["full_name"].lower()
                    if name in seen or name in existing_roots:
                        continue
                    valid, _ = valid_source(repo)
                    if valid and category_match(repo, category):
                        seen.add(name)
                        pools[category].append(repo)
            except APIError as exc:
                errors.append(f"搜尋 {topic} 失敗：HTTP {exc.status} {exc}")
    if errors:
        # Partial search must never produce arbitrary new forks.
        return [], errors
    for pool in pools.values():
        pool.sort(key=score, reverse=True)
    chosen: list[tuple[str, dict[str, Any]]] = []
    used = set(existing_roots)
    rotation = list(TOPIC_QUERIES)
    start = dt.date.today().toordinal() % len(rotation)
    rotation = rotation[start:] + rotation[:start]
    while len(chosen) < max_count and any(pools.values()):
        for category in rotation:
            while pools[category] and pools[category][0]["full_name"].lower() in used:
                pools[category].pop(0)
            if pools[category] and len(chosen) < max_count:
                repo = pools[category].pop(0)
                chosen.append((category, repo))
                used.add(repo["full_name"].lower())
    return chosen, []


def fork_one(api: GitHub, source: dict[str, Any], existing_roots: set[str]) -> tuple[dict[str, Any] | None, str]:
    name = source["full_name"]
    if name.lower() in existing_roots:
        return None, "already-owned"
    try:
        response = api.request("POST", f"/repos/{name}/forks", {})
    except APIError as exc:
        return None, f"HTTP {exc.status}: {exc}"
    expected = response.get("full_name") or f"{OWNER}/{source['name']}"
    for delay in (2, 4, 8, 15, 30):
        time.sleep(delay)
        try:
            fork = api.get_repo(expected)
            if fork.get("fork") and source_root(fork) == name.lower():
                existing_roots.add(name.lower())
                return fork, "created"
        except APIError as exc:
            if exc.status != 404:
                return None, f"驗證 fork 失敗：HTTP {exc.status} {exc}"
    return None, "GitHub 已接受建立，但 59 秒內無法驗證；下次重跑會再次檢查"


def sync_forks(api: GitHub, forks: list[dict[str, Any]]) -> dict[str, str]:
    result: dict[str, str] = {}
    for index, fork in enumerate(forks, 1):
        name = fork["full_name"]
        try:
            response = api.request("POST", f"/repos/{name}/merge-upstream", {"branch": fork["default_branch"]})
            message = response.get("message", "")
            result[name] = "已是最新" if "not behind" in message.lower() else "已更新" if "successfully" in message.lower() else (message or "已同步")
        except APIError as exc:
            result[name] = "需處理：合併衝突" if exc.status == 409 else f"需處理：HTTP {exc.status} {exc}"
        if index % 10 == 0 or index == len(forks):
            print(f"已檢查同步：{index}/{len(forks)}", flush=True)
    return result


def clean_summary(value: str | None) -> str:
    text = re.sub(r"\s+", " ", value or "").strip()
    text = text.replace("|", "／")
    return text[:150] + "…" if len(text) > 150 else text


def catalog_entry(fork: dict[str, Any], overrides: dict[str, Any], statuses: dict[str, str]) -> dict[str, Any]:
    root = fork.get("source") or fork.get("parent") or fork
    upstream = fork.get("parent") or root
    override = overrides.get(root["full_name"], overrides.get(upstream["full_name"], overrides.get(fork["full_name"], {})))
    category = classify(root, override)
    license_id = (root.get("license") or {}).get("spdx_id") or "未辨識"
    summary = clean_summary(override.get("summary") or fork.get("description") or root.get("description")) or "待補用途說明"
    advice = override.get("advice") or ("架構參考" if license_id.startswith(("AGPL", "GPL")) else "待評估")
    return {
        "fork": fork["full_name"],
        "upstream": upstream["full_name"],
        "source": root["full_name"],
        "category": category,
        "summary": summary,
        "fit": override.get("fit", CATEGORY_LABELS[category] if category != "other" else "—"),
        "platform": override.get("platform", "待評估"),
        "advice": advice,
        "stars": root.get("stargazers_count", 0),
        "license": license_id,
        "sync": statuses.get(fork["full_name"], "本次未同步"),
    }


def render_catalog(entries: list[dict[str, Any]], report: dict[str, Any]) -> str:
    lines = [
        "# MAGI 技術 Fork 目錄",
        "",
        "整理可供 MAGI 研究的開源技術，涵蓋推論效能、記憶體、逐字稿、翻譯與 Agent／MCP 架構。Fork 代表技術收藏，採用建議不代表已整合。",
        "",
        f"最近檢查（UTC）：{report['checked_at']}　｜　Fork：{len(entries)}　｜　本次新增：{report.get('created', 0)}　｜　本次同步異常：{report.get('sync_issues', 0)}",
        "",
        "摘要沿用原專案語言；星數與授權以來源倉庫為準。私有 MAGI 的實作路徑、設定與資料不在此公開目錄中。",
        "",
    ]
    for category, label in CATEGORY_LABELS.items():
        group = sorted((e for e in entries if e["category"] == category), key=lambda e: (-e["stars"], e["fork"].lower()))
        lines.extend([f"## {label}（{len(group)}）", ""])
        if not group:
            lines.extend(["尚無項目。", ""])
            continue
        lines.extend([
            "| Fork／來源 | 用途 | MAGI 適用面向 | 平台 | 星數 | 授權 | 建議 | 同步 |",
            "|---|---|---|---|---:|---|---|---|",
        ])
        for e in group:
            fork_link = f"[{e['fork'].split('/')[-1]}](https://github.com/{e['fork']})"
            source_link = f"[來源](https://github.com/{e['source']})"
            status = clean_summary(e["sync"])
            lines.append(
                f"| {fork_link} · {source_link} | {e['summary']} | {e['fit']} | {e['platform']} | {e['stars']:,} | {e['license']} | {e['advice']} | {status} |"
            )
        lines.append("")
    lines.extend([
        "## 自動化規則",
        "",
        "每日台北時間 10:17 搜尋千星以上、可辨識開源授權的專案；新 Fork 每天最多 3 個，使用來源網路去重。全部既有公開 Fork 每日嘗試同步預設分支；衝突不強制覆寫。",
        "",
        "[操作與授權](SETUP.md) · [檢視最近執行紀錄](https://github.com/WhaleChao/ai-fork-catalog/actions) · [機器可讀狀態](data/report.json) · [人工調整摘要與分類](data/overrides.json)",
        "",
    ])
    return "\n".join(lines)


def update_metadata(api: GitHub, forks: list[dict[str, Any]], overrides: dict[str, Any], state: dict[str, Any], errors: list[str]) -> None:
    generated = state.setdefault("generated_descriptions", {})
    for index, fork in enumerate(forks, 1):
        root = fork.get("source") or fork.get("parent") or fork
        upstream = fork.get("parent") or root
        override = overrides.get(root["full_name"], overrides.get(upstream["full_name"], overrides.get(fork["full_name"], {})))
        category = classify(root, override)
        summary = clean_summary(override.get("summary") or root.get("description"))
        current = fork.get("description") or ""
        inherited = (fork.get("parent") or {}).get("description") or ""
        previous = generated.get(fork["full_name"])
        if summary and summary != current and (not current or current == inherited or current == previous):
            try:
                api.request("PATCH", f"/repos/{fork['full_name']}", {"description": summary})
                generated[fork["full_name"]] = summary
            except APIError as exc:
                errors.append(f"更新簡介 {fork['full_name']}：HTTP {exc.status} {exc}")
        topic = "mcp" if category == "agent" and "mcp" in (fork["name"] + " " + (summary or "")).lower() else CATEGORY_TOPICS[category]
        topics = set(fork.get("topics") or [])
        desired_topics = (topics - set(CATEGORY_TOPICS.values()) - {"mcp"}) | {topic}
        if desired_topics != topics:
            try:
                api.request("PUT", f"/repos/{fork['full_name']}/topics", {"names": sorted(desired_topics)[:20]})
            except APIError as exc:
                errors.append(f"更新分類 {fork['full_name']}：HTTP {exc.status} {exc}")
        if index % 10 == 0 or index == len(forks):
            print(f"已整理簡介與分類：{index}/{len(forks)}", flush=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("preview", "bootstrap", "daily", "refresh"), required=True)
    parser.add_argument("--preview-scope", choices=("bootstrap", "daily"), default="bootstrap")
    args = parser.parse_args()
    token = os.environ.get("FORK_PAT") or os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN") or ""
    if args.mode != "preview" and not (os.environ.get("FORK_PAT") or os.environ.get("GH_TOKEN")):
        print("FORK_PAT（或本機 GH_TOKEN）未設定，拒絕跨倉庫寫入。", file=sys.stderr)
        return 2
    api = GitHub(token)
    seeds = read_json(DATA / "seed.json", [])
    overrides = read_json(DATA / "overrides.json", {})
    state = read_json(DATA / "state.json", {"bootstrap_complete": False, "generated_descriptions": {}})
    errors: list[str] = []
    forks = api.owned_forks()
    roots = {source_root(fork) for fork in forks}
    candidates: list[tuple[str, dict[str, Any]]] = []
    mode = args.preview_scope if args.mode == "preview" else args.mode
    if mode == "bootstrap":
        for item in seeds[:30]:
            name = item["source"]
            if name.lower() in roots:
                continue
            try:
                repo = api.get_repo(name)
                valid, reason = valid_source(repo, allow_old=name in MANUAL_ACTIVITY_EXCEPTIONS)
                if valid:
                    candidates.append((item["category"], repo))
                else:
                    errors.append(f"略過 {name}：{reason}")
            except APIError as exc:
                errors.append(f"核對 {name}：HTTP {exc.status} {exc}")
    elif mode == "daily":
        budget = remaining_daily_budget(forks, seeds, state.get("bootstrap_day"))
        candidates, discovery_errors = discover(api, roots, budget) if budget else ([], [])
        errors.extend(discovery_errors)
    if args.mode == "preview":
        print(json.dumps({
            "mode": mode,
            "existing_forks": len(forks),
            "candidates": [{"source": repo["full_name"], "category": category, "stars": repo["stargazers_count"]} for category, repo in candidates],
            "errors": errors,
        }, ensure_ascii=False, indent=2))
        return 1 if errors else 0
    created: list[str] = []
    for index, (category, source) in enumerate(candidates, 1):
        fork, status = fork_one(api, source, roots)
        print(f"首次／每日 Fork：{index}/{len(candidates)} {source['full_name']} → {status}", flush=True)
        if fork:
            created.append(fork["full_name"])
            forks.append(fork)
        else:
            errors.append(f"建立 {source['full_name']}：{status}")
    if mode == "bootstrap" and not errors:
        state["bootstrap_complete"] = True
    if mode == "bootstrap":
        state["bootstrap_created"] = sorted(set(state.get("bootstrap_created", []) + created))
        state.setdefault("bootstrap_day", (dt.datetime.now(dt.timezone.utc) + dt.timedelta(hours=8)).date().isoformat())
    # Always refresh the current fork list after asynchronous creation.
    forks = api.owned_forks()
    statuses = sync_forks(api, forks)
    update_metadata(api, forks, overrides, state, errors)
    entries = [catalog_entry(fork, overrides, statuses) for fork in forks]
    sync_issues = sum(value.startswith("需處理：") for value in statuses.values())
    report = {
        "checked_at": iso_now(),
        "mode": mode,
        "owned_public_forks": len(forks),
        "created": len(created),
        "created_repositories": created,
        "bootstrap_created_total": len(state.get("bootstrap_created", [])),
        "sync_issues": sync_issues,
        "issues": errors + [f"同步 {name}：{value}" for name, value in statuses.items() if value.startswith("需處理：")],
    }
    write_json(DATA / "report.json", report)
    write_json(DATA / "state.json", state)
    (ROOT / "README.md").write_text(render_catalog(entries, report), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    # A fork with local commits can stay conflicted for many runs; report it
    # without making every scheduled workflow appear broken.
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
