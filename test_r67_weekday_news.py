"""Offline R67 source selection, history dedupe and never-publish tests."""
import copy
import json
import os
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo
from unittest.mock import patch

from r67_weekday_news import load_published_history, review_package, main

NOW = datetime(2026, 11, 20, 16, tzinfo=ZoneInfo("America/Toronto"))
TOPICS = ("AI", "Technology", "Crypto", "Markets")
HEADLINES = (
    "AI model safety trial begins for enterprise systems",
    "Chipmaker signs robotics semiconductor research agreement",
    "Bitcoin protocol developers propose testing changes",
    "Treasury bond auction signals rate expectations",
    "Cloud cybersecurity firm launches new monitoring tool",
    "Ethereum validator upgrade enters testing phase",
    "Market analysts evaluate new equity index methodology",
)
SENTENCE = "According to the publisher, the company introduced its new technical project after a series of preliminary trials, with additional evaluation expected before any wider public release."
SUMMARY = (SENTENCE + " " + SENTENCE)


def story(i):
    return {
        "title": HEADLINES[i], "url": f"https://example.org/news/{i}?utm_source=test",
        "selected_category": TOPICS[i % 4],
        "published": (NOW - timedelta(hours=i+1)).isoformat(),
        "summary": SUMMARY, "article_text": SUMMARY,
        "summary_screening": {"passed": True, "reason": "source_matched_not_fact_checked"},
        "screening_passed": True, "fact_checked": False,
        "feed_name": "Offline test publisher",
        "corroboration_status": "single_source",
    }


def sample():
    return {"selected_count": 7, "selected_stories": [story(i) for i in range(7)],
            "feed_status": {"AI": {"status": "success", "articles": 12}}}


class R67Tests(unittest.TestCase):
    def setUp(self):
        self.package = sample()

    def review(self, data=None, history=None, now=NOW):
        return review_package(data if data is not None else self.package,
                              history if history is not None else set(), now=now)

    def test_complete_review_only_package(self):
        value = self.review()
        self.assertEqual(value["story_count"], 7)
        self.assertEqual(value["toronto_date"], "2026-11-20")
        self.assertEqual(len(value["stories"]), 7)
        self.assertEqual(len({s["source_url"] for s in value["stories"]}), 7)
        self.assertTrue(all(s["editorial_approved"] is False for s in value["stories"]))
        for key in ("published", "editorial_approved", "cloudinary_uploaded",
                    "instagram_published", "render_authorized"):
            self.assertIs(value[key], False)

    def test_weekend_reviews_allowed_with_fresh_source_articles(self):
        for days, hour in ((1, 16), (2, 16)):  # Saturday and Sunday in Toronto
            when = NOW + timedelta(days=days)
            data = copy.deepcopy(self.package)
            for index, item in enumerate(data["selected_stories"]):
                item["published"] = (
                    when - timedelta(hours=index+1)
                ).isoformat()
            outcome = self.review(data=data, now=when)
            self.assertEqual(outcome["toronto_date"], when.date().isoformat())
            self.assertEqual(outcome["story_count"], 7)
            self.assertFalse(outcome["render_authorized"])
            self.assertFalse(outcome["instagram_published"])

    def test_seven_required(self):
        data=copy.deepcopy(self.package)
        data["selected_stories"].pop()
        data["selected_count"] = 6
        with self.assertRaisesRegex(ValueError, "Exactly seven"):
            self.review(data)

    def test_published_article_rejected_even_with_tracking_query(self):
        with self.assertRaisesRegex(ValueError, "published or repeated"):
            self.review(history={"https://example.org/news/1"})

    def test_duplicate_selected_url_rejected(self):
        data=copy.deepcopy(self.package)
        data["selected_stories"][1]["url"] = data["selected_stories"][0]["url"]
        with self.assertRaisesRegex(ValueError, "published or repeated"):
            self.review(data)

    def test_duplicate_story_event_rejected(self):
        data=copy.deepcopy(self.package)
        data["selected_stories"][1]["title"] = data["selected_stories"][0]["title"]
        with self.assertRaisesRegex(ValueError, "Overlapping"):
            self.review(data)

    def test_stale_or_future_article_refused(self):
        for hours in (49, -1):
            data=copy.deepcopy(self.package)
            data["selected_stories"][0]["published"]=(NOW-timedelta(hours=hours)).isoformat()
            with self.assertRaisesRegex(ValueError, "48-hour"):
                self.review(data)

    def test_unsupported_source_fails(self):
        data=copy.deepcopy(self.package)
        data["selected_stories"][0]["summary_screening"]["passed"]=False
        with self.assertRaisesRegex(ValueError, "Summary not supported"):
            self.review(data)

    def test_no_factual_verification_claim(self):
        value=self.review()
        self.assertEqual(value["stories"][0]["fact_check_status"],
                         "source_matched_not_independently_fact_checked")

    def test_no_successful_feed_refused(self):
        data=copy.deepcopy(self.package)
        data["feed_status"] = {"AI": {"status": "error"}}
        with self.assertRaisesRegex(ValueError, "No successful"):
            self.review(data)

    def test_live_collector_receives_authoritative_history_as_path(self):
        # Regression for GitHub run 44942315300: a string made the
        # collector's published_article_urls(...) crash before any rendering.
        with tempfile.TemporaryDirectory() as root:
            before = Path.cwd()
            try:
                os.chdir(root)
                Path("news_results.json").write_text("{}")
                Path("history.json").write_text("{}")
                with patch("news_collector.collect_news") as collect, \
                     patch("r67_weekday_news.review_package",
                           return_value={"status": "review_only",
                                         "toronto_date": "2026-11-21",
                                         "story_count": 7}):
                    main(["--history", "history.json", "--output", "output.json"])
                    collect.assert_called_once()
                    self.assertEqual(collect.call_args.kwargs["history_path"],
                                     Path("history.json"))
                    self.assertTrue(callable(collect.call_args.kwargs["extractor"]))
                    self.assertEqual(json.loads(Path("output.json").read_text()),
                                     {"status": "review_only",
                                      "toronto_date": "2026-11-21",
                                      "story_count": 7})
            finally:
                os.chdir(before)

    def test_authoritative_history_parsing_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/"history.json"
            path.write_text(json.dumps({
                "published": {"status": "published",
                              "article_urls": ["https://example.org/news/1?ref=ads"]},
                "draft": {"status": "draft", "article_urls": ["https://example.org/draft"]},
            }))
            self.assertEqual(load_published_history(path), {"https://example.org/news/1"})
            path.write_text('{"oops": {"status":"published"}}')
            with self.assertRaisesRegex(ValueError, "missing article URL"):
                load_published_history(path)


if __name__ == "__main__":
    unittest.main()
