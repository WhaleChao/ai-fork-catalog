import datetime as dt
import unittest

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


class CatalogTests(unittest.TestCase):
    def test_source_network_root_prevents_duplicate_fork(self):
        owned = {"full_name": "WhaleChao/llama-cpp-turboquant", "source": {"full_name": "ggml-org/llama.cpp"}}
        self.assertEqual(catalog.source_root(owned), "ggml-org/llama.cpp")

    def test_source_validation_and_activity_exception(self):
        candidate = repo("example/fast-asr", "Fast speech transcription", ["speech-to-text"])
        self.assertTrue(catalog.valid_source(candidate)[0])
        candidate["license"] = None
        self.assertFalse(catalog.valid_source(candidate)[0])
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
        ]
        selected, errors = catalog.discover(FakeAPI(items), {"example/agent"}, 3)
        self.assertFalse(errors)
        self.assertEqual(len(selected), 3)
        self.assertNotIn("example/agent", [item[1]["full_name"] for item in selected])
        self.assertNotIn("example/irrelevant", [item[1]["full_name"] for item in selected])

    def test_catalog_summary_escapes_table_separator(self):
        entry = {
            "fork": "WhaleChao/tool", "source": "example/tool", "category": "agent",
            "summary": catalog.clean_summary("Agents | tools"), "fit": "Agent", "platform": "跨平台",
            "stars": 2000, "license": "MIT", "advice": "待評估", "sync": "已同步",
        }
        markdown = catalog.render_catalog([entry], {"checked_at": "2026-09-13T00:00:00Z", "created": 0, "sync_issues": 0})
        self.assertIn("Agents ／ tools", markdown)


if __name__ == "__main__":
    unittest.main()
