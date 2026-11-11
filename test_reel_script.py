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

    def test_category_spoken_before_story(self):
        story = {"category": "Blockchain", "headline": "New settlement test",
                 "summary": "A pilot is underway."}
        self.assertEqual(
            build_narration(story, 1, 7),
            "New settlement test. A pilot is underway.",
        )

    def test_category_spoken_before_editor_approved_script(self):
        story = {"category": "Semiconductors", "headline": "Chip update",
                 "narration_text": "A prototype was introduced."}
        self.assertEqual(
            build_narration(story, 2, 7),
            "A prototype was introduced.",
        )

    def test_hybrid_editorial_varies_openers_without_categories(self):
        stories = [{"headline": f"Headline {i}", "summary": "Verified detail.",
                    "category": "Blockchain"} for i in range(1, 8)]
        narrations = build_all(stories)
        self.assertEqual(narrations[0], "Headline 1. Verified detail.")
        self.assertTrue(narrations[1].startswith("Meanwhile, another headline:"))
        self.assertTrue(narrations[2].startswith("Next up:"))
        self.assertTrue(narrations[3].startswith("Here's another development:"))
        self.assertTrue(narrations[4].startswith("Meanwhile, another headline:"))
        self.assertTrue(all(not line.startswith("Blockchain.") for line in narrations))

    def test_approved_script_remains_verbatim_for_later_story(self):
        story = {"headline": "Update", "summary": "Context",
                 "narration_text": "A carefully reviewed opening. The facts follow."}
        self.assertEqual(build_narration(story, 6, 7), story["narration_text"])

    def test_missing_headline(self):
        for headline in ("", "  ", "🚀", None):
            with self.subTest(headline=headline):
                with self.assertRaises(ValueError):
                    build_narration({"headline": headline}, 1, 7)

    def test_all_stories(self):
        stories = [{"headline": "First", "summary": "One"}, {"headline": "Second", "summary": "Two"}]
        self.assertEqual(
            build_all(stories),
            ["First. One", "Meanwhile, another headline: Second. Two"],
        )


if __name__ == "__main__":
    unittest.main()
