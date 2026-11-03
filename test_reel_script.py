"""Tests for Reel narration generation."""

import unittest

from reel_script import build_all, build_narration


class NarrationTests(unittest.TestCase):
    """Check pronunciation, cleanup and headline requirements."""

    def test_cleanup(self):
        result = build_narration(
            {"headline": "🚀 **OpenAI** and BTC beat S&P 500",
             "summary": "[Anthropic](https://example.com) tracks Nasdaq 📈"},
            1, 7,
        )
        self.assertEqual(
            result,
            "1 of 7. Open A I and B T C beat S and P five hundred. an-THROP-ik tracks Naz-dak",
        )

    def test_missing_headline(self):
        for headline in ("", "  ", "🚀", None):
            with self.subTest(headline=headline):
                with self.assertRaises(ValueError):
                    build_narration({"headline": headline}, 1, 7)

    def test_all_stories(self):
        stories = [{"headline": "First", "summary": "One"}, {"headline": "Second", "summary": "Two"}]
        self.assertEqual(
            build_all(stories),
            ["1 of 2. First. One", "2 of 2. Second. Two"],
        )


if __name__ == "__main__":
    unittest.main()
