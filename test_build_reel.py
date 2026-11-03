"""Isolated tests for Reel assembly without network or live publishing."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import build_reel
from tts import ReelBuildError


class BuildReelTests(unittest.TestCase):
    def test_captions_two_lines_and_escape(self):
        with tempfile.TemporaryDirectory() as folder:
            target = build_reel.write_captions("Headline {test} " + "word " * 25, 6, Path(folder) / "sub.ass")
            text = target.read_text()
            self.assertIn("Fontsize", text)
            self.assertIn("54,", text)
            self.assertIn(r"\{test\}", text)
            dialogues = [line for line in text.splitlines() if line.startswith("Dialogue:")]
            self.assertGreaterEqual(len(dialogues), 2)
            self.assertTrue(all(line.count(r"\N") <= 1 for line in dialogues))

    def test_rejects_mismatched_inputs(self):
        with self.assertRaises(ReelBuildError):
            build_reel.build_reel(["frame.png"], [], ["narration"], "out.mp4")

    def test_metadata_and_ffmpeg_arguments(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            frame = root / "frame.png"
            audio = root / "audio.mp3"
            frame.write_bytes(b"frame")
            audio.write_bytes(b"audio")
            output = root / "reel.mp4"
            commands = []

            def fake_run(args):
                commands.append(args)
                Path(args[-1]).write_bytes(b"video")

            with patch("build_reel.shutil.which", return_value="/usr/bin/ffmpeg"), patch("build_reel.duration", return_value=2.1), patch("build_reel._run", side_effect=fake_run):
                self.assertEqual(build_reel.build_reel([frame], [audio], ["One of one."], output), output)
            self.assertEqual(len(commands), 2)
            self.assertIn("zoompan", " ".join(commands[0]))
            self.assertIn("ass=", " ".join(commands[0]))
            self.assertIn("libx264", commands[0])
            self.assertIn("aac", commands[0])
            data = json.loads((root / "reel_segments.json").read_text())
            self.assertEqual(data["segments"][0]["duration_seconds"], 3.0)

    def test_missing_ffmpeg(self):
        with patch("build_reel.shutil.which", return_value=None):
            with self.assertRaises(ReelBuildError):
                build_reel.build_reel(["frame"], ["audio"], ["text"], "out.mp4")


if __name__ == "__main__":
    unittest.main()
