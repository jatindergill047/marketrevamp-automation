import json
import tempfile
import unittest
from pathlib import Path
from reel_r30_audit import audit

class R30Tests(unittest.TestCase):
    def test_repeated_subjects_flagged_and_none_approved(self):
        stories = []
        for i in range(7):
            title = "Bitcoin falls again" if i < 2 else f"New software market update {i}"
            stories.append({"title": title, "summary": "Bitcoin market investors react to changes",
                "source_url": f"https://example.com/{i}", "category": "Crypto" if i < 2 else "Markets",
                "editorial_approved": False})
        with tempfile.TemporaryDirectory() as tmp:
            source, target = Path(tmp)/"in.json", Path(tmp)/"out.json"
            source.write_text(json.dumps({"selected_stories": stories}))
            result = audit(source, target)
            self.assertTrue(any("repeated_headline_subject:bitcoin" in x
                for x in result["stories"][1]["flags"]))
            self.assertTrue(all(s["editorial_approved"] is False for s in result["stories"]))
            self.assertEqual(json.loads(target.read_text())["publication"], "disabled")

    def test_rejects_missing_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp)/"in.json"
            source.write_text(json.dumps({"selected_stories": [
                {"title": "Test", "summary": "Test", "source_url": ""} for _ in range(7)]}))
            with self.assertRaises(ValueError):
                audit(source, Path(tmp)/"out.json")

if __name__ == "__main__":
    unittest.main()
