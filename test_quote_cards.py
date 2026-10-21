"""Offline safety tests for the single-quote-card preview experiment."""
import tempfile
import unittest
from pathlib import Path

from PIL import Image

import image_generator as ig
from quote_cards import (
    attributed_quote_candidates, best_quote, quote_matches_source,
    select_one_quote,
)
from quote_card_preview import draw_quote_card, render_trial

QUOTE = (
    "Independent audits have reduced deployment costs for smaller teams, "
    "but faster launches will still require clear privacy rules and "
    "additional customer safeguards."
)
ARTICLE = (
    'During a research briefing, Maya Chen said, “' + QUOTE +
    '” The company expects independent testing to continue next year.'
)
SUMMARY = (
    "The organization announced a pilot project involving software tools for "
    "enterprise customers. It described initial testing procedures and a "
    "schedule for reviewing results. Executives said more evaluation would "
    "be needed before broader deployment decisions are finalized."
)


def synthetic_stories():
    """Test-only invented examples; never substitute them for reported news."""
    rows = []
    for i in range(7):
        rows.append({
            "title": (
                "AI model release may reduce deployment costs for smaller teams"
                if i == 3 else
                f"Enterprise technology update for test slide number {i + 1}"
            ),
            "summary": SUMMARY,
            "summary_status": "ready_for_review",
            "selected_category": ("AI", "Technology", "Crypto", "Markets")[i % 4],
            "url": f"https://example.com/mock-news-{i + 1}",
            "published": "2026-10-20T15:00:00+00:00",
            "article_text": ARTICLE if i == 3 else
                            "No direct quotations appear in this demo source.",
        })
    return rows


class QuoteCardExperimentTests(unittest.TestCase):
    def test_literal_attributed_quote_is_selected(self):
        chosen = best_quote(ARTICLE, "deployment costs for small teams")
        self.assertIsNotNone(chosen)
        self.assertEqual(chosen["text"], QUOTE)
        self.assertEqual(chosen["speaker"], "Maya Chen")
        self.assertTrue(12 <= chosen["word_count"] <= 38)

    def test_post_quote_speaker_is_supported(self):
        article = "“" + QUOTE + "” said Maya Chen following the briefing."
        picked = best_quote(article)
        self.assertIsNotNone(picked)
        self.assertEqual(picked["speaker"], "Maya Chen")

    def test_unsupported_quote_rejected(self):
        self.assertIsNone(best_quote("“" + QUOTE + "”"))
        self.assertIsNone(best_quote("Chen said, “" + QUOTE + "”"))
        self.assertIsNone(best_quote("Maya Chen mentioned " + QUOTE))
        self.assertIsNone(best_quote("Maya Chen said, “A brief quote.”"))
        self.assertIsNone(best_quote(
            "Maya Chen said, “We are excited to announce another "
            "great opportunity that will change everything for customers "
            "and investors across the globe.”"
        ))

    def test_no_unsafe_rewritten_or_misattributed_quote(self):
        story = synthetic_stories()[3]
        original = best_quote(story["article_text"], story["title"])
        self.assertTrue(quote_matches_source(story, original))
        changed = dict(original, text=original["text"].replace(
            "reduced", "eliminated"))
        self.assertFalse(quote_matches_source(story, changed))
        changed_speaker = dict(original, speaker="Alex Smith")
        self.assertFalse(quote_matches_source(story, changed_speaker))
        with self.assertRaisesRegex(ValueError, "not supported"):
            draw_quote_card(story, 4, 7, "Oct 20, 2026", changed)

    def test_exactly_one_quote_across_seven(self):
        stories = synthetic_stories()
        stories[1]["article_text"] = ARTICLE
        idx, quote = select_one_quote(stories)
        self.assertIsNotNone(idx)
        self.assertIsNotNone(quote)
        self.assertIn(idx, (1, 3))
        self.assertEqual(quote["speaker"], "Maya Chen")
        self.assertEqual(select_one_quote(
            [{**s, "article_text": ""} for s in stories]), (None, None))
        with self.assertRaisesRegex(ValueError, "seven"):
            select_one_quote(stories[:6])

    def test_full_preview_render_is_one_quote_and_six_standard(self):
        stories = synthetic_stories()
        with tempfile.TemporaryDirectory() as d:
            result = render_trial(stories, d)
            self.assertEqual(result["quote_count"], 1)
            self.assertEqual(result["quote_slide"], 4)
            self.assertEqual(result["speaker"], "Maya Chen")
            self.assertEqual(len(list(Path(d).glob("slide_*.png"))), 7)
            self.assertTrue((Path(d) / "before_after.png").exists())
            quote = Image.open(Path(d) / "slide_04.png")
            self.assertEqual(quote.size, (1080, 1350))
            base = ig.draw_card(stories[0], 1, 7, "Oct 20, 2026")
            preview = Image.open(Path(d) / "slide_01.png")
            # Standard slide pixel content MUST remain identical.
            self.assertEqual(base.tobytes(), preview.tobytes())

    def test_zero_quote_fallback_stays_seven_standard_cards(self):
        stories = synthetic_stories()
        for story in stories:
            story["article_text"] = "No attributable direct quote exists."
        with tempfile.TemporaryDirectory() as d:
            result = render_trial(stories, d)
            self.assertEqual(result["quote_count"], 0)
            self.assertEqual(len(list(Path(d).glob("slide_*.png"))), 7)
            self.assertFalse((Path(d) / "quote_card_experiment.png").exists())


if __name__ == "__main__":
    unittest.main()
