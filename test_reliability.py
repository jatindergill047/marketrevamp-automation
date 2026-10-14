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


class ReliabilityTests(unittest.TestCase):
    def test_dst_window(self):
        tz = ZoneInfo("America/Toronto")
        for date in ("2026-01-14T18:00:00", "2026-07-14T18:00:00"):
            self.assertTrue(should_run("schedule", datetime.fromisoformat(date).replace(tzinfo=tz)))
        self.assertFalse(should_run("schedule", datetime(2026, 10, 14, 17, tzinfo=tz)))
        self.assertFalse(should_run("schedule", datetime(2026, 10, 14, 19, tzinfo=tz)))
        self.assertTrue(should_run("workflow_dispatch", datetime(2026, 10, 14, 19, tzinfo=tz)))

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
