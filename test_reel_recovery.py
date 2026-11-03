"""Verify optional Reel failures never alter the existing carousel."""
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from prepare_reel import prepare
from tts import ReelBuildError

class RecoveryTests(unittest.TestCase):
    def check_failure(self, stage, upload=False):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "news_results.json").write_text(json.dumps({"selected_stories": [
                {"title": str(i), "summary": "News summary"} for i in range(7)]}))
            (root / "instagram_images").mkdir()
            carousel = root / "carousel.json"
            carousel.write_text("unchanged")
            previous = Path.cwd()
            try:
                os.chdir(root)
                def frame(source, index, dest):
                    Path(dest).write_bytes(b"frame")
                    return Path(dest)
                def audio(text, dest):
                    Path(dest).write_bytes(b"audio")
                    return Path(dest)
                def render(frames, audios, texts, dest, segments):
                    Path(dest).write_bytes(b"video")
                    return Path(dest)
                def fail(*args):
                    raise ReelBuildError("injected failure")
                with patch.dict(os.environ, {"REEL_ENABLED": "true",
                        "REEL_UPLOAD_ENABLED": str(upload).lower(),
                        "CLOUDINARY_CLOUD_NAME": "demo",
                        "CLOUDINARY_UPLOAD_PRESET": "test"}), \
                     patch("reel_script.build_all", return_value=["Narration"] * 7), \
                     patch("reel_frames.compose", side_effect=fail if stage == "frame" else frame), \
                     patch("tts.speak", side_effect=fail if stage == "tts" else audio), \
                     patch("build_reel.build_reel", side_effect=fail if stage == "render" else render), \
                     patch("reel_cloudinary.upload_video", side_effect=fail if stage == "upload" else None):
                    with self.assertRaisesRegex(ReelBuildError, "injected failure"):
                        prepare()
                self.assertEqual(carousel.read_text(), "unchanged")
                self.assertFalse((root / "cloudinary_reel_upload.json").exists())
            finally:
                os.chdir(previous)

    def test_frame_failure(self):
        self.check_failure("frame")

    def test_tts_failure(self):
        self.check_failure("tts")

    def test_render_failure(self):
        self.check_failure("render")

    def test_upload_failure(self):
        self.check_failure("upload", True)

if __name__ == "__main__":
    unittest.main()
