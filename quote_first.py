"""Verified source-backed quote-first carousel arrangement.

Opt-in only. The original seven article objects are not changed; reordering is
applied before news_results.json is saved so images, manifest and caption agree.
"""
from carousel_config import CAROUSEL_SIZE
from quote_cards import select_one_quote, quote_matches_source


def promote_quote_to_first(stories):
    """Move one quoteable real article to slide 1 or fail with no changes.

    Production callers MUST halt rather than publish another layout when
    a promised quote-card first slide cannot be safely constructed.
    """
    if len(stories) != CAROUSEL_SIZE:
        raise ValueError("Exactly seven source-screened stories required")
    if any(s.get("quote_card") for s in stories):
        raise ValueError("Carousel already contains quote metadata")
    original_index, quote = select_one_quote(stories)
    if original_index is None or quote is None:
        raise ValueError("No safe directly attributed quote in seven fresh stories")
    if not quote_matches_source(stories[original_index], quote):
        raise ValueError("Selected quote fails literal source attribution check")
    ordered = [dict(s) for s in stories]
    winner = ordered.pop(original_index)
    winner["quote_card"] = {
        "text": quote["text"],
        "speaker": quote["speaker"],
    }
    ordered.insert(0, winner)
    assert len(ordered) == CAROUSEL_SIZE
    return ordered


def verify_quote_first(stories):
    """Pre-upload integrity check: exactly one literal quote on slide 1."""
    if len(stories) != CAROUSEL_SIZE:
        raise ValueError("Quote-first publication needs seven stories")
    if not stories[0].get("quote_card"):
        raise ValueError("First slide must contain one verified quote")
    if any(s.get("quote_card") for s in stories[1:]):
        raise ValueError("Only slide 1 may contain a quote card")
    if not quote_matches_source(stories[0], stories[0]["quote_card"]):
        raise ValueError("Slide 1 quotation and speaker no longer match source")
    return True
