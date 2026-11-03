"""Offline R8 approval and authorization regressions."""
import copy
import os
import unittest
from unittest.mock import patch

from publish_instagram import approval_fingerprint
from auto_publish_gate import verify_manifest_and_fingerprint


def fixture():
    slides = [{"slide": i + 1, "image_url": f"https://res.cloudinary.com/demo/image/upload/{i}.jpg", "alt_text": f"Story {i}"} for i in range(7)]
    manifest = {"slides": slides, "article_urls": [f"https://example.com/{i}" for i in range(7)], "caption": "MarketRevamp news", "first_comment": "", "publish_enabled": True, "automated_checks_passed": True, "media_type": "CAROUSEL"}
    return manifest, [s["image_url"] for s in slides]


class ReelSecurityTests(unittest.TestCase):
    def test_carousel_fingerprint_unchanged(self):
        manifest, urls = fixture()
        self.assertEqual(approval_fingerprint(manifest, urls), approval_fingerprint({**manifest, "media_kind": "carousel"}, urls))

    def test_reel_changes_fingerprint(self):
        manifest, urls = fixture()
        old = approval_fingerprint(manifest, urls)
        manifest["media_kind"] = "reel"
        manifest["reel"] = {"video_url": "https://res.cloudinary.com/demo/video/upload/reel.mp4", "cover_url": urls[0], "duration_seconds": 44, "caption": manifest["caption"]}
        fingerprint = approval_fingerprint(manifest, urls)
        self.assertNotEqual(old, fingerprint)
        changed = copy.deepcopy(manifest)
        changed["reel"]["duration_seconds"] = 45
        self.assertNotEqual(fingerprint, approval_fingerprint(changed, urls))
        changed["reel"]["video_url"] = "https://evil.example/video/upload/reel.mp4"
        with self.assertRaises(ValueError):
            approval_fingerprint(changed, urls)

    def test_gate_requires_opt_in_and_exact_fingerprint(self):
        manifest, urls = fixture()
        manifest["media_kind"] = "reel"
        manifest["reel"] = {"video_url": "https://res.cloudinary.com/demo/video/upload/reel.mp4", "cover_url": urls[0], "duration_seconds": 44, "caption": manifest["caption"]}
        fingerprint = approval_fingerprint(manifest, urls)
        with patch("auto_publish_gate.load_manifest", return_value=(manifest, urls)):
            with patch.dict(os.environ, {"REEL_ENABLED": "false", "REQUIRE_QUOTE_FIRST": "", "REQUIRE_STANDARD_CARDS": ""}):
                with self.assertRaisesRegex(ValueError, "REEL_ENABLED"):
                    verify_manifest_and_fingerprint(fingerprint)
            with patch.dict(os.environ, {"REEL_ENABLED": "true", "REQUIRE_QUOTE_FIRST": "", "REQUIRE_STANDARD_CARDS": ""}):
                self.assertEqual(verify_manifest_and_fingerprint(fingerprint), fingerprint)
                with self.assertRaisesRegex(ValueError, "fingerprint changed"):
                    verify_manifest_and_fingerprint("f" * 64)


if __name__ == "__main__":
    unittest.main()
