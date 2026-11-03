"""Opt-in configuration for MarketRevamp Reels; carousels remain the default."""

import os


def reel_enabled() -> bool:
    """Read the opt-in flag at call time; only literal true enables Reels."""
    return os.environ.get("REEL_ENABLED", "false").strip().lower() == "true"


REEL_ENABLED = reel_enabled()
REEL_WIDTH = 1080
REEL_HEIGHT = 1920
SAFE_TOP = 180
CAPTION_BAND_TOP = 1545
CAPTION_BAND_BOTTOM = 1790
MIN_SLIDE_SECONDS = 3.0
SLIDE_PAD_SECONDS = 1.0
ZOOM_MAX = 1.06
VOICE = "en-US-AvaNeural"
REEL_CONTAINER_POLLS = 40
PRONUNCIATIONS = {
    "S&P 500": "S and P five hundred",
    "BTC": "B T C",
    "Nasdaq": "Naz-dak",
    "Anthropic": "an-THROP-ik",
    "OpenAI": "Open A I",
}
