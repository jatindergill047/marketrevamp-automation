"""Offline regression for opt-in Sunday live quote-first carousel safeguards."""
import os
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch
from zoneinfo import ZoneInfo

import image_generator as ig
from auto_publish_gate import verify_manifest_and_fingerprint, verify_preparation_run
from quote_cards import quote_matches_source
from quote_first import promote_quote_to_first, verify_quote_first
from news_quality import select_usable
from quote_card_preview import draw_quote_card
from schedule_guard import should_run, valid_one_shot
from test_quote_cards import synthetic_stories


TORONTO = ZoneInfo("America/Toronto")
SUNDAY = datetime(2026, 10, 25, 19, 0, tzinfo=TORONTO)
MONDAY = datetime(2026, 10, 26, 10, 0, tzinfo=TORONTO)


class LiveQuoteFirstTests(unittest.TestCase):
    def test_exactly_one_source_quote_promoted_from_middle_to_first(self):
        stories = synthetic_stories()
        urls_before = [s["url"] for s in stories]
        result = promote_quote_to_first(stories)
        self.assertTrue(verify_quote_first(result))
        self.assertEqual(result[0]["url"], urls_before[3])
        self.assertEqual([s["url"] for s in result[1:]],
                         urls_before[:3] + urls_before[4:])
        self.assertEqual(len(result), 7)
        self.assertEqual(sum(bool(s.get("quote_card")) for s in result), 1)
        self.assertTrue(quote_matches_source(result[0],
                                              result[0]["quote_card"]))
        self.assertNotIn("quote_card", stories[3])

    def test_backup_source_used_when_initial_seven_lack_quotes(self):
        from test_news_quality import GOOD_SUMMARY
        from test_quote_cards import ARTICLE
        candidates = []
        distinct_titles = (
            "Nvidia announces enterprise accelerator hardware",
            "Microsoft expands robotics cloud partnerships",
            "Apple launches accessibility keyboard features",
            "Google publishes quantum processor benchmarking results",
            "Tesla introduces charging adapter design",
            "Amazon updates warehouse scheduling software",
            "Meta demonstrates new wearable neural interface",
            "Anthropic releases developer programming tools",
        )
        for i in range(8):
            domain = ("first.com" if i < 3 else
                      "second.com" if i < 6 else "third.com")
            candidates.append({
                "title": distinct_titles[i],
                "category": "Technology",
                "url": f"https://{domain}/news/{i}",
                "published": "2026-10-25T15:00:00+00:00",
                "score": 50 - i,
            })
        def extract(url):
            return GOOD_SUMMARY + (" " + ARTICLE if url.endswith("/7") else "")
        selected = select_usable(
            candidates, lambda story: "Technology",
            extract, lambda text, headline: GOOD_SUMMARY,
            require_quote=True,
        )
        self.assertEqual(len(selected), 7)
        promoted = promote_quote_to_first(selected)
        self.assertTrue(promoted[0]["url"].endswith("/7"))
        self.assertTrue(verify_quote_first(promoted))

    def test_no_quote_never_creates_published_carousel(self):
        cases = synthetic_stories()
        for s in cases:
            s["article_text"] = "The source has no clearly attributed quote."
        with self.assertRaisesRegex(ValueError, "No safe directly attributed"):
            promote_quote_to_first(cases)
        with self.assertRaisesRegex(ValueError, "quote"):
            verify_quote_first(cases)

    def test_live_quote_requires_opt_in_and_is_not_watermarked(self):
        story = promote_quote_to_first(synthetic_stories())[0]
        # Production runs set the job-level opt-in; explicitly clear it
        # while verifying the default-off behavior in this unit test.
        with patch.dict(os.environ, {"MARKETREVAMP_QUOTE_FIRST": ""}):
            with self.assertRaisesRegex(ValueError, "explicit slide-1 opt-in"):
                ig.draw_card(story, 1, 7, "Oct 25, 2026")
        with patch.dict(os.environ, {"MARKETREVAMP_QUOTE_FIRST": "true"}):
            live = ig.draw_card(story, 1, 7, "Oct 25, 2026")
        preview = draw_quote_card(story, 1, 7, "Oct 25, 2026",
                                  story["quote_card"], experimental=True)
        self.assertEqual(live.size, (1080, 1350))
        self.assertEqual(live.crop((200, 30, 900, 200)).tobytes(),
                         preview.crop((200, 30, 900, 200)).tobytes())
        self.assertNotEqual(live.crop((67, 1145, 650, 1196)).tobytes(),
                            preview.crop((67, 1145, 650, 1196)).tobytes())
        with patch.dict(os.environ, {"MARKETREVAMP_QUOTE_FIRST": "true"}):
            with self.assertRaisesRegex(ValueError, "explicit slide-1 opt-in"):
                ig.draw_card(story, 2, 7, "Oct 25, 2026")

    def test_one_shot_cannot_recur_after_pinned_date(self):
        self.assertTrue(valid_one_shot(SUNDAY))
        self.assertTrue(should_run("push", now=SUNDAY))
        self.assertFalse(valid_one_shot(MONDAY))
        self.assertFalse(should_run("push", now=MONDAY))
        self.assertTrue(should_run("workflow_dispatch", now=MONDAY))

    def test_one_shot_publishing_rejects_nonmatching_preparation(self):
        approved = {
            "id": 91919, "name": "MarketRevamp Automation", "event": "push",
            "head_branch": "main", "conclusion": "success",
            "repository": {"full_name": "jatindergill047/marketrevamp-automation"},
            "created_at": "2026-10-25T22:30:00Z",
        }
        repo = approved["repository"]["full_name"]
        verify_preparation_run(approved, "91919", repo, now=SUNDAY)
        for wrong in (
            {"event": "workflow_dispatch"},
            {"head_branch": "test"},
            {"conclusion": "failure"},
            {"created_at": "2026-10-24T22:30:00Z"},
        ):
            with self.subTest(change=wrong), self.assertRaises(ValueError):
                verify_preparation_run({**approved, **wrong},
                                       "91919", repo, now=SUNDAY)
        with self.assertRaises(ValueError):
            verify_preparation_run(approved, "91919", repo, now=MONDAY)

    def test_auto_publisher_rejects_missing_quote_first_attestation(self):
        slides = [{"slide": i + 1,
                   "image_url": f"https://res.cloudinary.com/demo/image/upload/{i}.jpg",
                   "alt_text": ("MarketRevamp attributed quote card: test"
                                if i == 0 else "MarketRevamp news slide: test")}
                  for i in range(7)]
        urls = [s["image_url"] for s in slides]
        manifest = {"slides": slides, "article_urls": [f"https://example.com/{i}"
                                                      for i in range(7)],
                    "publish_enabled": True, "automated_checks_passed": True,
                    "caption": "Source-backed test", "quote_card_first": True,
                    "quote_card_count": 1}
        with patch("auto_publish_gate.load_manifest",
                   return_value=(manifest, urls)), patch.dict(
                       os.environ, {"REQUIRE_QUOTE_FIRST": "true"}):
            fp = verify_manifest_and_fingerprint()
            self.assertEqual(len(fp), 64)
            for field, value in (("quote_card_first", False),
                                 ("quote_card_count", 0)):
                manifest[field] = value
                with self.assertRaisesRegex(ValueError, "quote"):
                    verify_manifest_and_fingerprint()
                manifest[field] = True if field == "quote_card_first" else 1
            manifest["slides"][0]["alt_text"] = "MarketRevamp news slide: test"
            with self.assertRaisesRegex(ValueError, "quote"):
                verify_manifest_and_fingerprint()


if __name__ == "__main__":
    unittest.main()
