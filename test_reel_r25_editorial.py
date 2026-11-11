"""R25 source-linked review safety tests."""
import json
import tempfile
import unittest
from pathlib import Path
from reel_r25_editorial import validate_stories, build_review_package

def sample():
    return [{"title": f"Headline {i}", "summary": "Reviewed detail.",
             "narration_text": f"Reviewed narration {i}.",
             "editorial_impact": "Reviewed relevance.",
             "source_url": f"https://example.com/article/{i}",
             "editorial_approved": True} for i in range(7)]

class EditorialTests(unittest.TestCase):
    def test_requires_seven(self):
        with self.assertRaises(ValueError):
            validate_stories(sample()[:6])
    def test_requires_source(self):
        stories = sample()
        stories[0]["source_url"] = "http://example.com"
        with self.assertRaisesRegex(ValueError, "source URL"):
            validate_stories(stories)
    def test_requires_approval(self):
        stories = sample()
        stories[0]["editorial_approved"] = False
        with self.assertRaisesRegex(ValueError, "approval"):
            validate_stories(stories)
    def test_requires_reviewed_impact(self):
        stories = sample()
        del stories[0]["editorial_impact"]
        with self.assertRaisesRegex(ValueError, "editorial_impact"):
            validate_stories(stories)
    def test_generates_review_without_publishing(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "news_results.json"
            source.write_text(json.dumps({"selected_stories": sample()}))
            output = build_review_package(source, root / "review")
            manifest = json.loads((output / "editorial_review.json").read_text())
            self.assertEqual(manifest["publication"], "disabled")
            self.assertEqual(len(manifest["stories"]), 7)
            self.assertIn("https://example.com/article/0", (output / "REVIEW.md").read_text())
            self.assertIn("Reviewed narration 6.", (output / "narration.txt").read_text())

if __name__ == "__main__":
    unittest.main()
