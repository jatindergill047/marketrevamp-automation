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
            "Open A I and B T C beat S and P five hundred. an-THROP-ik tracks Naz-dak.",
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

    def test_anchor_fallback_avoids_repeated_bridges_and_categories(self):
        stories = [{"headline": f"Headline {i}", "summary": "Verified detail.",
                    "category": "Blockchain"} for i in range(1, 8)]
        narrations = build_all(stories)
        self.assertEqual(narrations[0], "Headline 1. Verified detail.")
        self.assertEqual(narrations[6], "Headline 7. Verified detail.")
        self.assertTrue(all(not line.startswith("Blockchain.") for line in narrations))
        self.assertTrue(all("Meanwhile" not in line and "Next up" not in line
                            for line in narrations))

    def test_anchor_uses_reviewed_impact_but_not_dramatic_hook(self):
        story = {"headline": "New chip introduced", "summary": "The prototype uses less power.",
                 "editorial_hook": "A prototype could reshape the discussion",
                 "editorial_impact": "Independent testing is still pending"}
        self.assertEqual(
            build_narration(story, 3, 7),
            "New chip introduced. The prototype uses less power. Independent testing is still pending.",
        )

    def test_approved_script_remains_verbatim_for_later_story(self):
        story = {"headline": "Update", "summary": "Context",
                 "narration_text": "A carefully reviewed opening. The facts follow."}
        self.assertEqual(build_narration(story, 6, 7), story["narration_text"])

    def test_preview_categories_are_not_spoken_as_headlines(self):
        from reel_r14_preview import STORIES
        for category, headline, summary in STORIES:
            with self.subTest(category=category):
                self.assertNotEqual(category.casefold(), headline.casefold())
                narration = build_narration(
                    {"category": category, "headline": headline, "summary": summary}, 1, 7
                )
                self.assertTrue(narration.startswith(headline + "."))
                self.assertFalse(narration.startswith(category + "."))

    def test_missing_headline(self):
        for headline in ("", "  ", "🚀", None):
            with self.subTest(headline=headline):
                with self.assertRaises(ValueError):
                    build_narration({"headline": headline}, 1, 7)

    def test_all_stories(self):
        stories = [{"headline": "First", "summary": "One"}, {"headline": "Second", "summary": "Two"}]
        self.assertEqual(
            build_all(stories),
            ["First. One.", "Second. Two."],
        )


if __name__ == "__main__":
    unittest.main()
