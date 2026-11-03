"""Build spoken narration for seven MarketRevamp stories."""

import re
import unicodedata

from reel_config import PRONUNCIATIONS


def clean_text(value):
    """Remove emoji and markdown and apply spoken pronunciations."""
    text = str(value or "")
    text = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"(\*\*|__|~~|[`*_#>])", "", text)
    text = "".join(char for char in text if unicodedata.category(char) not in {"So", "Sk", "Cc", "Cs"} and char not in "\ufe0f\u200d")
    for original, spoken in PRONUNCIATIONS.items():
        text = re.sub(r"(?<!\w)" + re.escape(original) + r"(?!\w)", lambda match: spoken, text, flags=re.IGNORECASE)
    return " ".join(text.split())


def build_narration(story, index, total):
    """Format the headline and summary for one narrated story."""
    headline = clean_text(story.get("headline"))
    if not headline:
        raise ValueError("Story headline is required")
    summary = clean_text(story.get("summary"))
    return f"{headline}. {summary}".strip()


def build_all(stories):
    """Build natural narration without spoken story numbering."""
    return [build_narration(story, index, len(stories)) for index, story in enumerate(stories, start=1)]
