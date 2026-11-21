"""Offline end-to-end candidate integration checks for fresh R72 news review."""
import copy
import json
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from r67_weekday_news import review_package
from reel_bookends import HOOK_LINE, FOLLOW_LINE, narration_segments
from reel_r50_review import draw_frames
from reel_r72_review import (prepare_stories, publisher_from_url,
                             MAX_TOTAL_STORY_WORDS, MIN_TOTAL_STORY_WORDS)
from test_r67_weekday_news import sample

NOW = datetime(2026, 11, 23, 14, tzinfo=ZoneInfo("America/Toronto"))
DOMAINS = ("techcrunch.com", "arstechnica.com", "coindesk.com",
           "cnbc.com", "bbc.co.uk", "coindesk.com", "cnbc.com")


def package():
    results = sample()
    for i, item in enumerate(results["selected_stories"]):
        item["url"] = f"https://{DOMAINS[i]}/2026/11/23/headline-{i}?utm_campaign=test"
        item["title"] += " as decision makers review the new developments this week"
        item["published"] = (NOW - timedelta(hours=i+2)).isoformat()
    return review_package(results, set(), now=NOW)


class R72NewsReviewTests(unittest.TestCase):
    def test_seven_stories_produce_short_attributed_scripts(self):
        prepared = prepare_stories(package(), set(), now=NOW)
        self.assertEqual(len(prepared), 7)
        self.assertTrue(all(not s["narration_text"].startswith("According to ")
                            for s in prepared))
        self.assertTrue(all(s["source_name"] and s["source_url"].startswith("https://")
                            for s in prepared))
        self.assertTrue(all(s["narration_text"].endswith((".", "!", "?"))
                            for s in prepared))
        total = sum(len(s["narration_text"].split()) for s in prepared)
        self.assertGreaterEqual(total, MIN_TOTAL_STORY_WORDS)
        self.assertLessEqual(total, MAX_TOTAL_STORY_WORDS)
        self.assertTrue(all(s["fact_check_status"] ==
                            "source_supported_pending_editorial_approval"
                            for s in prepared))
        self.assertTrue(all(s["editorial_approved"] is False for s in prepared))
        self.assertTrue(all("?utm_campaign" not in s["source_url"] for s in prepared))
        segments = narration_segments(prepared)
        self.assertEqual(segments[0]["narration_text"], HOOK_LINE)
        self.assertEqual(segments[-1]["narration_text"], FOLLOW_LINE)
        self.assertEqual(len(segments), 9)

    def test_weekend_news_reviews_allowed_but_wrong_dates_still_refused(self):
        for days_back in (1, 2):  # Sunday and Saturday, Toronto local time
            when = NOW - timedelta(days=days_back)
            data = copy.deepcopy(package())
            data["toronto_date"] = when.date().isoformat()
            for i, item in enumerate(data["stories"]):
                item["published_at"] = (
                    when - timedelta(hours=i + 2)
                ).isoformat()
            prepared = prepare_stories(data, set(), now=when)
            self.assertEqual(len(prepared), 7)
            self.assertTrue(all(story["editorial_approved"] is False
                                for story in prepared))
            self.assertTrue(all(story["source_url"].startswith("https://")
                                for story in prepared))
        data = package()
        data["toronto_date"] = "2026-11-20"
        with self.assertRaisesRegex(ValueError, "today's Toronto"):
            prepare_stories(data, set(), now=NOW)

    def test_history_dedup_and_near_duplicate_fail_closed(self):
        original = package()
        with self.assertRaisesRegex(ValueError, "published"):
            prepare_stories(original, {original["stories"][1]["source_url"]},
                            now=NOW)
        data = copy.deepcopy(original)
        data["stories"][1]["source_url"] = data["stories"][0]["source_url"]
        with self.assertRaisesRegex(ValueError, "repeated"):
            prepare_stories(data, set(), now=NOW)
        data = copy.deepcopy(original)
        data["stories"][1]["headline"] = data["stories"][0]["headline"]
        data["stories"][1]["summary"] = data["stories"][0]["summary"]
        with self.assertRaisesRegex(ValueError, "Near-duplicate"):
            prepare_stories(data, set(), now=NOW)

    def test_bad_origin_or_missing_screen_fails(self):
        data = copy.deepcopy(package())
        data["stories"][0]["source_url"] = "https://unreviewed-news.example.org/story"
        with self.assertRaisesRegex(ValueError, "reviewed feed"):
            prepare_stories(data, set(), now=NOW)
        data = copy.deepcopy(package())
        data["stories"][0]["fact_check_status"] = "verified_true"
        with self.assertRaisesRegex(ValueError, "provenance"):
            prepare_stories(data, set(), now=NOW)
        data = copy.deepcopy(package())
        data["render_authorized"] = True
        with self.assertRaisesRegex(ValueError, "authorization"):
            prepare_stories(data, set(), now=NOW)

    def test_stale_source_and_future_article_rejected(self):
        for hours in (50, -2):
            data = copy.deepcopy(package())
            data["stories"][0]["published_at"] = (
                NOW - timedelta(hours=hours)
            ).isoformat()
            with self.assertRaisesRegex(ValueError, "Stale or future"):
                prepare_stories(data, set(), now=NOW)

    def test_publisher_names_are_source_derived(self):
        self.assertEqual(publisher_from_url("https://www.coindesk.com/markets/x"),
                         "CoinDesk")
        self.assertEqual(publisher_from_url("https://www.cnbc.com/x"), "CNBC")
        with self.assertRaises(ValueError):
            publisher_from_url("https://unknown.example.com/story")

    def test_actual_r71_frame_builder_accepts_fresh_date_and_prefix(self):
        with tempfile.TemporaryDirectory() as root:
            folder = Path(root)
            stories = prepare_stories(package(), set(), now=NOW)
            frames = draw_frames(stories, folder,
                                 display_date="NOV 23, 2026", prefix="R72")
            self.assertEqual(len(frames), 7)
            self.assertEqual([p.name for p in frames],
                             [f"R72_scene_{i:02d}.png" for i in range(1, 8)])
            for index, path in enumerate(frames, 1):
                self.assertTrue(path.is_file())
                self.assertTrue((folder / f"R72_artwork_{index:02d}.png").exists())


if __name__ == "__main__":
    unittest.main()
