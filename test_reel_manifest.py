"""Tests for optional Reel manifest metadata and carousel fallback."""
import json
import tempfile
import unittest
from pathlib import Path

from reel_manifest import load_reel_metadata


class ReelManifestTests(unittest.TestCase):
    def test_absent_upload_returns_none(self):
        with tempfile.TemporaryDirectory() as folder:
            self.assertIsNone(load_reel_metadata(Path(folder) / "missing.json"))

    def test_valid_reel(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            upload = root / "upload.json"
            segments = root / "segments.json"
            upload.write_text(json.dumps({
                "secure_url": "https://res.cloudinary.com/demo/video/upload/v1/reel.mp4",
                "resource_type": "video",
            }))
            segments.write_text(json.dumps({
                "duration_seconds": 42.5,
                "segments": [{"index": i} for i in range(1, 8)],
            }))
            self.assertEqual(load_reel_metadata(upload, segments)["duration_seconds"], 42.5)

    def test_rejects_wrong_host(self):
        with tempfile.TemporaryDirectory() as folder:
            upload = Path(folder) / "upload.json"
            upload.write_text(json.dumps({
                "secure_url": "https://example.com/video/upload/reel.mp4",
                "resource_type": "video",
            }))
            with self.assertRaises(ValueError):
                load_reel_metadata(upload, Path(folder) / "segments.json")

    def test_rejects_incomplete_segments(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            upload = root / "upload.json"
            segments = root / "segments.json"
            upload.write_text(json.dumps({
                "secure_url": "https://res.cloudinary.com/demo/video/upload/reel.mp4",
                "resource_type": "video",
            }))
            segments.write_text(json.dumps({"duration_seconds": 3, "segments": []}))
            with self.assertRaises(ValueError):
                load_reel_metadata(upload, segments)


if __name__ == "__main__":
    unittest.main()
