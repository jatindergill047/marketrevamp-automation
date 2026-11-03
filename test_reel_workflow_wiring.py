"""R18 offline assertions for disabled-by-default production Reel wiring."""
import unittest
from pathlib import Path

class ReelWorkflowWiringTests(unittest.TestCase):
    def test_reel_opt_in_is_explicit_and_disabled(self):
        workflow = Path(".github/workflows/marketrevamp.yml").read_text()
        self.assertIn("REEL_ENABLED: 'false'", workflow)
        self.assertIn("REEL_UPLOAD_ENABLED: 'false'", workflow)
        self.assertIn("python prepare_reel.py", workflow)
        self.assertLess(workflow.index("python upload_to_cloudinary.py"), workflow.index("python prepare_reel.py"))
        self.assertLess(workflow.index("python prepare_reel.py"), workflow.index("python prepare_instagram_carousel.py"))
        self.assertIn("continue-on-error: true", workflow)

if __name__ == "__main__":
    unittest.main()
