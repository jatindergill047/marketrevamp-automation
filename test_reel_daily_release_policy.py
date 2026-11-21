"""R83 policy tests: no network, no publishing, no silent editorial bypass."""
import copy
import hashlib
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch
from zoneinfo import ZoneInfo

from reel_daily_release_policy import (APPROVED_CTA, APPROVED_HOOK,
                                       AUTO_POLICY, release_decision,
                                       validate_draft)
from reel_r46_launch_gate import ReleaseBlocked

NOW = datetime(2026, 11, 21, 15, tzinfo=ZoneInfo("America/Toronto"))
HOSTS = ("techcrunch.com", "arstechnica.com", "coindesk.com", "cnbc.com",
         "bbc.co.uk", "coindesk.com", "cnbc.com")
NAMES = ("TechCrunch", "Ars Technica", "CoinDesk", "CNBC",
         "BBC News", "CoinDesk", "CNBC")
CATEGORIES = ("AI", "Technology", "Crypto", "Markets",
              "Technology", "AI", "Markets")


def fixtures():
    urls = [f"https://{host}/news/2026/11/21/story-{i}"
            for i, host in enumerate(HOSTS, 1)]
    pending = {"status": "review_only", "version": "R72",
               "toronto_date": NOW.date().isoformat(),
               "editorial_approved": False, "published": False,
               "stories": []}
    sources = {"status": "review_only", "version": "R67",
               "toronto_date": NOW.date().isoformat(),
               "editorial_approved": False, "published": False,
               "cloudinary_uploaded": False,
               "instagram_published": False, "render_authorized": False,
               "story_count": 7, "stories": []}
    for i, (url, name, category) in enumerate(zip(urls, NAMES, CATEGORIES), 1):
        headline = f"Research project number {i} reports a new public technology update"
        pending["stories"].append({
            "headline": headline, "category": category,
            "source_url": url, "source_name": name,
            "narration_text": f"According to {name}, {headline.lower()}.",
            "fact_check_status": "source_supported_pending_editorial_approval",
            "editorial_approved": False,
        })
        sources["stories"].append({
            "headline": headline, "category": category,
            "source_url": url, "editorial_approved": False,
            "fact_check_status": "source_matched_not_independently_fact_checked",
            "published_at": (NOW - timedelta(hours=i)).isoformat(),
        })
    qa = {
        "status": "review_only", "version": "R72",
        "toronto_date": NOW.date().isoformat(),
        "editorial_approved": False, "published": False,
        "cloudinary_uploaded": False, "instagram_published": False,
        "synthetic_content": False, "real_source_headlines": True,
        "not_independently_fact_checked": True,
        "seven_scenes": 7, "presentation_segments": 9,
        "spoken_hook": APPROVED_HOOK, "spoken_follow_cta": APPROVED_CTA,
        "dimensions": "1080x1920", "video_codec": "h264",
        "audio_codec": "aac", "caption_font_size_px": 80,
        "subtitle_placement": "below_artwork",
        "alignment_token_ratio": 1.0, "tts_word_boundaries": 150,
        "duration_seconds": 84.0, "history_checked": True,
        "source_links": urls,
    }
    return qa, pending, sources


