"""Offline regression tests for unified summary and responsive editorial cards."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from PIL import Image, ImageDraw
import image_generator as ig


FIRST = (
    "Elorian, the Palo Alto AI startup that raised a $55 million seed round "
    "at a $300 million valuation before it launched a product, released its "
    "first model on Friday, TechCrunch has exclusively learned."
)
SECOND = (
    "The model, Glimpse, is launching as a research preview with API access "
    "and a chat interface."
)
SUMMARY = FIRST + " " + SECOND


class EditorialRegressionTests(unittest.TestCase):
    def test_article_date_not_collection_date(self):
        story = {"published": "2026-10-15T21:30:00+00:00"}
        self.assertEqual(ig._article_date(story, "Oct 17, 2026"),
                         "ARTICLE DATE: OCT 15, 2026")
        self.assertEqual(ig._article_date({}, "Oct 17, 2026"),
                         "EDITION: OCT 17, 2026")
        self.assertEqual(ig._article_date({"published": "invalid"}, "Oct 17, 2026"),
                         "EDITION: OCT 17, 2026")

    def test_complete_summary_is_one_unbroken_block(self):
        draw = ImageDraw.Draw(Image.new("RGB", (1080, 1350), "white"))
        fit = ig._fit_editorial(
            draw,
            "Elorian’s first AI model wants to reason with images, not just about them",
            SUMMARY,
        )
        headline_face, headline_lines, headline_leading, section_y, summary_face, lines, leading, text_y, bottom = fit
        self.assertEqual(" ".join(lines), SUMMARY)
        self.assertGreater(section_y, 300 + len(headline_lines) * headline_leading)
        self.assertEqual(text_y, section_y + 77)
        self.assertLess(bottom, 1170)
        self.assertLess(bottom - text_y, 400)  # no huge empty card

    def test_one_sentence_remains_in_same_summary_section(self):
        draw = ImageDraw.Draw(Image.new("RGB", (1080, 1350), "white"))
        fit = ig._fit_editorial(draw, "AI startup launches new model", FIRST)
        self.assertEqual(" ".join(fit[5]), FIRST)

    def test_varied_headlines_and_full_summary_render(self):
        with tempfile.TemporaryDirectory() as folder:
            logo = Path(folder) / "logo.png"
            Image.new("RGBA", (100, 100), (0, 150, 200, 255)).save(logo)
            with patch.object(ig, "LOGO", logo):
                for headline in (
                    "Bitcoin market update",
                    "International regulators announce extensive new technology guidelines "
                    "as major companies prepare for substantial changes",
                    "Elorian’s first AI model wants to reason with images, not just about them",
                ):
                    image = ig.draw_card({
                        "title": headline,
                        "summary": SUMMARY,
                        "summary_status": "ready_for_review",
                        "selected_category": "AI",
                        "url": "https://example.com/article",
                        "published": "2026-10-15T21:30:00+00:00",
                    }, 6, 7, "Oct 17, 2026")
                    self.assertEqual(image.size, (1080, 1350))

    def test_decorative_engraving_only_uses_available_space(self):
        from newspaper_design import draw_editorial_illustration
        image = Image.new("RGB", (1080, 1350), (249, 248, 245))
        before = image.copy()
        self.assertTrue(draw_editorial_illustration(image, 848, 6, "AI"))
        # Header, summary and source/footer are untouched by the illustration.
        for point in ((100, 500), (100, 800), (200, 1201), (800, 1270)):
            self.assertEqual(image.getpixel(point), before.getpixel(point))
        self.assertNotEqual(image.getpixel((67, 878)), before.getpixel((67, 878)))
        dense = Image.new("RGB", (1080, 1350), (249, 248, 245))
        self.assertFalse(draw_editorial_illustration(dense, 1050, 6, "AI"))
        self.assertEqual(dense.tobytes(), before.tobytes())

    def test_category_illustrations_are_distinct_and_preserve_text(self):
        from newspaper_design import draw_editorial_illustration
        rendered = []
        for category in ("AI", "Technology", "Crypto", "Markets"):
            image = Image.new("RGB", (1080, 1350), (249, 248, 245))
            before = image.copy()
            self.assertTrue(draw_editorial_illustration(image, 850, 2, category))
            # Only the editorial area between summary and footer may change.
            self.assertEqual(image.crop((0, 0, 1080, 875)).tobytes(),
                             before.crop((0, 0, 1080, 875)).tobytes())
            self.assertEqual(image.crop((0, 1174, 1080, 1350)).tobytes(),
                             before.crop((0, 1174, 1080, 1350)).tobytes())
            rendered.append(image.crop((500, 930, 1013, 1174)).tobytes())
        self.assertEqual(len(set(rendered)), 4)

    def test_long_summary_skips_artwork_without_modifying_pixels(self):
        from newspaper_design import draw_editorial_illustration
        image = Image.new("RGB", (1080, 1350), (249, 248, 245))
        original = image.tobytes()
        for category in ("AI", "Technology", "Crypto", "Markets"):
            self.assertFalse(draw_editorial_illustration(image, 1050, 2, category))
            self.assertEqual(image.tobytes(), original)

    def test_newspaper_background_is_deterministic(self):
        from newspaper_design import newspaper_background
        first = newspaper_background(6)
        second = newspaper_background(6)
        self.assertEqual(first.tobytes(), second.tobytes())

    def test_no_publishing_with_invalid_summary(self):
        with self.assertRaisesRegex(ValueError, "invalid summary"):
            ig.draw_card({"title": "Test", "summary": "Too short."}, 1, 7, "Oct 17, 2026")


if __name__ == "__main__":
    unittest.main()
