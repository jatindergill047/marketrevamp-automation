"""Offline R10 disabled-by-default workflow regression."""
import os
import unittest
from pathlib import Path
from unittest.mock import patch

from prepare_reel import prepare


class ReelWorkflowTests(unittest.TestCase):
    def test_disabled_does_not_read_files_or_upload(self):
        with patch.dict(os.environ, {"REEL_ENABLED": "false", "REEL_UPLOAD_ENABLED": "false"}):
            self.assertFalse(prepare())

    def test_workflow_is_manual_and_does_not_publish(self):
        workflow = Path(".github/workflows/reel-opt-in-validation.yml").read_text(encoding="utf-8")
        self.assertIn("workflow_dispatch:", workflow)
        self.assertNotIn("schedule:", workflow)
        self.assertNotIn("publish_instagram.py", workflow)
        self.assertIn("INSTAGRAM_PUBLISH_ENABLED: 'false'", workflow)
        self.assertIn("REEL_UPLOAD_ENABLED: 'false'", workflow)


if __name__ == "__main__":
    unittest.main()
