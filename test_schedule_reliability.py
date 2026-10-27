"""Timezone-correct weekday schedule and one-time catch-up tests."""
import os
import unittest
from datetime import datetime
from unittest.mock import patch
from zoneinfo import ZoneInfo

from schedule_guard import expected_crons, should_run, valid_one_shot
from auto_publish_gate import verify_manifest_and_fingerprint
from publish_instagram import approval_fingerprint

TORONTO = ZoneInfo("America/Toronto")


class ScheduleReliabilityTests(unittest.TestCase):
    def test_two_independent_time_slots_in_ed_toronto(self):
        at_six = datetime(2026, 10, 27, 18, 14, tzinfo=TORONTO)
        at_seven = datetime(2026, 10, 27, 19, 14, tzinfo=TORONTO)
        self.assertTrue(should_run("schedule", at_six, "13 22 * * 1-5"))
        self.assertFalse(should_run("schedule", at_six, "13 0 * * 2-6"))
        self.assertTrue(should_run("schedule", at_seven, "13 23 * * 1-5"))
        self.assertFalse(should_run("schedule", at_seven, "0 22 * * 1-5"))
        self.assertEqual(len(expected_crons(at_six)), 2)

    def test_winter_utc_rollover_and_weekend(self):
        at_six = datetime(2026, 11, 2, 18, 14, tzinfo=TORONTO)
        at_seven = datetime(2026, 11, 2, 19, 14, tzinfo=TORONTO)
        self.assertTrue(should_run("schedule", at_six, "13 23 * * 1-5"))
        self.assertTrue(should_run("schedule", at_seven, "13 0 * * 2-6"))
        self.assertFalse(should_run("schedule", at_six, "13 22 * * 1-5"))
        sunday = datetime(2026, 11, 1, 19, 14, tzinfo=TORONTO)
        self.assertFalse(should_run("schedule", sunday, "13 0 * * 2-6"))

    def test_date_locked_one_shot_expires(self):
        monday = datetime(2026, 10, 26, 20, 0, tzinfo=TORONTO)
        tuesday = datetime(2026, 10, 27, 20, 0, tzinfo=TORONTO)
        self.assertTrue(valid_one_shot(monday))
        self.assertTrue(should_run("push", monday))
        self.assertFalse(valid_one_shot(tuesday))
        self.assertFalse(should_run("push", tuesday))

    def test_standard_catchup_manifest_does_not_reuse_quote(self):
        slides = [
            {"slide": index + 1,
             "image_url": f"https://res.cloudinary.com/demo/image/upload/{index}.jpg",
             "alt_text": "MarketRevamp news slide: sourced headline"}
            for index in range(7)
        ]
        manifest = {
            "slides": slides,
            "article_urls": [f"https://example.com/article-{i}" for i in range(7)],
            "caption": "Sources: example.com",
            "publish_enabled": True,
            "automated_checks_passed": True,
            "quote_card_first": False,
            "quote_card_count": 0,
        }
        images = [s["image_url"] for s in slides]
        fp = approval_fingerprint(manifest, images)
        with patch("auto_publish_gate.load_manifest", return_value=(manifest, images)):
            with patch.dict(os.environ, {"REQUIRE_STANDARD_CARDS": "true",
                                      "REQUIRE_QUOTE_FIRST": ""}):
                self.assertEqual(verify_manifest_and_fingerprint(fp), fp)
                manifest["quote_card_first"] = True
                with self.assertRaisesRegex(ValueError, "standard news cards"):
                    verify_manifest_and_fingerprint(fp)
                manifest["quote_card_first"] = False
                manifest["quote_card_count"] = 1
                with self.assertRaisesRegex(ValueError, "standard news cards"):
                    verify_manifest_and_fingerprint(fp)


if __name__ == "__main__":
    unittest.main()
