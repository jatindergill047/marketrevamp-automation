"""R68 offline checks for seven-slide-matched 2D Reel illustrations."""
import tempfile
import unittest
from pathlib import Path

from PIL import Image

from newspaper_design import illustration_topic
from reel_artwork import (
    ANIMATION_PX, ARTWORK_SIZE, ARTWORK_ZONE, CAPTION_CENTER_Y,
    SUBTITLE_ZONE, composite_artwork_preview, overlay_filter,
    render_artwork, story_theme, write_artwork_concat,
)


class ArtworkTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)

    def test_uses_identical_carousel_motif_selection(self):
        pairs = (
            ("AI", "New AI model launches"),
            ("Technology", "Smartphone security alert"),
            ("Crypto", "Bitcoin market follows Ethereum changes"),
            ("Markets", "New stock market report"),
            ("Technology", "Satellite connects a remote site"),
        )
        for category, headline in pairs:
            story = {"category": category, "headline": headline}
            self.assertEqual(story_theme(story),
                             illustration_topic(headline, category))
        self.assertEqual(story_theme({"category": "Technology",
                                      "headline": "Smartphone security alert"}), "security")
        self.assertEqual(story_theme({"category": "Technology",
                                      "headline": "Cybersecurity testing"}), "security")

    def test_rendered_artwork_is_original_transparent_image(self):
        themes = [
            ("AI", "AI model releases new benchmark"),
            ("Technology", "Smartphone production expands"),
            ("Technology", "Cybersecurity vulnerability identified"),
            ("Technology", "Smart glasses product unveiled"),
            ("Crypto", "Blockchain tokenization project"),
            ("Markets", "Stock market analysts review new report"),
            ("AI", "AI safety rules proposed"),
        ]
        assets = []
        for index, (category, headline) in enumerate(themes, 1):
            location = self.root / f"R50_artwork_{index:02d}.png"
            result = render_artwork(
                {"category": category, "headline": headline}, location
            )
            self.assertEqual(result["path"], str(location))
            with Image.open(location) as image:
                self.assertEqual(image.size, ARTWORK_SIZE)
                self.assertEqual(image.mode, "RGBA")
                self.assertEqual(image.getpixel((0, 0))[3], 0)
                self.assertIsNotNone(image.getbbox())
            assets.append(location)
        self.assertEqual(len(set(location.read_bytes() for location in assets)), 7)

    def test_artwork_subtitles_and_source_never_overlap(self):
        self.assertEqual(CAPTION_CENTER_Y, 1365)
        self.assertLess(ARTWORK_ZONE[3], SUBTITLE_ZONE[1])
        self.assertLess(SUBTITLE_ZONE[3], 1605)
        self.assertEqual(ANIMATION_PX, 8)
        self.assertIn("overlay=", overlay_filter(self.root / "words.ass"))
        self.assertIn("sin(", overlay_filter(self.root / "words.ass"))
        self.assertIn("eval=frame", overlay_filter(self.root / "words.ass"))

    def test_artwork_track_is_aligned_for_seven_scenes(self):
        for i in range(1, 8):
            render_artwork({"category": "AI", "headline": f"AI model {i}"},
                           self.root / f"R50_artwork_{i:02d}.png")
        concat = write_artwork_concat(self.root, "R50",
                                      [0, 8, 16, 24, 32, 40, 48, 56])
        text = concat.read_text()
        self.assertEqual(text.count("duration "), 7)
        self.assertEqual(text.count("file '"), 8)
        with self.assertRaisesRegex(ValueError, "Seven positive"):
            write_artwork_concat(self.root, "R50", [0, 1])

    def test_composite_preview_preserves_source_and_logo_region(self):
        bg = self.root / "background.png"
        img = Image.new("RGB", (1080, 1920), (248, 247, 244))
        img.putpixel((70, 80), (172, 32, 44))
        img.putpixel((75, 1692), (1, 20, 55))
        img.save(bg)
        art = self.root / "artwork.png"
        render_artwork({"category": "AI", "headline": "New AI model"}, art)
        preview = composite_artwork_preview(bg, art)
        self.assertEqual(preview.getpixel((70, 80)), (172, 32, 44))
        self.assertEqual(preview.getpixel((75, 1692)), (1, 20, 55))
        self.assertNotEqual(preview.getpixel((540, 980)), (248, 247, 244))


if __name__ == "__main__":
    unittest.main()
