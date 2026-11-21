"""Offline R46 release gate tests: no Cloudinary or Instagram requests."""
import datetime
import hashlib
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from reel_r46_launch_gate import ReleaseBlocked, authorize_publication, validate_and_fingerprint

NOW = datetime.datetime(2026, 11, 20, 19, 0, tzinfo=datetime.timezone(datetime.timedelta(hours=-5)))

def approved_stories():
    return [
        {"headline": f"Verified headline {i}", "narration_text": f"Verified narration for story {i}",
         "source_url": f"https://example.org/news/{i}", "editorial_approved": True,
         "fact_check_status": "source_supported"} for i in range(7)
    ]

def approved_metadata():
    return {"toronto_date": "2026-11-20", "editorial_approved": True,
            "visual_qa_approved": True, "audio_qa_approved": True,
            "official_logo_verified": True, "word_timing_origin": "tts_word_boundaries",
            "voice": "en-US-AndrewNeural", "reviewed_by": "Human editor",
            "caption": "Seven verified stories. Sources: listed below."}

class LaunchGateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.video = Path(self.temp.name) / "release.mp4"
        self.video.write_bytes(b"test-video-mocked-probe" * 90)
        self.mock_probe = patch("reel_r46_launch_gate.video_info", return_value={
            "duration_seconds": 82.4, "width": 1080, "height": 1920
        })
        self.mock_probe.start()
        self.addCleanup(self.mock_probe.stop)

    def verified(self, metadata=None, stories=None):
        return validate_and_fingerprint(metadata or approved_metadata(),
                                        stories or approved_stories(), self.video, now=NOW)

    def test_positive_review_and_fingerprint(self):
        result = self.verified()
        self.assertEqual(result["voice"], "en-US-AndrewNeural")
        self.assertEqual(len(result["source_urls"]), 7)
        self.assertEqual(len(result["release_fingerprint"]), 64)
        self.assertEqual(result["video_sha256"], hashlib.sha256(self.video.read_bytes()).hexdigest())
        self.assertTrue(authorize_publication(result, result["release_fingerprint"], {}, now=NOW))

    def test_r45_unapproved_cannot_pass(self):
        meta = approved_metadata()
        meta["editorial_approved"] = False
        with self.assertRaisesRegex(ReleaseBlocked, "Editorial approval"):
            self.verified(meta)

    def test_visual_logo_and_word_alignment_gates(self):
        for field, bad in [("visual_qa_approved", False), ("audio_qa_approved", False),
                           ("official_logo_verified", False),
                           ("word_timing_origin", "estimated"),
                           ("voice", "en-US-AvaNeural")]:
            with self.subTest(field=field):
                meta = approved_metadata()
                meta[field] = bad
                with self.assertRaises(ReleaseBlocked):
                    self.verified(meta)

    def test_rejects_stale_news(self):
        meta = approved_metadata()
        meta["toronto_date"] = "2026-11-19"
        with self.assertRaisesRegex(ReleaseBlocked, "stale"):
            self.verified(meta)

    def test_rejects_bad_source_duplicate_and_unapproved_article(self):
        for change in ("duplicate", "http", "approval", "fact_check"):
            with self.subTest(change=change):
                stories = approved_stories()
                if change == "duplicate":
                    stories[1]["source_url"] = stories[0]["source_url"]
                elif change == "http":
                    stories[0]["source_url"] = "http://example.org/news/0"
                elif change == "approval":
                    stories[0]["editorial_approved"] = False
                else:
                    stories[0]["fact_check_status"] = "verification_blocked"
                with self.assertRaises(ReleaseBlocked):
                    self.verified(stories=stories)

    def test_approval_must_match_exact_video(self):
        payload = self.verified()
        with self.assertRaisesRegex(ReleaseBlocked, "approval"):
            authorize_publication(payload, "0"*64, {}, now=NOW)
        with self.assertRaisesRegex(ReleaseBlocked, "already attempted"):
            authorize_publication(payload, payload["release_fingerprint"],
                                  {payload["release_fingerprint"]: {"status": "unknown"}}, now=NOW)

    def test_same_day_pending_reel_blocks_but_carousel_does_not(self):
        payload = self.verified()
        history = {"otherfingerprint": {"media_kind": "reel", "toronto_date": "2026-11-20", "status": "pending"}}
        with self.assertRaisesRegex(ReleaseBlocked, "pending or completed"):
            authorize_publication(payload, payload["release_fingerprint"], history, now=NOW)
        history["otherfingerprint"]["media_kind"] = "carousel"
        self.assertTrue(authorize_publication(payload, payload["release_fingerprint"], history, now=NOW))

    def test_malformed_history_fails_closed(self):
        payload = self.verified()
        with self.assertRaisesRegex(ReleaseBlocked, "Malformed"):
            authorize_publication(payload, payload["release_fingerprint"], {"a": None}, now=NOW)

if __name__ == "__main__":
    unittest.main()
