"""Regression tests for DST schedule and duplicate-story selection."""
import json
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch
from zoneinfo import ZoneInfo

from schedule_guard import should_run
from news_collector import normalize_article_url, published_article_urls


class AtomicHistoryTests(unittest.TestCase):
    def test_history_writes_complete_json_in_both_worktrees(self):
        import os
        from unittest.mock import patch
        import publish_instagram
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "publishing-history").mkdir()
            with patch.object(publish_instagram, "HISTORY_FILE", root / "instagram_publish_history.json"), \
                 patch("publish_instagram.subprocess.run") as run, \
                 patch("publish_instagram.Path", wraps=Path):
                run.return_value.returncode = 0
                original = Path.cwd()
                try:
                    os.chdir(root)
                    publish_instagram.save_history({"test": {"status": "pending"}})
                finally:
                    os.chdir(original)
            expected = {"test": {"status": "pending"}}
            self.assertEqual(json.loads((root / "instagram_publish_history.json").read_text()), expected)
            self.assertEqual(json.loads((root / "publishing-history" / "instagram_publish_history.json").read_text()), expected)
            self.assertFalse(list(root.glob(".history-*")))
            self.assertFalse(list((root / "publishing-history").glob(".history-*")))


class ReliabilityTests(unittest.TestCase):
    def test_dst_window(self):
        tz = ZoneInfo("America/Toronto")
        for date in ("2026-01-14T18:00:00", "2026-07-14T18:00:00"):
            self.assertTrue(should_run("schedule", datetime.fromisoformat(date).replace(tzinfo=tz)))
        self.assertFalse(should_run("schedule", datetime(2026, 10, 14, 17, tzinfo=tz)))
        self.assertTrue(should_run("schedule", datetime(2026, 10, 14, 19, tzinfo=tz)))
        self.assertFalse(should_run("schedule", datetime(2026, 10, 14, 22, tzinfo=tz)))
        self.assertTrue(should_run("workflow_dispatch", datetime(2026, 10, 14, 19, tzinfo=tz)))

    def test_only_dst_correct_utc_cron_runs(self):
        tz = ZoneInfo("America/Toronto")
        summer = datetime(2026, 10, 19, 18, 14, tzinfo=tz)
        winter = datetime(2026, 12, 21, 18, 14, tzinfo=tz)
        self.assertTrue(should_run("schedule", summer, "13 22 * * 1-5"))
        self.assertFalse(should_run("schedule", summer, "13 0 * * 2-6"))
        self.assertTrue(should_run("schedule", winter, "13 23 * * 1-5"))
        self.assertFalse(should_run("schedule", winter, "13 22 * * 1-5"))
        # Late deliveries remain eligible for either genuine local run.
        self.assertTrue(should_run("schedule", summer.replace(hour=20, minute=47),
                                   "13 22 * * 1-5"))
        self.assertTrue(should_run("schedule", summer.replace(hour=20, minute=47),
                                  "13 23 * * 1-5"))
        self.assertFalse(should_run("schedule", summer.replace(hour=22),
                                    "13 22 * * 1-5"))

    def test_published_urls(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "history.json"
            path.write_text(json.dumps({
                "post": {"status": "published", "article_urls": ["https://example.com/story?utm=x"]},
                "attempt": {"status": "pending", "article_urls": ["https://example.com/other"]},
            }), encoding="utf-8")
            self.assertEqual(published_article_urls(path), {"https://example.com/story"})
            self.assertEqual(normalize_article_url("https://example.com/story/"), "https://example.com/story")

    def test_missing_history_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(RuntimeError):
                published_article_urls(Path(directory) / "missing.json")


if __name__ == "__main__":
    unittest.main()
