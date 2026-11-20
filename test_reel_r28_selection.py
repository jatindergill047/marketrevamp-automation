"""R28 independent selection safety tests."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from reel_r28_selection import select_reel_stories

class R28SelectionTests(unittest.TestCase):
    def test_missing_history_blocks_selection(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            source = root / "news.json"
            source.write_text(json.dumps({"articles": []}))
            with self.assertRaises(RuntimeError):
                select_reel_stories(source, root / "missing_history.json", root / "out.json")

    def test_filters_published_urls_and_does_not_modify_input(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            source = root / "news.json"
            history = root / "history.json"
            original = json.dumps({"articles": [
                {"title": "Old story", "url": "https://example.com/old", "score": 10},
                {"title": "Fresh story", "url": "https://example.com/new", "score": 10},
                {"title": "Low score", "url": "https://example.com/low", "score": 0}
            ]})
            source.write_text(original)
            history.write_text(json.dumps({"entry": {"status": "published",
                "article_urls": ["https://example.com/old"]}}))
            with patch("reel_r28_selection.select_usable") as select:
                select.return_value = [{"title": str(i)} for i in range(7)]
                out = select_reel_stories(source, history, root / "reel.json")
                candidates = select.call_args.args[0]
                self.assertEqual([s["title"] for s in candidates], ["Fresh story"])
                self.assertEqual(len(json.loads(out.read_text())["selected_stories"]), 7)
            self.assertEqual(source.read_text(), original)

    def test_incomplete_selection_refused(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            source = root / "news.json"
            history = root / "history.json"
            source.write_text(json.dumps({"articles": []}))
            history.write_text("{}")
            with patch("reel_r28_selection.select_usable", return_value=[]):
                with self.assertRaisesRegex(RuntimeError, "seven"):
                    select_reel_stories(source, history, root / "reel.json")

if __name__ == "__main__":
    unittest.main()
