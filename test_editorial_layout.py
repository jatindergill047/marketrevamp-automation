"""Offline regression tests for complete sentences and adaptive editorial layout."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from PIL import Image
import image_generator as ig


class EditorialRegressionTests(unittest.TestCase):
    def test_sentences_never_split_at_arbitrary_words(self):
        intro, details = ig._summary_parts(
            "Agents accessed confidential materials during testing. "
            "The regulator issued a warning on Thursday. "
            "Researchers described safeguards for affected teams."
        )
        self.assertEqual(intro, "Agents accessed confidential materials during testing.")
        self.assertEqual(len(details), 2)
        self.assertTrue(all(x.endswith(".") for x in details))

    def test_single_sentence_not_repeated_or_chopped(self):
        sentence = "A complete article sentence remains intact without an artificial cut."
        intro, details = ig._summary_parts(sentence)
        self.assertEqual(intro, "")
        self.assertEqual(details, [sentence])

    def test_article_date_not_collection_date(self):
        story = {"published": "2026-10-15T21:30:00+00:00"}
        self.assertEqual(ig._article_date(story, "Oct 17, 2026"), "ARTICLE DATE: OCT 15, 2026")
        self.assertEqual(ig._article_date({}, "Oct 17, 2026"), "EDITION: OCT 17, 2026")
        self.assertEqual(ig._article_date({"published": "invalid"}, "Oct 17, 2026"),
                         "EDITION: OCT 17, 2026")

    def test_varied_headlines_and_full_summary_render(self):
        summaries = [
            ("A first complete sentence explains the market development. "
             "A second sentence reports the regulator's response. "
             "A third sentence provides the date and background. "
             "A fourth sentence describes what market participants expect."),
            ("The company said its newest systems were being evaluated across multiple regions. "
             "Researchers reviewed the safety and operational results and described a plan "
             "for monitoring deployment in the months ahead.")
        ]
        with tempfile.TemporaryDirectory() as folder:
            logo = Path(folder) / "logo.png"
            Image.new("RGBA", (100, 100), (0, 150, 200, 255)).save(logo)
            with patch.object(ig, "LOGO", logo):
                for headline in (
                    "Bitcoin market update",
                    "International regulators announce extensive new technology guidelines "
                    "as major companies prepare for substantial changes",
                ):
                    for summary in summaries:
                        image = ig.draw_card({
                            "title": headline,
                            "summary": summary,
                            "summary_status": "ready_for_review",
                            "selected_category": "Markets",
                            "url": "https://example.com/article",
                            "published": "2026-10-15T21:30:00+00:00",
                        }, 1, 7, "Oct 17, 2026")
                        self.assertEqual(image.size, (1080, 1350))

    def test_single_detail_uses_feature_panel_not_fake_bullets(self):
        from PIL import ImageDraw
        sample = ("OpenAI said its models accessed two websites during an internal evaluation "
                  "and bypassed several company browsing restrictions. "
                  "The company disclosed the incidents in a public report on Thursday "
                  "and described how it was reviewing additional safeguards.")
        intro, details = ig._summary_parts(sample)
        self.assertEqual(len(details), 1)
        with tempfile.TemporaryDirectory() as folder:
            logo = Path(folder) / "logo.png"
            Image.new("RGBA", (100, 100), (0, 150, 200, 255)).save(logo)
            with patch.object(ig, "LOGO", logo):
                image = ig.draw_card({
                    "title": "OpenAI models hacked a crypto wallet and breached more websites",
                    "summary": sample,
                    "summary_status": "ready_for_review",
                    "selected_category": "AI",
                    "url": "https://example.com/story",
                }, 3, 7, "Oct 16, 2026")
        self.assertEqual(image.size, (1080, 1350))
        draw = ImageDraw.Draw(image)
        fit = ig._fit_editorial(draw,
                "OpenAI models hacked a crypto wallet and breached more websites",
                intro, details)
        section_y = fit[6]
        self.assertGreaterEqual(section_y, 780)
        self.assertEqual(image.getpixel((75, section_y + 80)), (239, 246, 249))
        self.assertEqual(image.getpixel((70, section_y + 90)), ig.CYAN)

    def test_no_publishing_with_invalid_summary(self):
        with self.assertRaisesRegex(ValueError, "invalid summary"):
            ig.draw_card({"title": "Test", "summary": "Too short."}, 1, 7, "Oct 17, 2026")


if __name__ == "__main__":
    unittest.main()
