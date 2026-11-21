"""Regression contract for the user-approved R68 Reel visual template.

This approves presentation only. No publication, editorial or upload gates.
"""
import json
import unittest
from pathlib import Path

from reel_artwork import (
    ARTWORK_SIZE, ARTWORK_ZONE, ANIMATION_PX,
    ANIMATION_SECONDS, CAPTION_CENTER_Y, SUBTITLE_ZONE,
    story_theme, overlay_filter,
)
from reel_r51_design import (
    CAPTION_FONT_SIZE, SUBTITLE_BOX,
)
from newspaper_design import illustration_topic

ROOT = Path(__file__).resolve().parent
SPEC = json.loads((ROOT / "R68_APPROVED_DESIGN.json").read_text(
    encoding="utf-8"
))


class R68VisualDesignContractTests(unittest.TestCase):
    def test_approved_spec_is_visual_only(self):
        self.assertEqual(SPEC["version"], "R68")
        self.assertEqual(SPEC["design_status"], "approved_for_reel_visuals")
        self.assertEqual(SPEC["frame_size"], [1080, 1920])
        self.assertEqual(SPEC["story_count"], 7)
        self.assertEqual(SPEC["scope"],
                         "experimental feature/reels-opt-in visual template only")
        self.assertEqual(SPEC["logo_asset"],
                         "marketrevamp_logo_horizontal.png")
        for key in (
            "approved_reel_content", "editorial_approved",
            "instagram_published", "cloudinary_uploaded",
            "production_reel_publishing_enabled", "changes_to_main_allowed",
            "key_details_section",
        ):
            self.assertIs(SPEC[key], False, key)

    def test_artwork_matches_approved_carousel_style_and_safe_zone(self):
        art = SPEC["artwork"]
        self.assertEqual(art["source_selector"],
                         "newspaper_design.illustration_topic")
        self.assertEqual(tuple(art["pixel_size"]), ARTWORK_SIZE)
        self.assertEqual(tuple(art["zone"]), ARTWORK_ZONE)
        self.assertEqual(art["animation"], "subtle_vertical_float")
        self.assertEqual(art["amplitude_pixels"], ANIMATION_PX)
        self.assertEqual(art["period_seconds"], ANIMATION_SECONDS)
        self.assertLess(ARTWORK_ZONE[3], SUBTITLE_ZONE[1])
        self.assertLess(SUBTITLE_ZONE[3], 1605)
        self.assertEqual(
            story_theme({"headline": "AI model launch", "category": "AI"}),
            illustration_topic("AI model launch", "AI")
        )
        self.assertEqual(
            story_theme({"headline": "Cybersecurity warning", "category": "Technology"}),
            "security"
        )
        self.assertIn("sin(", overlay_filter("example.ass"))
        self.assertIn("eval=frame", overlay_filter("example.ass"))

    def test_subtitle_style_is_preserved_below_artwork(self):
        captions = SPEC["subtitles"]
        self.assertEqual(tuple(captions["box"]), SUBTITLE_BOX)
        self.assertEqual(tuple(captions["box"]), SUBTITLE_ZONE)
        self.assertEqual(captions["center_y"], CAPTION_CENTER_Y)
        self.assertEqual(captions["font_size_px"], CAPTION_FONT_SIZE)
        self.assertEqual(CAPTION_FONT_SIZE, 80)
        self.assertEqual(captions["position"], "below_artwork")
        self.assertTrue(captions["active_word_highlight"])

    def test_actual_renderers_use_approved_components(self):
        for name in ("reel_r50_review.py", "reel_r52_review.py"):
            source = (ROOT / name).read_text(encoding="utf-8")
            for required in (
                "render_artwork(story,",
                "overlay_filter(ass)",
                "write_artwork_concat(target,",
                "enlarge_subtitles(ass_path, ass_path)",
                "make_logo()",
            ):
                self.assertIn(required, source, f"{name}: {required}")
        design = (ROOT / "reel_r51_design.py").read_text(encoding="utf-8")
        self.assertNotIn('draw.text((118,1091),"THE KEY DETAIL"', design)
        review = (ROOT / "reel_clean_end_to_end_review.py").read_text(
            encoding="utf-8"
        )
        self.assertIn('"status": "review_only"', review)
        self.assertIn('"published": False', review)
        self.assertIn('"cloudinary_uploaded": False', review)
        self.assertIn('"instagram_published": False', review)


if __name__ == "__main__":
    unittest.main()
