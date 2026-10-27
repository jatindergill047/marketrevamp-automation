"""Offline security regression for opt-in automatic Instagram publishing."""
import json
import os
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch
from zoneinfo import ZoneInfo

from auto_publish_gate import (
    get_source, verify_preparation_run, verify_manifest_and_fingerprint,
)
from publish_instagram import approval_fingerprint

NOW = datetime(2026, 10, 19, 21, 20, tzinfo=ZoneInfo("America/Toronto"))
GOOD_RUN = {
    "id": 39349690506,
    "name": "MarketRevamp Automation",
    "event": "schedule",
    "head_branch": "main",
    "conclusion": "success",
    "repository": {"full_name": "jatindergill047/marketrevamp-automation"},
    "created_at": "2026-10-20T00:47:08Z",
}


class AutoPublishGateTests(unittest.TestCase):
    def test_one_shot_requires_same_day_pinned_id_and_fingerprint(self):
        with tempfile.TemporaryDirectory() as directory:
            trigger = Path(directory) / "trigger"
            expected = "a" * 64
            trigger.write_text(json.dumps({
                "source_run_id": 39349690506,
                "toronto_date": "2026-10-19",
                "expected_fingerprint": expected,
            }), encoding="utf-8")
            self.assertEqual(get_source("push", trigger_path=trigger, now=NOW),
                             ("39349690506", expected))
            with self.assertRaisesRegex(ValueError, "different Toronto date"):
                get_source("push", trigger_path=trigger,
                           now=NOW.replace(day=20))
            with self.assertRaisesRegex(ValueError, "Malformed"):
                trigger.write_text(json.dumps({
                    "source_run_id": 123,
                    "toronto_date": "2026-10-19",
                    "expected_fingerprint": "wrong",
                }), encoding="utf-8")
                get_source("push", trigger_path=trigger, now=NOW)

    def test_scheduled_event_source_requires_numeric_id(self):
        self.assertEqual(get_source("workflow_run", 39349690506),
                         ("39349690506", ""))
        with self.assertRaises(ValueError):
            get_source("workflow_run", "")
        with self.assertRaises(ValueError):
            get_source("workflow_dispatch", "39349690506")

    def test_run_provenance_requires_successful_same_day_schedule(self):
        repo = GOOD_RUN["repository"]["full_name"]
        verify_preparation_run(GOOD_RUN, "39349690506", repo, now=NOW)
        for changes in (
            {"conclusion": "failure"}, {"event": "workflow_dispatch"},
            {"head_branch": "user-branch"}, {"id": 500},
            {"created_at": "2026-10-18T22:00:00Z"},
            {"repository": {"full_name": "attacker/repo"}},
        ):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                verify_preparation_run({**GOOD_RUN, **changes}, "39349690506",
                                       repo, now=NOW)

    @patch.dict(os.environ, {"REQUIRE_QUOTE_FIRST": "", "REQUIRE_STANDARD_CARDS": ""})
    def test_manifest_is_exactly_seven_and_prevalidated(self):
        # This generic fixture is intentionally not a quote-first manifest.
        # Its behavior must not depend on a live run's environment variables.
        slides = [
            {"slide": i + 1,
             "image_url": f"https://res.cloudinary.com/demo/image/upload/{i}.png",
             "alt_text": "Verified source graphic"}
            for i in range(7)
        ]
        manifest = {
            "slides": slides,
            "article_urls": [f"https://example.com/story{i}" for i in range(7)],
            "caption": "Sources: example.com",
            "publish_enabled": True,
            "automated_checks_passed": True,
        }
        urls = [s["image_url"] for s in slides]
        fp = approval_fingerprint(manifest, urls)
        with patch("auto_publish_gate.load_manifest",
                   return_value=(manifest, urls)):
            self.assertEqual(verify_manifest_and_fingerprint(fp), fp)
            with self.assertRaisesRegex(ValueError, "fingerprint changed"):
                verify_manifest_and_fingerprint("f" * 64)
            manifest["automated_checks_passed"] = False
            with self.assertRaisesRegex(ValueError, "checks"):
                verify_manifest_and_fingerprint(fp)
            manifest["automated_checks_passed"] = True
            manifest["publish_enabled"] = False
            with self.assertRaisesRegex(ValueError, "disabled"):
                verify_manifest_and_fingerprint(fp)

    def test_workflow_separates_scheduling_and_live_credentials(self):
        prep = Path(".github/workflows/marketrevamp.yml").read_text()
        auto = Path(".github/workflows/publish-automatic.yml").read_text()
        self.assertIn("MARKETREVAMP_SCHEDULE:", prep)
        self.assertNotIn("INSTAGRAM_ACCESS_TOKEN:", prep)
        self.assertNotIn("INSTAGRAM_APPROVED_FINGERPRINT:", prep)
        self.assertIn("workflow_run:", auto)
        self.assertIn("github.event.workflow_run.event == 'schedule'", auto)
        self.assertIn("github.event.workflow_run.conclusion == 'success'", auto)
        self.assertIn("marketrevamp-post-now.trigger", auto)
        self.assertIn("auto_publish_gate.py verify-run", auto)
        self.assertIn("auto_publish_gate.py authorize", auto)
        self.assertIn("INSTAGRAM_ACCESS_TOKEN:", auto)
        self.assertIn("INSTAGRAM_USER_ID:", auto)
        self.assertIn("test_publishing_flow.py", auto)
        self.assertIn("cancel-in-progress: false", auto)


if __name__ == "__main__":
    unittest.main()