class AutomatedReleasePolicyTests(unittest.TestCase):
    def setUp(self):
        d = tempfile.TemporaryDirectory()
        self.addCleanup(d.cleanup)
        self.video = Path(d.name) / "test.mp4"
        self.video.write_bytes(b"synthetic-mp4-fixture" * 250)
        self.sha = hashlib.sha256(self.video.read_bytes()).hexdigest()
        self.qa, self.pending, self.sources = fixtures()
        video_info = patch("reel_r46_launch_gate.video_info", return_value={
            "duration_seconds": 84.0, "width": 1080, "height": 1920,
        })
        video_info.start()
        self.addCleanup(video_info.stop)

    def prepare(self, **kwargs):
        return validate_draft(self.qa, self.pending, self.sources,
                              self.video, kwargs.get("history", {}), now=NOW)

    def release(self, *, activation=None, history=None,
                first=False, approval="", now=NOW):
        return release_decision(self.qa, self.pending, self.sources, self.video,
                                {} if history is None else history,
                                activation=activation, first_live=first,
                                approved_video_sha256=approval, now=now)

    def test_source_data_valid_but_not_an_automatic_publish_approval(self):
        metadata, stories = self.prepare()
        self.assertEqual(len(stories), 7)
        self.assertTrue(all(s["editorial_approved"] is True for s in stories))
        self.assertEqual(metadata["editorial_review_mode"], AUTO_POLICY)
        self.assertIn("not independently fact-checked", metadata["caption"])
        with self.assertRaisesRegex(ReleaseBlocked, "owner authorization"):
            self.release(activation={})

    def test_first_live_exact_hash_and_source_qa_required(self):
        activation = {"owner_authorized": True, "policy": AUTO_POLICY,
                      "controlled_first_live": True, "first_video_sha256": self.sha}
        release = self.release(activation=activation, first=True,
                               approval=self.sha)
        self.assertTrue(release["first_live"])
        self.assertEqual(release["video_sha256"], self.sha)
        self.assertEqual(len(release["fingerprint"]), 64)
        with self.assertRaisesRegex(ReleaseBlocked, "exact reviewed video hash"):
            self.release(activation=activation, first=True, approval="0"*64)

    def test_unattended_requires_verified_first_live_instagram_readback(self):
        activation = {"owner_authorized": True, "policy": AUTO_POLICY,
                      "daily_enabled": True,
                      "verified_first_media_id": "17878336866585252"}
        with self.assertRaisesRegex(ReleaseBlocked, "readback"):
            self.release(activation=activation)
        prior = {"confirmed": {
            "media_kind": "reel", "status": "published",
            "toronto_date": "2026-11-20", "template_version": "R72",
            "instagram_media_id": "17878336866585252",
            "instagram_readback_verified": True,
            "article_urls": ["https://techcrunch.com/news/old"],
        }}
        result = self.release(activation=activation, history=prior)
        self.assertFalse(result["first_live"])
        prior["confirmed"]["instagram_readback_verified"] = False
        with self.assertRaisesRegex(ReleaseBlocked, "readback"):
            self.release(activation=activation, history=prior)

    def test_fail_closed_synthetic_or_stale_or_duplicates(self):
        self.qa["synthetic_content"] = True
        with self.assertRaisesRegex(ReleaseBlocked, "real source-screened"):
            self.prepare()
        self.qa["synthetic_content"] = False
        self.pending["toronto_date"] = "2026-11-20"
        with self.assertRaisesRegex(ReleaseBlocked, "Stale"):
            self.prepare()
        self.pending["toronto_date"] = NOW.date().isoformat()
        self.pending["stories"][1]["source_url"] = self.pending["stories"][0]["source_url"]
        with self.assertRaisesRegex(ReleaseBlocked, "differs"):
            self.prepare()

    def test_publication_history_rejects_recycled_and_unknown_outcomes(self):
        url = self.sources["stories"][0]["source_url"]
        with self.assertRaisesRegex(ReleaseBlocked, "Previously published"):
            self.prepare(history={"old": {
                "status": "published", "article_urls": [url]}})
        with self.assertRaisesRegex(ReleaseBlocked, "pending, unknown or published"):
            self.prepare(history={"pending": {
                "media_kind": "reel", "toronto_date": NOW.date().isoformat(),
                "status": "unknown"}})

    def test_fails_on_speech_drift_or_missing_publisher_attribution(self):
        self.qa["alignment_token_ratio"] = .95
        with self.assertRaisesRegex(ReleaseBlocked, "quality"):
            self.prepare()
        self.qa["alignment_token_ratio"] = 1.0
        self.pending["stories"][0]["narration_text"] = "A shocking story."
        with self.assertRaisesRegex(ReleaseBlocked, "attribution"):
            self.prepare()

if __name__ == "__main__":
    unittest.main()
