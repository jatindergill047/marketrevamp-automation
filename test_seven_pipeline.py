"""Safe seven-slide carousel contract tests; no live Instagram publishing."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import publish_instagram as publisher


class SevenSlideContractTests(unittest.TestCase):
    def manifest(self, count):
        return {
            "slides": [
                {"slide": i + 1,
                 "image_url": f"https://res.cloudinary.com/demo/image/upload/story{i + 1}.jpg"}
                for i in range(count)
            ],
            "article_urls": [f"https://example.com/article-{i + 1}" for i in range(count)],
        }

    def test_seven_images_accepted(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "manifest.json"
            path.write_text(json.dumps(self.manifest(7)), encoding="utf-8")
            with patch.object(publisher, "MANIFEST_FILE", path):
                data, urls = publisher.load_manifest()
            self.assertEqual(len(urls), 7)
            self.assertEqual(len(data["article_urls"]), 7)

    def test_five_images_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "manifest.json"
            path.write_text(json.dumps(self.manifest(5)), encoding="utf-8")
            with patch.object(publisher, "MANIFEST_FILE", path):
                with self.assertRaisesRegex(RuntimeError, "seven slides"):
                    publisher.load_manifest()


if __name__ == "__main__":
    unittest.main()
