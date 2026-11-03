"""Network-free tests for opt-in Reel text-to-speech."""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import tts


class TTSTests(unittest.TestCase):
    """Check retries, binary availability, and ffprobe output validation."""

    def test_available_false_without_ffprobe(self):
        with patch("tts.shutil.which", return_value=None):
            self.assertFalse(tts.available())

    def test_duration_parses_ffprobe_json(self):
        with patch("tts.available", return_value=True), patch("tts.subprocess.run") as run:
            run.return_value.stdout = json.dumps({"format": {"duration": "4.25"}})
            self.assertEqual(tts.duration("voice.mp3"), 4.25)

    def test_duration_rejects_invalid_data(self):
        with patch("tts.available", return_value=True), patch("tts.subprocess.run") as run:
            run.return_value.stdout = '{"format": {"duration": "nan"}}'
            with self.assertRaises(tts.ReelBuildError):
                tts.duration("voice.mp3")

    def test_speak_retries_then_raises(self):
        communicator = MagicMock()
        communicator.save = AsyncMock(side_effect=OSError("offline"))
        fake_edge = MagicMock()
        fake_edge.Communicate.return_value = communicator
        with tempfile.TemporaryDirectory() as directory:
            with patch.dict("sys.modules", {"edge_tts": fake_edge}), patch("tts.time.sleep") as sleep:
                with self.assertRaises(tts.ReelBuildError):
                    tts.speak("Hello", Path(directory) / "voice.mp3")
                self.assertEqual(communicator.save.await_count, 3)
                self.assertEqual(sleep.call_count, 2)

    def test_speak_success(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "voice.mp3"
            async def write_audio(path):
                Path(path).write_bytes(b"audio")
            communicator = MagicMock()
            communicator.save = AsyncMock(side_effect=write_audio)
            fake_edge = MagicMock()
            fake_edge.Communicate.return_value = communicator
            with patch.dict("sys.modules", {"edge_tts": fake_edge}):
                self.assertEqual(tts.speak("Hello", output), output)
                self.assertEqual(output.read_bytes(), b"audio")
                fake_edge.Communicate.assert_called_once_with("Hello", tts.VOICE, rate="-5%", pitch="-2Hz")


if __name__ == "__main__":
    unittest.main()
