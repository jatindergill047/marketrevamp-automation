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
            "article_urls": ["https://example.com/1", "https://example.com/2"],
            "slides": [{"slide": 1, "alt_text": "First"},
                       {"slide": 2, "alt_text": "Second"}],
        }
        original = approval_fingerprint(manifest, urls)
        self.assertEqual(len(original), 64)
        for field, changed in (
            ("caption", "Sources: another.com"),
            ("article_urls", ["https://example.com/3", "https://example.com/2"]),
            ("slides", [{"slide": 1, "alt_text": "Edited"},
                        {"slide": 2, "alt_text": "Second"}]),
        ):
            candidate = dict(manifest)
            candidate[field] = changed
            self.assertNotEqual(original, approval_fingerprint(candidate, urls))
        self.assertNotEqual(original, approval_fingerprint(manifest, list(reversed(urls))))

    def test_automatic_workflow_never_grants_publish_flag(self):
        production = Path(".github/workflows/marketrevamp.yml").read_text()
        manual = Path(".github/workflows/publish-approved.yml").read_text()
        self.assertIn("INSTAGRAM_PUBLISH_ENABLED: 'false'", production)
        self.assertNotIn("INSTAGRAM_ACCESS_TOKEN:", production)
        self.assertIn("workflow_dispatch:", manual)
        self.assertIn("INSTAGRAM_PUBLISH_ENABLED: 'true'", manual)
        self.assertIn("INSTAGRAM_APPROVED_FINGERPRINT:", manual)
        self.assertIn("marketrevamp-instagram-carousel", manual)
        self.assertIn('.head_branch == "main"', manual)


if __name__ == "__main__":
    unittest.main()
