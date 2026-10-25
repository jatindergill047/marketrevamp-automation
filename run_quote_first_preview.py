"""Synthetic, offline-only live-format quote-first preview for CI inspection.

This script has NO calls to feeds, Cloudinary, Metricool or Instagram.
"""
import os
from pathlib import Path
from unittest.mock import patch
from PIL import Image
import image_generator as ig
from quote_first import promote_quote_to_first
from test_quote_cards import synthetic_stories

OUTPUT = Path("quote_first_preview")
if __name__ == "__main__":
    stories = promote_quote_to_first(synthetic_stories())
    OUTPUT.mkdir(exist_ok=True)
    with patch.dict(os.environ, {"MARKETREVAMP_QUOTE_FIRST": "true"}):
        for index, story in enumerate(stories, 1):
            img = ig.draw_card(story, index, 7, "Oct 25, 2026")
            img.save(OUTPUT / f"slide_{index:02d}.png", "PNG", optimize=True)
    if len(list(OUTPUT.glob("slide_*.png"))) != 7:
        raise SystemExit("Expected exactly 7 synthetic sample images")
    before = ig.draw_card(synthetic_stories()[3], 1, 7, "Oct 25, 2026")
    with Image.open(OUTPUT / "slide_01.png") as after:
        comparison = Image.new("RGB", (2160, 1350), (249, 248, 245))
        comparison.paste(before, (0, 0))
        comparison.paste(after, (1080, 0))
        comparison.save(OUTPUT / "before_after.png", optimize=True)
    print("PASS: synthetic quote is on slide 1, six unchanged standard slides.")
    print("NO REAL NEWS OR MEDIA WAS PUBLISHED.")
