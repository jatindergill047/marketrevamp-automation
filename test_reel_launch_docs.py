"""R12 static launch-safety and documentation checks."""
import unittest
from pathlib import Path

class ReelLaunchDocsTests(unittest.TestCase):
    def test_runbook_contains_launch_blockers_and_rollback(self):
        doc = Path("REELS_RUNBOOK.md").read_text(encoding="utf-8")
        for phrase in ("REEL_ENABLED", "REEL_UPLOAD_ENABLED", "INSTAGRAM_PUBLISH_ENABLED",
                       "rollback", "Cloudinary staging", "Real TTS", "not", "test_reel_recovery.py"):
            self.assertIn(phrase.lower(), doc.lower())

    def test_workflow_cannot_publish(self):
        workflow = Path(".github/workflows/reel-opt-in-validation.yml").read_text(encoding="utf-8")
        self.assertIn("INSTAGRAM_PUBLISH_ENABLED: 'false'", workflow)
        self.assertIn("REEL_UPLOAD_ENABLED: 'false'", workflow)
        self.assertIn("REEL_ENABLED: 'false'", workflow)
        self.assertNotIn("python publish_instagram.py", workflow)
        self.assertNotIn("schedule:", workflow)

    def test_readme_links_runbook(self):
        self.assertIn("REELS_RUNBOOK.md", Path("README.md").read_text(encoding="utf-8"))

if __name__ == "__main__":
    unittest.main()
