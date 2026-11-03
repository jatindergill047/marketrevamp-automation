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
            "Open A I and B T C beat S and P five hundred. an-THROP-ik tracks Naz-dak",
        )

    def test_storytelling_script_overrides_headline_summary(self):
        story = {
            "headline": "AI research",
            "summary": "An evaluation update",
            "narration_text": "Here's what changed. Researchers are testing a new evaluation approach. The question is how well it works in practice.",
        }
        self.assertEqual(build_narration(story, 1, 7), story["narration_text"])

    def test_missing_headline(self):
        for headline in ("", "  ", "🚀", None):
            with self.subTest(headline=headline):
                with self.assertRaises(ValueError):
                    build_narration({"headline": headline}, 1, 7)

    def test_all_stories(self):
        stories = [{"headline": "First", "summary": "One"}, {"headline": "Second", "summary": "Two"}]
        self.assertEqual(
            build_all(stories),
            ["First. One", "Second. Two"],
        )


if __name__ == "__main__":
    unittest.main()
