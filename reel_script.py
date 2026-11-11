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
    # Prefer an editor-approved spoken script when provided. Never invent
    # implications or facts from a headline alone.
    spoken = clean_text(story.get("narration_text"))
    if spoken:
        return spoken
    # Professional anchor fallback: lead with verified headline, then concise
    # context and an optional editor-reviewed consequence. No spoken categories,
    # artificial transitions, dramatic hooks, or ellipsis pauses.
    impact = clean_text(story.get("editorial_impact"))
    lead = headline if headline.endswith((".", "!", "?")) else headline + "."
    parts = [lead]
    if summary and summary.casefold().rstrip(".!?") != headline.casefold().rstrip(".!?"):
        parts.append(summary if summary.endswith((".", "!", "?")) else summary + ".")
    if impact and impact.casefold().rstrip(".!?") not in " ".join(parts).casefold():
        parts.append(impact if impact.endswith((".", "!", "?")) else impact + ".")
    return " ".join(parts)


def build_all(stories):
    """Build natural narration without spoken story numbering."""
    return [build_narration(story, index, len(stories)) for index, story in enumerate(stories, start=1)]


def build_connected_all(stories):
    """R23: reviewed story sentences in one continuous, category-free script.

    This function never invents commentary, transitions, or factual connections.
    The caller provides editor-reviewed spoken text for each story.
    """
    if not stories:
        raise ValueError("Connected briefing requires stories")
    if any(not isinstance(story, dict) or not clean_text(story.get("narration_text"))
           for story in stories):
        raise ValueError("Connected briefing requires reviewed narration_text for every story")
    return [clean_text(story["narration_text"]) for story in stories]


def connected_script(stories):
    """Return the uninterrupted narration text for one TTS synthesis."""
    return " ".join(build_connected_all(stories))
