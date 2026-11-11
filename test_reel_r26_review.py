"""R26 review safety checks; no external services required."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from reel_r26_review import prepare_r26
from test_reel_r25_editorial import sample

class R26ReviewTests(unittest.TestCase):
    def test_blocks_upload_flags_before_reading_input(self):
        with patch.dict("os.environ", {"REEL_UPLOAD_ENABLED": "true"}):
            with self.assertRaisesRegex(RuntimeError, "review-only"):
                prepare_r26("missing.json")

    def test_requires_explicit_editorial_approval(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            stories = sample()
            stories[0]["editorial_approved"] = False
            source = root / "news.json"
            source.write_text(json.dumps({"selected_stories": stories}))
            with patch("reel_r26_review.render_reviewed_preview") as render:
                with self.assertRaisesRegex(ValueError, "approval"):
                    prepare_r26(source, root / "slides", root / "review")
                render.assert_not_called()

    def test_requires_real_slides(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source = root / "news.json"
            source.write_text(json.dumps({"selected_stories": sample()}))
            with self.assertRaisesRegex(FileNotFoundError, "slides"):
                prepare_r26(source, root / "missing", root / "review")

if __name__ == "__main__":
    unittest.main()
