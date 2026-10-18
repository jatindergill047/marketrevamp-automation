"""Offline regression tests for unified summary and responsive editorial cards."""
import unittest
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

    def test_larger_summary_font_keeps_full_text_and_safe_bounds(self):
        draw = ImageDraw.Draw(Image.new("RGB", (1080, 1350), "white"))
        headline = "Who profits as tokenization expands across financial markets?"
        short_copy = (
            "The analysis said custody providers and asset managers could earn "
            "service fees by helping issuers move securities onto token networks. "
            "Infrastructure platforms may also receive revenue for processing "
            "digital transfers on behalf of participating institutions."
        )
        fit = ig._fit_editorial(draw, headline, short_copy)
        self.assertGreaterEqual(fit[4].size, 32)
        self.assertEqual(" ".join(fit[5]), short_copy)
        self.assertLessEqual(fit[8], 1170)
        # A long fully sourced summary must still fit without truncation.
        long_copy = " ".join([short_copy, short_copy])
        long_fit = ig._fit_editorial(draw, headline, long_copy)
        self.assertGreaterEqual(long_fit[4].size, 22)
        self.assertEqual(" ".join(long_fit[5]), long_copy)
        self.assertLessEqual(long_fit[8], 1170)

    def test_varied_headlines_and_full_summary_render(self):
        # Use the official horizontal PNG to detect layout regressions.
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

    def test_disclaimer_clears_bottom_rule_and_date(self):
        canvas = ImageDraw.Draw(Image.new("RGB", (1080, 1350), "white"))
        face = ig.font(16, bold=True)
        bounds = canvas.textbbox(
            (67, ig.FOOTER_DISCLAIMER_Y),
            "MARKETREVAMP  •  NEWS, NOT INVESTMENT ADVICE",
            font=face,
        )
        self.assertGreater(bounds[1], 1270)
        self.assertLessEqual(bounds[3], 1309)
        self.assertGreaterEqual(1321 - bounds[3], 12)

    def test_tokenization_uses_asset_certificate_not_bitcoin_symbol(self):
        from newspaper_design import illustration_topic, draw_editorial_illustration
        title = "Citrini sees a tokenization boom in real-world assets"
        self.assertEqual(illustration_topic(title, "Crypto"), "tokenization")
        self.assertEqual(illustration_topic("Bitcoin ETF inflows rise", "Crypto"),
                         "ledger")
        base = Image.new("RGB", (1080, 1350), (249, 248, 245))
        token_image = base.copy()
        bitcoin_image = base.copy()
        self.assertTrue(draw_editorial_illustration(
            token_image, 850, category="Crypto", headline=title))
        self.assertTrue(draw_editorial_illustration(
            bitcoin_image, 850, category="Crypto",
            headline="Bitcoin ETF inflows rise"))
        self.assertNotEqual(
            token_image.crop((280, 910, 800, 1174)).tobytes(),
            bitcoin_image.crop((280, 910, 800, 1174)).tobytes())
        self.assertEqual(token_image.crop((0, 1174, 1080, 1350)).tobytes(),
                         base.crop((0, 1174, 1080, 1350)).tobytes())

    def test_decorative_engraving_only_uses_available_space(self):
        from newspaper_design import draw_editorial_illustration
        image = Image.new("RGB", (1080, 1350), (249, 248, 245))
        before = image.copy()
        self.assertTrue(draw_editorial_illustration(image, 848, 6, "AI"))
        # Header, summary and source/footer are untouched by the illustration.
        for point in ((100, 500), (100, 800), (200, 1201), (800, 1270)):
            self.assertEqual(image.getpixel(point), before.getpixel(point))
        self.assertNotEqual(image.getpixel((67, 875)), before.getpixel((67, 875)))
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

    def test_headline_drives_illustration_topic(self):
        from newspaper_design import illustration_topic
        cases = [
            ("Jev is Vercel's fastest-adopted AI model ever", "AI", "chip"),
            ("Lawmakers propose new AI regulation", "AI", "policy"),
            ("OpenAI models hacked a crypto wallet", "AI", "security"),
            ("Ray-Ban Meta smart glasses record unexpectedly", "Technology", "glasses"),
            ("Bitcoin ETF inflows rise", "Crypto", "ledger"),
            ("Global stock markets open higher", "Markets", "market"),
            ("AI breakthrough announced", "AI", "network"),
        ]
        for headline, category, expected in cases:
            with self.subTest(headline=headline):
                self.assertEqual(illustration_topic(headline, category), expected)

    def test_same_category_headlines_produce_distinct_centered_art(self):
        from newspaper_design import draw_editorial_illustration
        art = []
        for headline in ("New AI model released", "AI regulators announce policy"):
            image = Image.new("RGB", (1080, 1350), (249, 248, 245))
            self.assertTrue(draw_editorial_illustration(
                image, 850, category="AI", headline=headline))
            art.append(image.crop((300, 900, 780, 1174)).tobytes())
            # Illustration is centered, not confined to the right edge.
            self.assertNotEqual(image.crop((380, 930, 700, 1160)).tobytes(),
                                Image.new("RGB", (320, 230), (249, 248, 245)).tobytes())
        self.assertNotEqual(art[0], art[1])

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
