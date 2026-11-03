"""Offline R9 Reel dispatch checks."""
import unittest

from reel_publish import reel_payload


class ReelPublishTests(unittest.TestCase):
    def test_payload(self):
        url = "https://res.cloudinary.com/demo/image/upload/slide.jpg"
        manifest = {
            "media_kind": "reel", "caption": "Sources: example.com",
            "slides": [{"image_url": url}],
            "reel": {
                "video_url": "https://res.cloudinary.com/demo/video/upload/reel.mp4",
                "cover_url": url,
                "duration_seconds": 40,
                "caption": "Sources: example.com",
            },
        }
        self.assertEqual(reel_payload(manifest)["media_type"], "REELS")
        self.assertEqual(reel_payload(manifest)["video_url"], manifest["reel"]["video_url"])
        manifest["reel"]["video_url"] = "https://example.com/reel.mp4"
        with self.assertRaises(ValueError):
            reel_payload(manifest)


if __name__ == "__main__":
    unittest.main()
