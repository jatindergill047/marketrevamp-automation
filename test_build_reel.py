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

    def test_captions_stop_before_quiet_story_pause(self):
        with tempfile.TemporaryDirectory() as folder:
            path = build_reel.write_captions(
                "A development worth watching.", 6, Path(folder) / "pause.ass",
                spoken_seconds=4,
            )
            dialogues = [line for line in path.read_text().splitlines()
                         if line.startswith("Dialogue:")]
            self.assertTrue(dialogues)
            self.assertIn("0:00:04.00", dialogues[-1])
            self.assertNotIn("0:00:06.00", dialogues[-1])

    def test_phrase_boundary_and_word_weighted_caption_timing(self):
        with tempfile.TemporaryDirectory() as folder:
            path = build_reel.write_captions(
                "First short sentence. Then five more words follow now.",
                10, Path(folder) / "phrases.ass", spoken_seconds=8,
            )
            dialogues = [line for line in path.read_text().splitlines()
                         if line.startswith("Dialogue:")]
            self.assertEqual(len(dialogues), 2)
            self.assertIn("First short sentence.", dialogues[0])
            self.assertIn("0:00:02.67", dialogues[0])
            self.assertIn("0:00:08.00", dialogues[-1])

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
            self.assertEqual(data["segments"][0]["duration_seconds"], 3.1)

    def test_r24_rejects_mismatched_word_boundaries(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            frame, audio = root / "frame.png", root / "audio.mp3"
            frame.write_bytes(b"frame")
            audio.write_bytes(b"audio")
            timings = root / "boundaries.json"
            timings.write_text(json.dumps([{"text": "Different", "start_seconds": 0.0}]))
            with patch("build_reel.shutil.which", return_value="/usr/bin/ffmpeg"), patch("build_reel.duration", return_value=2.0):
                with self.assertRaisesRegex(ReelBuildError, "do not match"):
                    build_reel.build_continuous_reel([frame], audio, ["Reviewed words."],
                        root / "output.mp4", boundaries_path=timings)

    def test_r25_word_timed_captions(self):
        with tempfile.TemporaryDirectory() as folder:
            words = [
                {"start_seconds": 0.3, "duration_seconds": 0.2},
                {"start_seconds": 1.1, "duration_seconds": 0.4},
                {"start_seconds": 2.0, "duration_seconds": 0.3},
            ]
            path = build_reel.write_captions(
                "One two three.", 4, Path(folder) / "timed.ass", word_timings=words)
            lines = [line for line in path.read_text().splitlines()
                     if line.startswith("Dialogue:")]
            self.assertEqual(len(lines), 1)
            self.assertIn("0:00:00.30", lines[0])
            self.assertIn("0:00:02.30", lines[0])

    def test_r25_hyphenated_caption_word_alignment(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            frame, audio = root / "frame.png", root / "voice.mp3"
            frame.write_bytes(b"frame")
            audio.write_bytes(b"audio")
            timings = root / "boundaries.json"
            timings.write_text(json.dumps([
                {"text": "Cross", "start_seconds": 0.1, "duration_seconds": 0.2},
                {"text": "border", "start_seconds": 0.3, "duration_seconds": 0.2},
                {"text": "payments", "start_seconds": 0.6, "duration_seconds": 0.3},
            ]))
            commands = []
            def fake_run(args):
                commands.append(args)
                Path(args[-1]).write_bytes(b"video")
            with patch("build_reel.shutil.which", return_value="/usr/bin/ffmpeg"), \
                 patch("build_reel.duration", return_value=2.0), \
                 patch("build_reel._run", side_effect=fake_run):
                build_reel.build_continuous_reel(
                    [frame], audio, ["Cross-border payments."], root / "video.mp4",
                    fps=5, boundaries_path=timings)
            self.assertEqual(len(commands), 3)

    def test_missing_ffmpeg(self):
        with patch("build_reel.shutil.which", return_value=None):
            with self.assertRaises(ReelBuildError):
                build_reel.build_reel(["frame"], ["audio"], ["text"], "out.mp4")


if __name__ == "__main__":
    unittest.main()
