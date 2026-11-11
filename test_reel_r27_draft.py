"""R27 source-linked draft is fail-closed and never auto-approved."""
import json
import tempfile
import unittest
from pathlib import Path
from reel_r27_draft import prepare_draft

class R27DraftTests(unittest.TestCase):
    def test_seven_sources_are_drafts_not_approved(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            news = root / "news.json"
            news.write_text(json.dumps({"selected_stories": [
                {"title": f"Story {i}", "summary": "Publisher extract.",
                 "url": f"https://example.com/{i}"} for i in range(7)]}))
            result = prepare_draft(news, root / "review" / "draft.json")
            records = json.loads(result.read_text())["selected_stories"]
            self.assertEqual(len(records), 7)
            self.assertTrue(all(s["editorial_approved"] is False for s in records))
            self.assertTrue(all(s["narration_text"] == "" for s in records))
            self.assertTrue((result.parent / "EDITORIAL_CHECKLIST.md").exists())

    def test_five_story_carousel_does_not_silently_fill_seven(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            news = root / "news.json"
            news.write_text(json.dumps({"selected_stories": [
                {"title": "Example", "summary": "Example", "url": "https://example.com"}
                for _ in range(5)]}))
            with self.assertRaisesRegex(ValueError, "seven"):
                prepare_draft(news, root / "draft.json")

if __name__ == "__main__":
    unittest.main()
