"""Network-free tests for Cloudinary Reel uploads."""
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from reel_cloudinary import upload_video


class UploadTests(unittest.TestCase):
    def test_unsigned_upload(self):
        with tempfile.TemporaryDirectory() as directory:
            video = Path(directory) / "reel.mp4"
            video.write_bytes(b"fake mp4 content")
            response = io.BytesIO(json.dumps({
                "secure_url": "https://res.cloudinary.com/demo/video/upload/v1/reel.mp4",
                "public_id": "reel",
            }).encode())
            with patch("reel_cloudinary.urllib.request.urlopen", return_value=response) as mocked:
                result = upload_video(video, "demo", "preset")
            self.assertEqual(result["resource_type"], "video")
            request = mocked.call_args.args[0]
            self.assertIn("/video/upload", request.full_url)
            self.assertIn(b"video/mp4", request.data)
            self.assertIn(b"fake mp4 content", request.data)

    def test_signed_upload(self):
        with tempfile.TemporaryDirectory() as directory:
            video = Path(directory) / "reel.mp4"
            video.write_bytes(b"mp4")
            response = io.BytesIO(json.dumps({
                "secure_url": "https://res.cloudinary.com/demo/video/upload/reel.mp4"
            }).encode())
            with patch("reel_cloudinary.urllib.request.urlopen", return_value=response) as mocked:
                upload_video(video, "demo", "preset", "key", "secret")
            self.assertIn(b'name="signature"', mocked.call_args.args[0].data)

    def test_reject_missing_file(self):
        with self.assertRaises(ValueError):
            upload_video("missing.mp4", "demo", "preset")

    def test_reject_bad_url(self):
        with tempfile.TemporaryDirectory() as directory:
            video = Path(directory) / "reel.mp4"
            video.write_bytes(b"mp4")
            response = io.BytesIO(b'{"secure_url":"https://example.com/reel.mp4"}')
            with patch("reel_cloudinary.urllib.request.urlopen", return_value=response):
                with self.assertRaises(ValueError):
                    upload_video(video, "demo", "preset")


if __name__ == "__main__":
    unittest.main()
