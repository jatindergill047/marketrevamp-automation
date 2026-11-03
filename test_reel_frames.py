"""Tests for the vertical Reel slide compositor."""

import tempfile
import unittest
from pathlib import Path

from PIL import Image, ImageDraw, ImageStat

from reel_frames import compose


class ReelFrameTests(unittest.TestCase):
    """Verify geometry, legibility, and input preservation."""

    def test_dimensions_and_foreground_variance(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "source.png"
            output = Path(folder) / "frame.png"
            image = Image.new("RGB", (1080, 1350), "#f5f5f5")
            draw = ImageDraw.Draw(image)
            for x in range(0, 1080, 24):
                draw.rectangle((x, 0, x + 11, 1350), fill=(x % 255, 20, 180))
            image.save(source)
            original_bytes = source.read_bytes()
            compose(source, 3, output)
            with Image.open(output) as result:
                self.assertEqual(result.size, (1080, 1920))
                foreground = result.crop((80, 280, 1000, 1100))
                background = result.crop((80, 1800, 1000, 1850))
                self.assertGreater(sum(ImageStat.Stat(foreground).var), sum(ImageStat.Stat(background).var))
            self.assertEqual(source.read_bytes(), original_bytes)

    def test_invalid_index(self):
        with self.assertRaises(ValueError):
            compose("missing.png", 8, "out.png")

    def test_overlong_slide_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "tall.png"
            Image.new("RGB", (100, 200), "white").save(source)
            with self.assertRaises(ValueError):
                compose(source, 1, Path(folder) / "out.png")


if __name__ == "__main__":
    unittest.main()
