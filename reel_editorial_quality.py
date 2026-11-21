"""Reel-only headline relevance and duplicate-event checks.

A publisher-matched summary can still discuss a tangential paragraph. Keep
only summaries that explain the story headline; never manufacture context.
These are conservative editorial heuristics, not independent fact checking.
"""
import re
from news_quality import story_terms, same_event

ENTITIES = (
    "anthropic", "openai", "google", "meta", "microsoft", "apple", "nvidia",
    "amazon", "tesla", "bitcoin", "ethereum", "coinbase", "solana",
    "spacex", "kalshi", "instinct", "claude", "chatgpt",
)
EVENT_GROUPS = {
    "ipo": (r"\bipo\b", r"\bpublic offering\b", r"\bpublic debut\b"),
    "earnings": (r"\bearnings\b", r"\bquarterly results?\b", r"\bprofits?\b"),
    "funding": (r"\bfunding\b", r"\braises?\b", r"\bfinancing\b"),
    "regulatory": (r"\bregulation\b", r"\bregulators?\b", r"\blawsuit\b"),
    "acquisition": (r"\bacquires?\b", r"\bacquisition\b", r"\bmerger\b"),
}


def event_groups(headline):
    value = str(headline or "").casefold()
    return {name for name, phrases in EVENT_GROUPS.items()
            if any(re.search(pattern, value) for pattern in phrases)}


def same_reel_event(first, second):
    if same_event(first, second):
        return True
    a = str(first or "").casefold()
    b = str(second or "").casefold()
    shared_entities = {e for e in ENTITIES if re.search(r"\b"+e+r"\b", a)
                       and re.search(r"\b"+e+r"\b", b)}
    return bool(shared_entities and event_groups(a) & event_groups(b))


def sentence_supports_headline(headline, sentence):
    """Narrated context must directly concern the same named news event."""
    if not isinstance(sentence, str) or not isinstance(headline, str):
        return False
    anchor = story_terms(headline) - {"your", "here", "are", "can", "out", "top"}
    if anchor & story_terms(sentence):
        return True
    if re.search(r"\\bprediction markets?\\b", headline, re.I) and re.search(
            r"\\b(?:kalshi|cftc|event contracts?)\\b", sentence, re.I):
        return True
    return False


def summary_supports_headline(headline, summary):
    """Source-extracted context must include meaningful headline support."""
    if not isinstance(summary, str) or not isinstance(headline, str):
        return False
    return (bool(headline.strip()) and len(summary.split()) >= 30
            and sentence_supports_headline(headline, summary))


def reel_story_guard(article, already_selected):
    """Return False to try the next publisher-screened candidate."""
    headline = article.get("title", "")
    summary = article.get("summary", "")
    if not summary_supports_headline(headline, summary):
        return False
    return not any(same_reel_event(headline, old.get("title", ""))
                   for old in already_selected)
