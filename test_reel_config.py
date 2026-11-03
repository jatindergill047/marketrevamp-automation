"""Network-free checks for the opt-in Reel configuration."""

import os
import unittest
from unittest.mock import patch

import reel_config


class ReelConfigTests(unittest.TestCase):
    """Ensure Reels never turn on implicitly."""

    def test_disabled_by_default(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertFalse(reel_config.reel_enabled())

    def test_enabled_only_for_true(self):
        for value in ("true", "TRUE", " True "):
            with self.subTest(value=value), patch.dict(os.environ, {"REEL_ENABLED": value}):
                self.assertTrue(reel_config.reel_enabled())
        for value in ("false", "1", "yes", ""):
            with self.subTest(value=value), patch.dict(os.environ, {"REEL_ENABLED": value}):
                self.assertFalse(reel_config.reel_enabled())

    def test_layout_and_voice_defaults(self):
        self.assertEqual((reel_config.REEL_WIDTH, reel_config.REEL_HEIGHT), (1080, 1920))
        self.assertLess(reel_config.SAFE_TOP, reel_config.CAPTION_BAND_TOP)
        self.assertLess(reel_config.CAPTION_BAND_TOP, reel_config.CAPTION_BAND_BOTTOM)
        self.assertLess(reel_config.CAPTION_BAND_BOTTOM, reel_config.REEL_HEIGHT)
        self.assertEqual(reel_config.VOICE, "en-US-AvaNeural")
        self.assertEqual(reel_config.REEL_CONTAINER_POLLS, 40)
        self.assertEqual(len(reel_config.PRONUNCIATIONS), 5)


if __name__ == "__main__":
    unittest.main()
