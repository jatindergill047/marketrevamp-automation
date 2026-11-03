"""R11 isolated end-to-end Reel render and mocked Cloudinary validation."""
import io
import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image
from build_reel import build_reel
from reel_cloudinary import upload_video
from reel_frames import compose
from reel_manifest import load_reel_metadata


class ReelIntegrationTests(unittest.TestCase):
    def test_seven_segment_mp4_and_mock_cloudinary(self):
        self.assertIsNotNone(shutil.which("ffmpeg"), "ffmpeg is required for R11")
        self.assertIsNotNone(shutil.which("ffprobe"), "ffprobe is required for R11")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            frames, audios, narrations = [], [], []
            for i in range(1, 8):
                slide = root / f"slide_{i:02d}.png"
                Image.new("RGB", (1080, 1350), (20 + i * 15, 35, 55)).save(slide)
                frames.append(compose(slide, i, root / f"frame_{i:02d}.png"))
                audio = root / f"audio_{i:02d}.wav"
                subprocess.run(["ffmpeg", "-nostdin", "-y", "-loglevel", "error",
                                "-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono",
                                "-t", "0.25", str(audio)], check=True, timeout=30)
                audios.append(audio)
                narrations.append(f"Story {i} test narration.")
            output = root / "reel.mp4"
            timing = root / "reel_segments.json"
            build_reel(frames, audios, narrations, output, timing, fps=2)
            self.assertGreater(output.stat().st_size, 1000)
            data = json.loads(timing.read_text())
            self.assertEqual(len(data["segments"]), 7)
            probe = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                                    "stream=codec_type,width,height", "-of", "json", str(output)],
                                   capture_output=True, text=True, check=True, timeout=30)
            streams = json.loads(probe.stdout)["streams"]
            self.assertTrue(any(s.get("codec_type") == "video" and
                                (s.get("width"), s.get("height")) == (1080, 1920) for s in streams))
            self.assertTrue(any(s.get("codec_type") == "audio" for s in streams))
            cloudinary = {"secure_url": "https://res.cloudinary.com/demo/video/upload/v1/reel.mp4",
                          "public_id": "reel", "resource_type": "video"}
            with patch("reel_cloudinary.urllib.request.urlopen",
                       return_value=io.BytesIO(json.dumps(cloudinary).encode())) as mocked:
                upload = upload_video(output, "demo", "test-preset")
            self.assertEqual(upload["resource_type"], "video")
            self.assertIn(b"video/mp4", mocked.call_args.args[0].data)
            upload_path = root / "cloudinary_reel_upload.json"
            upload_path.write_text(json.dumps(upload))
            metadata = load_reel_metadata(upload_path, timing)
            self.assertEqual(metadata["video_url"], cloudinary["secure_url"])
            self.assertGreater(metadata["duration_seconds"], 0)


if __name__ == "__main__":
    unittest.main()
