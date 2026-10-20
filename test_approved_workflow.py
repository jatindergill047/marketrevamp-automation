"""Offline checks for artifact approval and manual publishing separation."""
import unittest
from pathlib import Path

from publish_instagram import approval_fingerprint


class ApprovedWorkflowTests(unittest.TestCase):
    def test_review_hash_binds_entire_carousel(self):
        urls = ["https://res.cloudinary.com/demo/image/upload/a.jpg",
                "https://res.cloudinary.com/demo/image/upload/b.jpg"]
        manifest = {
            "caption": "Sources: example.com",
            "first_comment": "#MarketRevamp #AI",
            "article_urls": ["https://example.com/1", "https://example.com/2"],
            "slides": [{"slide": 1, "alt_text": "First"},
                       {"slide": 2, "alt_text": "Second"}],
        }
        original = approval_fingerprint(manifest, urls)
        self.assertEqual(len(original), 64)
        for field, changed in (
            ("caption", "Sources: another.com"),
            ("first_comment", "#MarketRevamp #Blockchain"),
            ("article_urls", ["https://example.com/3", "https://example.com/2"]),
            ("slides", [{"slide": 1, "alt_text": "Edited"},
                        {"slide": 2, "alt_text": "Second"}]),
        ):
            candidate = dict(manifest)
            candidate[field] = changed
            self.assertNotEqual(original, approval_fingerprint(candidate, urls))
        self.assertNotEqual(original, approval_fingerprint(manifest, list(reversed(urls))))

    def test_manual_validation_workflows_have_no_live_side_effects(self):
        for filename in ("test-instagram-carousel.yml", "test-history.yml"):
            content = (Path(".github/workflows") / filename).read_text()
            self.assertIn("contents: read", content)
            self.assertNotIn("INSTAGRAM_ACCESS_TOKEN:", content)
            self.assertNotIn("INSTAGRAM_USER_ID:", content)
            self.assertNotIn("publishing-history", content)
            self.assertNotIn("test_instagram_carousel.py", content)
            self.assertNotIn("test_history_persistence.py", content)
            self.assertIn("python -m unittest", content)

    def test_scheduled_workflow_still_blocks_unapproved_posts(self):
        production = Path(".github/workflows/marketrevamp.yml").read_text()
        manual = Path(".github/workflows/publish-approved.yml").read_text()
        self.assertIn("INSTAGRAM_PUBLISH_ENABLED: 'true'", production)
        self.assertNotIn("INSTAGRAM_APPROVED_FINGERPRINT:", production)
        self.assertNotIn("INSTAGRAM_USER_ID:", production)
        self.assertIn("Verify unapproved carousel is blocked", production)
        self.assertNotIn("INSTAGRAM_ACCESS_TOKEN:", production)
        self.assertIn("workflow_dispatch:", manual)
        self.assertIn("INSTAGRAM_PUBLISH_ENABLED: 'true'", manual)
        self.assertIn("INSTAGRAM_APPROVED_FINGERPRINT:", manual)
        self.assertIn("marketrevamp-instagram-carousel", manual)
        self.assertIn('.head_branch == "main"', manual)


if __name__ == "__main__":
    unittest.main()
