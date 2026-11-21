"""Review-only tests for the R70 spoken Reel hook and follow outro."""
import tempfile
import unittest
from pathlib import Path

from PIL import Image

from reel_bookends import (
    FOLLOW_LINE, HOOK_LINE, MAX_DURATION_SECONDS,
    build_bookends, joined_narration, narration_segments,
    validate_bookend_timing,
)
from reel_artwork import write_artwork_concat
from reel_r51_design import CAPTION_DARK, SUBTITLE_BOX


class SpokenBookendTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.folder = Path(temporary.name)
        self.stories = [
            {"headline": f"Sample headline {i}", "narration_text": f"Source backed story {i}."}
            for i in range(1, 8)
        ]

    def test_exactly_seven_stories_plus_spoken_bookends(self):
        segments = narration_segments(self.stories)
        self.assertEqual(len(segments), 9)
        self.assertEqual([s["role"] for s in segments],
                         ["intro"] + ["story"] * 7 + ["outro"])
        self.assertEqual(segments[0]["narration_text"], HOOK_LINE)
        self.assertEqual(segments[-1]["narration_text"], FOLLOW_LINE)
        self.assertTrue(HOOK_LINE.startswith("You're watching MarketRevamp."))
        self.assertIn("Follow MarketRevamp", FOLLOW_LINE)
        self.assertEqual([s["narration_text"] for s in segments[1:-1]],
                         [s["narration_text"] for s in self.stories])
        self.assertEqual(joined_narration(segments).count("Source backed story"), 7)

    def test_invalid_content_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "seven stories"):
            narration_segments(self.stories[:6])
        corrupt = [dict(story) for story in self.stories]
        corrupt[4]["narration_text"] = ""
        with self.assertRaisesRegex(ValueError, "sourced narration"):
            narration_segments(corrupt)
        with self.assertRaisesRegex(ValueError, "seven stories"):
            joined_narration([{"narration_text": "incomplete"}])

    def test_intro_outro_frames_preserve_logo_caption_and_disclaimer_safe_zone(self):
        logo = Image.new("RGB", (400, 70), (172, 32, 44))
        paths = build_bookends(logo, self.folder, "R50")
        self.assertEqual(len(paths), 2)
        for path in paths:
            with Image.open(path) as image:
                self.assertEqual(image.size, (1080, 1920))
                self.assertEqual(image.getpixel((73, 85)), (172, 32, 44))
                self.assertEqual(image.getpixel((75, 1365)), CAPTION_DARK)
                self.assertEqual(image.getpixel((75, 1692)), (248, 247, 244))
                self.assertLess(SUBTITLE_BOX[3], 1605)
        for role in ("intro", "outro"):
            with Image.open(self.folder / f"R50_artwork_{role}.png") as transparent:
                self.assertEqual(transparent.mode, "RGBA")
                self.assertIsNone(transparent.getbbox())

    def test_nine_video_segments_and_artwork_track_align(self):
        cuts = [0, 4, 14, 24, 34, 44, 54, 64, 74, 78]
        qa = validate_bookend_timing(cuts)
        self.assertEqual(qa["presentation_segments"], 9)
        self.assertEqual(qa["story_count"], 7)
        self.assertEqual(qa["intro_seconds"], 4)
        self.assertEqual(qa["outro_seconds"], 4)
        build_bookends(Image.new("RGB", (400, 70), "white"), self.folder, "R50")
        for i in range(1, 8):
            Image.new("RGBA", (860, 370)).save(
                self.folder / f"R50_artwork_{i:02d}.png"
            )
        ffconcat = write_artwork_concat(self.folder, "R50", cuts,
                                        include_bookends=True)
        contents = ffconcat.read_text()
        self.assertEqual(contents.count("duration "), 9)
        self.assertEqual(contents.count("file '"), 10)
        self.assertIn("R50_artwork_intro.png", contents)
        self.assertIn("R50_artwork_outro.png", contents)

    def test_timing_and_length_limits(self):
        for invalid in (
            [0, 1, 11, 21, 31, 41, 51, 61, 71, 75],
            [0, 4, 14, 24, 34, 44, 54, 64, 74, 95],
            [0, 4, 14, 24, 34, 44, 54, 64, 74],
        ):
            with self.assertRaises(ValueError):
                validate_bookend_timing(invalid)
        self.assertEqual(MAX_DURATION_SECONDS, 90.0)


if __name__ == "__main__":
    unittest.main()
