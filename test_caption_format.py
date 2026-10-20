"""Ensure every new MarketRevamp caption includes readable, safe hashtags."""
import unittest
from pathlib import Path

from caption_format import CAPTION_LIMIT, HASHTAGS, compose_caption


class CaptionFormatTests(unittest.TestCase):
    def test_hashtags_follow_sources_and_disclaimer_once(self):
        lines = [
            "🚀 MARKETREVAMP | DAILY NEWS BRIEF",
            "1. AI safety announcement",
            "Source: techcrunch.com",
            "",
            "2. Bitcoin markets update",
            "Source: coindesk.com",
            "",
            "Follow @marketrevampdaily for daily updates.",
            "",
            "News and information only. Not investment advice.",
        ]
        caption = compose_caption(lines)
        self.assertTrue(caption.endswith("\n\n" + HASHTAGS))
        self.assertEqual(caption.count(HASHTAGS), 1)
        self.assertEqual(len(HASHTAGS.split()), 6)
        self.assertIn("Source: techcrunch.com", caption)
        self.assertIn("Source: coindesk.com", caption)
        self.assertIn("Not investment advice.", caption)
        self.assertLessEqual(len(caption), CAPTION_LIMIT)

    def test_exact_limit_passes_and_over_limit_fails_closed(self):
        space = CAPTION_LIMIT - len(HASHTAGS) - 2
        self.assertEqual(len(compose_caption(["A" * space])), CAPTION_LIMIT)
        with self.assertRaisesRegex(ValueError, "2,200"):
            compose_caption(["A" * (space + 1)])

    def test_production_manifest_uses_caption_and_no_first_comment(self):
        code = Path("prepare_instagram_carousel.py").read_text(encoding="utf-8")
        self.assertIn("caption = compose_caption(caption_lines)", code)
        self.assertIn('first_comment = ""', code)
        self.assertNotIn('first_comment = "#MarketRevamp', code)


if __name__ == "__main__":
    unittest.main()
