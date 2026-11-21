"""No-network regression tests for R51 larger captions and retained Key Detail."""
import tempfile
import unittest
from pathlib import Path

from PIL import Image
from reel_r51_design import (
    CAPTION_DARK, CAPTION_FONT_SIZE, KEY_BOX, RED,
    SUBTITLE_BOX, enlarge_subtitles, style_scene,
)

ASS="""[Script Info]
ScriptType: v4.00+
[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Words,DejaVu Sans,53,&H001D23BF,&H00FFFFFF,&H990A1020,&H70050D20,1,0,0,0,100,100,0,0,1,2,0,2,60,60,440,1
[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 0,0:00:01.00,0:00:02.00,Words,,0,0,0,,{\\kf40}MarketRevamp {\\kf60}reporting
"""

class R51DesignTests(unittest.TestCase):
    def setUp(self):
        folder=tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.root=Path(folder.name)

    def test_retains_key_detail_and_caption_safe_region(self):
        src=self.root/"original.png"
        dest=self.root/"styled.png"
        original=Image.new("RGB",(1080,1920),(248,247,244))
        original.putpixel((100,100),(12,55,155))
        original.save(src)
        result=style_scene(src,"A limited pilot adds parent booking and more driver safeguards.",dest)
        self.assertEqual(result["detail_lines"],2)
        with Image.open(dest) as out:
            self.assertEqual(out.size,(1080,1920))
            self.assertEqual(out.getpixel((100,100)),(12,55,155))
            self.assertEqual(out.getpixel((75,1110)),RED)
            self.assertEqual(out.getpixel((75,1400)),CAPTION_DARK)
            self.assertEqual(out.getpixel((75,1650)),(248,247,244))
        self.assertLess(KEY_BOX[3],SUBTITLE_BOX[1])
        self.assertLess(SUBTITLE_BOX[3],1605)

    def test_caption_increase_preserves_exact_karaoke_text_and_times(self):
        source=self.root/"source.ass"
        target=self.root/"result.ass"
        source.write_text(ASS,encoding="utf-8")
        result=enlarge_subtitles(source,target)
        self.assertEqual(result["caption_font_size"],72)
        self.assertEqual(result["karaoke_events_unchanged"],1)
        output=target.read_text(encoding="utf-8")
        self.assertIn("Dialogue: 0,0:00:01.00,0:00:02.00",output)
        original_events=[x for x in ASS.splitlines() if x.startswith("Dialogue:")]
        revised_events=[x for x in output.splitlines() if x.startswith("Dialogue:")]
        self.assertEqual(original_events,revised_events)
        style=next(x for x in output.splitlines() if x.startswith("Style: Words,")).split(":",1)[1].strip().split(",")
        self.assertEqual(style[2],str(CAPTION_FONT_SIZE))
        self.assertEqual(style[18],"2")
        self.assertEqual(style[19:22],["110","110","390"])

    def test_rejects_unreadable_key_detail(self):
        image=self.root/"frame.png"
        Image.new("RGB",(1080,1920),(248,247,244)).save(image)
        with self.assertRaisesRegex(ValueError,"overflow"):
            style_scene(image,"This is a long complex detail "*65,self.root/"bad.png")

    def test_rejects_wrong_video_frame_size(self):
        image=self.root/"frame.png"
        Image.new("RGB",(540,960),(248,247,244)).save(image)
        with self.assertRaisesRegex(ValueError,"1080x1920"):
            style_scene(image,"A key detail",self.root/"bad.png")

if __name__=="__main__":
    unittest.main()
