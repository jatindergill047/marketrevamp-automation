import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from reel_r32_storyboard import prepare

class StoryboardTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.source = Path(self.temp.name) / "input.json"
        self.output = Path(self.temp.name) / "review"
        self.stories = [{"title": f"News {i}", "summary": "Source summary",
                         "narration_text": "Narration text", "editorial_impact": "Impact",
                         "source_url": f"https://example.org/news/{i}",
                         "editorial_approved": False} for i in range(7)]
        self.source.write_text(json.dumps({"selected_stories": self.stories}))

    def test_creates_unapproved_review_only_storyboard(self):
        with patch.dict("os.environ", {key: "false" for key in
                        ("REEL_ENABLED", "REEL_UPLOAD_ENABLED", "INSTAGRAM_PUBLISH_ENABLED")}):
            result = prepare(self.source, self.output)
        self.assertEqual(len(result["stories"]), 7)
        self.assertEqual(result["publication"], "disabled")
        self.assertTrue(all(not item["editorial_approved"] for item in result["stories"]))
        self.assertTrue((self.output / "STORYBOARD.md").is_file())

    def test_fails_closed_with_publishing_enabled(self):
        with patch.dict("os.environ", {"INSTAGRAM_PUBLISH_ENABLED": "true"}):
            with self.assertRaises(RuntimeError):
                prepare(self.source, self.output)

    def test_rejects_incomplete_stories(self):
        self.stories[0]["source_url"] = ""
        self.source.write_text(json.dumps({"selected_stories": self.stories}))
        with self.assertRaises(ValueError):
            prepare(self.source, self.output)

if __name__ == "__main__":
    unittest.main()
