import datetime as dt
import contextlib
import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import catalog


def repo(name, description, topics, stars=2000, license_id="MIT"):
    return {
        "full_name": name,
        "name": name.split("/")[-1],
        "description": description,
        "topics": topics,
        "stargazers_count": stars,
        "license": {"spdx_id": license_id} if license_id else None,
        "pushed_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "fork": False,
        "archived": False,
        "disabled": False,
        "private": False,
    }


class FakeAPI:
    def __init__(self, items):
        self.items = items

    def search(self, query):
        topic = query.split(" ")[0].split(":", 1)[1]
        return {"items": [item for item in self.items if topic in item["topics"]], "incomplete_results": False}


class RecordingAPI:
    def __init__(self):
        self.calls = []

    def request(self, method, path, payload):
        self.calls.append((method, path, payload))
        return {}


class CatalogTests(unittest.TestCase):
    def test_actions_guard_disables_and_verifies_before_sync(self):
        api = mock.Mock()
        api.request.side_effect = [{"enabled": True}, None, {"enabled": False}, {"message": "Successfully merged upstream"}]
        fork = {"full_name": "WhaleChao/tool", "default_branch": "main", "fork": True, "private": False}
        actions = {}
        with contextlib.redirect_stdout(io.StringIO()):
            statuses = catalog.sync_forks(api, [fork], actions_targets={"whalechao/tool"}, actions_statuses=actions)
        path = "/repos/WhaleChao/tool/actions/permissions"
        self.assertEqual(api.request.call_args_list, [mock.call("GET", path), mock.call("PUT", path, {"enabled": False}), mock.call("GET", path), mock.call("POST", "/repos/WhaleChao/tool/merge-upstream", {"branch": "main"})])
        self.assertEqual(statuses["WhaleChao/tool"], "已更新")
        self.assertIn("本次停用", actions["WhaleChao/tool"])

    def test_actions_guard_failure_prevents_sync_push(self):
        for responses in ([catalog.APIError(403, "forbidden")], [{"enabled": True}, None, {"enabled": True}]):
            api = mock.Mock()
            api.request.side_effect = responses
            fork = {"full_name": "WhaleChao/tool", "default_branch": "main", "fork": True}
            with contextlib.redirect_stdout(io.StringIO()):
                statuses = catalog.sync_forks(api, [fork], actions_targets={"whalechao/tool"})
            self.assertEqual(catalog.sync_problem_counts(statuses), (0, 1))
            self.assertFalse(any(call.args[0] == "POST" for call in api.request.call_args_list))

    def test_actions_guard_rerun_and_keep_policy(self):
        policy = {"disable_inherited_actions": ["WhaleChao/tool", "WhaleChao/ai-fork-catalog", "other/tool"], "keep_actions": ["WhaleChao/development"]}
        state = {"reference_actions_forks": ["WhaleChao/new", "WhaleChao/Development"]}
        self.assertEqual(catalog.reference_actions_targets(policy, state), {"whalechao/tool", "whalechao/new"})
        api = mock.Mock()
        api.request.side_effect = [{"enabled": False}, {"message": "not behind"}]
        fork = {"full_name": "WhaleChao/tool", "default_branch": "main", "fork": True}
        with contextlib.redirect_stdout(io.StringIO()):
            catalog.sync_forks(api, [fork], actions_targets={"whalechao/tool"})
        self.assertFalse(any(call.args[0] == "PUT" for call in api.request.call_args_list))
        with self.assertRaises(catalog.APIError):
            catalog.disable_reference_actions(api, dict(fork, private=True))

    def test_classic_scope_preflight_accepts_public_and_normalized_repo(self):
        self.assertEqual(catalog.token_permission_issues({"public_repo", "workflow"}), [])
        self.assertEqual(catalog.token_permission_issues({"repo", "workflow"}), [])
        self.assertEqual(catalog.token_permission_issues(None), [])
        self.assertIn("缺少 workflow", catalog.token_permission_issues({"public_repo"})[0])
        self.assertEqual(len(catalog.token_permission_issues(set())), 2)

    def test_request_reads_scope_header_without_exposing_token(self):
        for headers, expected in [({"X-OAuth-Scopes": "public_repo, workflow"}, {"public_repo", "workflow"}), ({}, None), ({"X-OAuth-Scopes": ""}, set())]:
            response = mock.MagicMock()
            response.__enter__.return_value = response
            response.headers = headers
            response.read.return_value = b'{}'
            api = catalog.GitHub("private-test-token")
            with mock.patch("urllib.request.urlopen", return_value=response):
                api.request("GET", "/user")
            self.assertEqual(api.oauth_scopes, expected)

    def test_missing_workflow_skips_all_sync_requests(self):
        api = RecordingAPI()
        forks = [{"full_name": "WhaleChao/one"}, {"full_name": "WhaleChao/two"}]
        statuses = catalog.sync_forks(api, forks, blocked_reason="缺少 workflow 權限")
        self.assertEqual(api.calls, [])
        self.assertTrue(all(value.startswith("略過：") for value in statuses.values()))
        self.assertEqual(catalog.sync_problem_counts(statuses), (0, 0))

    def test_sync_conflict_is_distinct_from_api_failure(self):
        api = mock.Mock()
        api.request.side_effect = [catalog.APIError(409, "conflict"), catalog.APIError(422, "without workflow scope"), {"message": "Successfully merged upstream"}]
        forks = [{"full_name": f"WhaleChao/{name}", "default_branch": "main"} for name in ("conflict", "blocked", "ok")]
        with contextlib.redirect_stdout(io.StringIO()):
            statuses = catalog.sync_forks(api, forks)
        self.assertEqual(statuses["WhaleChao/conflict"], "需處理：合併衝突")
        self.assertEqual(statuses["WhaleChao/ok"], "已更新")
        self.assertEqual(catalog.sync_problem_counts(statuses), (1, 1))

    def test_failed_preflight_publishes_current_reason_without_writes(self):
        for identity, scopes, reason in [
            ({"login": "other-account"}, {"public_repo", "workflow"}, "金鑰帳戶"),
            ({"login": "WhaleChao"}, {"workflow"}, "public_repo"),
            (catalog.APIError(401, "Bad credentials"), None, "HTTP 401"),
        ]:
            with self.subTest(reason=reason), tempfile.TemporaryDirectory() as folder:
                data = Path(folder)
                api = mock.Mock()
                api.oauth_scopes = scopes
                if isinstance(identity, Exception):
                    api.request.side_effect = identity
                else:
                    api.request.return_value = identity
                summary = data / "summary.md"
                with mock.patch.object(catalog, "DATA", data), mock.patch.object(catalog, "GitHub", return_value=api), mock.patch("sys.argv", ["catalog.py", "--mode", "refresh"]), mock.patch.dict(os.environ, {"FORK_PAT": "test-token", "GITHUB_STEP_SUMMARY": str(summary)}), contextlib.redirect_stderr(io.StringIO()):
                    self.assertEqual(catalog.main(), 2)
                api.owned_forks.assert_not_called()
                self.assertIn(reason, summary.read_text(encoding="utf-8"))
                self.assertTrue(json.loads((data / "report.json").read_text(encoding="utf-8"))["preflight_failed"])

    def test_preview_does_not_write_or_validate_write_permissions(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            api = mock.Mock()
            api.owned_forks.return_value = []
            with mock.patch.object(catalog, "ROOT", root), mock.patch.object(catalog, "DATA", root), mock.patch.object(catalog, "GitHub", return_value=api), mock.patch("sys.argv", ["catalog.py", "--mode", "preview"]), mock.patch.dict(os.environ, {"GITHUB_STEP_SUMMARY": str(root / "summary.md")}), contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(catalog.main(), 0)
            api.request.assert_not_called()
            self.assertEqual(list(root.iterdir()), [])

    def test_refresh_exit_code_and_summary_match_sync_outcome(self):
        for statuses, scopes, expected in [
            ({"WhaleChao/tool": "需處理：合併衝突"}, {"public_repo", "workflow"}, 0),
            ({"WhaleChao/tool": "需處理：HTTP 503 unavailable"}, {"public_repo", "workflow"}, 1),
            (None, {"public_repo"}, 1),
        ]:
            with self.subTest(statuses=statuses), tempfile.TemporaryDirectory() as folder:
                root = Path(folder)
                data = root / "data"
                data.mkdir()
                summary_path = root / "summary.md"
                source = repo("example/tool", "Agent framework", ["agent-framework"])
                fork = dict(source, full_name="WhaleChao/tool", fork=True, source=source)
                api = mock.Mock()
                api.oauth_scopes = scopes
                api.request.return_value = {"login": "WhaleChao"}
                api.owned_forks.return_value = [fork]
                # Exercise the real missing-scope path, including no merge writes.
                sync = mock.patch.object(catalog, "sync_forks", return_value=statuses) if statuses is not None else contextlib.nullcontext()
                with mock.patch.object(catalog, "ROOT", root), mock.patch.object(catalog, "DATA", data), mock.patch.object(catalog, "GitHub", return_value=api), mock.patch.object(catalog, "update_metadata"), mock.patch("sys.argv", ["catalog.py", "--mode", "refresh"]), mock.patch.dict(os.environ, {"FORK_PAT": "private-test-token", "GITHUB_STEP_SUMMARY": str(summary_path)}), sync, contextlib.redirect_stdout(io.StringIO()):
                    self.assertEqual(catalog.main(), expected)
                report = json.loads((data / "report.json").read_text(encoding="utf-8"))
                self.assertEqual(report["ok"], expected == 0)
                self.assertNotIn("private-test-token", summary_path.read_text(encoding="utf-8"))
                if statuses is None:
                    self.assertEqual(report["sync_skipped"], 1)
                    self.assertEqual(len(report["issues"]), 1)
                    self.assertEqual(api.request.call_args_list, [mock.call("GET", "/user")])

    def test_source_network_root_prevents_duplicate_fork(self):
        owned = {"full_name": "WhaleChao/llama-cpp-turboquant", "source": {"full_name": "ggml-org/llama.cpp"}}
        self.assertEqual(catalog.source_root(owned), "ggml-org/llama.cpp")

    def test_daily_budget_survives_same_day_rerun(self):
        now = dt.datetime(2026, 9, 13, 16, 30, tzinfo=dt.timezone.utc)  # 00:30 Taipei next day
        forks = [
            {"full_name": "WhaleChao/first", "source": {"full_name": "example/first"}, "created_at": "2026-09-13T16:10:00Z"},
            {"full_name": "WhaleChao/second", "source": {"full_name": "example/second"}, "created_at": "2026-09-13T16:20:00Z"},
            {"full_name": "WhaleChao/bootstrap", "source": {"full_name": "example/bootstrap"}, "created_at": "2026-09-13T16:25:00Z"},
        ]
        self.assertEqual(catalog.remaining_daily_budget(forks, [{"source": "example/bootstrap"}], "2026-09-13", now), 0)
        self.assertEqual(catalog.remaining_daily_budget(forks, [{"source": "example/bootstrap"}], "2026-09-14", now), 1)

    def test_source_validation_and_activity_exception(self):
        candidate = repo("example/fast-asr", "Fast speech transcription", ["speech-to-text"])
        self.assertTrue(catalog.valid_source(candidate)[0])
        candidate["license"] = None
        self.assertFalse(catalog.valid_source(candidate)[0])
        candidate["license"] = {"spdx_id": "CC-BY-NC-4.0"}
        self.assertFalse(catalog.valid_source(candidate)[0])
        candidate["license"] = {"spdx_id": "AGPL-3.0"}
        self.assertTrue(catalog.valid_source(candidate)[0])
        candidate["license"] = {"spdx_id": "MIT"}
        candidate["pushed_at"] = "2025-01-01T00:00:00Z"
        self.assertFalse(catalog.valid_source(candidate)[0])
        self.assertTrue(catalog.valid_source(candidate, allow_old=True)[0])

    def test_daily_discovery_filters_and_caps(self):
        items = [
            repo("example/fast-inference", "Fast LLM inference", ["llm-serving"], 5000),
            repo("example/transcriber", "Whisper speech transcription", ["speech-to-text"], 4000),
            repo("example/translator", "Offline machine translation", ["machine-translation"], 3000),
            repo("example/agent", "Agent orchestration framework", ["agent-framework"], 2000),
            repo("example/irrelevant", "A general dashboard", ["mcp-server"], 9000),
            repo("example/tuner", "Unified Efficient Fine-Tuning of LLMs", ["quantization"], 8000),
            repo("example/browser-tool", "Browser extension for translation based on ChatGPT API", ["translation"], 7000),
            repo("example/userscript", "Bilingual translation extension and Greasemonkey script", ["translation"], 6000),
        ]
        selected, errors = catalog.discover(FakeAPI(items), {"example/agent"}, 3)
        self.assertFalse(errors)
        self.assertEqual(len(selected), 3)
        self.assertNotIn("example/agent", [item[1]["full_name"] for item in selected])
        self.assertNotIn("example/irrelevant", [item[1]["full_name"] for item in selected])
        self.assertNotIn("example/tuner", [item[1]["full_name"] for item in selected])
        self.assertNotIn("example/browser-tool", [item[1]["full_name"] for item in selected])
        self.assertNotIn("example/userscript", [item[1]["full_name"] for item in selected])

    def test_catalog_summary_escapes_table_separator(self):
        entry = {
            "fork": "WhaleChao/tool", "source": "example/tool", "category": "agent",
            "summary": catalog.clean_summary("Agents | tools"), "fit": "Agent", "platform": "跨平台",
            "stars": 2000, "license": "MIT", "advice": "待評估", "sync": "已同步",
        }
        markdown = catalog.render_catalog([entry], {"checked_at": "2026-09-13T00:00:00Z", "created": 0, "sync_issues": 0})
        self.assertIn("Agents ／ tools", markdown)

    def test_personal_description_is_not_overwritten(self):
        api = RecordingAPI()
        source = repo("example/mcp", "Generic upstream text", ["mcp-server"])
        fork = {
            "full_name": "WhaleChao/mcp", "name": "mcp", "description": "My own detailed description",
            "topics": [], "parent": {"full_name": "example/mcp", "description": "Generic upstream text"},
            "source": source,
        }
        catalog.update_metadata(api, [fork], {"example/mcp": {"category": "agent", "summary": "Better summary"}}, {}, [])
        self.assertNotIn("PATCH", [call[0] for call in api.calls])
        self.assertIn("PUT", [call[0] for call in api.calls])


if __name__ == "__main__":
    unittest.main()
