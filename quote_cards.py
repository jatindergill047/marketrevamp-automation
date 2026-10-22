"""Conservative, reversible quote-card *preview* experiment.

No production collector, manifest, upload or publishing module imports this file.
Only the Safe Validation preview script uses it. Quote text is never rewritten.
"""
import re

from carousel_config import CAROUSEL_SIZE

MIN_QUOTE_WORDS = 12
MAX_QUOTE_WORDS = 38
MAX_QUOTE_LENGTH = 285

# Require matched typographic or plain ASCII double quotation marks.
_DIRECT_QUOTE = re.compile(
    r'(?P<open>["“])(?P<text>[^"“”\n]{45,340})(?P<close>["”])'
)
_NAME = (r"[A-Z][a-z]+(?:[-'][A-Za-z]+)? "
         r"[A-Z][a-z]+(?:[-'][A-Za-z]+)?"
         r"(?: [A-Z][a-z]+(?:[-'][A-Za-z]+)?)?")
_VERBS = r"(?:said|says|stated|wrote|explained|noted)"
_BEFORE = re.compile(rf"(?P<speaker>{_NAME})\s+{_VERBS}\s*[:,]?\s*$")
_AFTER_VERB = re.compile(
    rf"^\s*[,;:.!?]?\s*{_VERBS}\s+(?P<speaker>{_NAME})\b"
)
_AFTER_NAME = re.compile(
    rf"^\s*[,;:.!?]?\s*(?P<speaker>{_NAME})\s+{_VERBS}\b"
)
_UNSAFE_COPY = re.compile(
    r"\b(?:subscribe|click here|read more|sign up|our newsletter|"
    r"excited to announce|game changer)\b", re.I
)
_STOPWORDS = {
    "this", "that", "with", "from", "which", "these", "those",
    "they", "their", "will", "could", "would", "about", "after",
    "into", "have", "your", "what", "when", "news",
}
_STRONG_DETAILS = re.compile(
    r"\b(?:revenue|fees|costs?|profits?|customers?|launch|growth|"
    r"million|billion|percent|declined|increased|reduced|"
    r"security|privacy|risks?|savings|supply|demand)\b", re.I
)


def attributed_quote_candidates(article_text, headline=""):
    """Return *exact* 12–38-word source quotes with nearby two-word names.

    Only a tightly attached "Maya Chen said, “...”" or
    "“...,” said Maya Chen" qualifies. Ambiguous surnames, free-floating
    quotations and indirect speech do not qualify.
    """
    if not isinstance(article_text, str) or not article_text.strip():
        return []
    topic = {
        word for word in re.findall(r"[a-z0-9]+", headline.casefold())
        if len(word) > 3 and word not in _STOPWORDS
    }
    found = []
    for match in _DIRECT_QUOTE.finditer(article_text):
        opener, closer = match.group("open"), match.group("close")
        if (opener == "“" and closer != "”") or (
            opener == '"' and closer != '"'
        ):
            continue
        raw = match.group("text")
        quote = raw.strip()
        if quote != raw or "\n" in quote:
            # Avoid stitching or silently modifying source wording.
            continue
        words = quote.split()
        if not MIN_QUOTE_WORDS <= len(words) <= MAX_QUOTE_WORDS:
            continue
        if len(quote) > MAX_QUOTE_LENGTH or quote.startswith("..."):
            continue
        if quote.endswith("...") or _UNSAFE_COPY.search(quote):
            continue

        # A speaker must be immediately attached to this quotation.
        before = article_text[max(0, match.start() - 105):match.start()]
        after = article_text[match.end():match.end() + 95]
        name_match = _BEFORE.search(before)
        if name_match is None:
            name_match = _AFTER_VERB.match(after) or _AFTER_NAME.match(after)
        if name_match is None:
            continue
        speaker = name_match.group("speaker")
        if speaker.casefold().split()[0] in {
            "the", "this", "that", "according", "chief", "executive",
            "research", "company", "market",
        }:
            continue
        terms = set(re.findall(r"[a-z0-9]+", quote.casefold()))
        overlap = len(terms & topic)
        specific = bool(_STRONG_DETAILS.search(quote) or re.search(r"\d", quote))
        # Deterministic scoring, no synthesized wording.
        score = 3 * overlap + (4 if specific else 0) - 0.003 * match.start()
        found.append({
            "text": quote,
            "speaker": speaker,
            "word_count": len(words),
            "score": score,
        })
    return sorted(found, key=lambda q: q["score"], reverse=True)


def best_quote(article_text, headline=""):
    """Return one source-supported quote, or None (never invent fallback)."""
    options = attributed_quote_candidates(article_text, headline)
    return options[0] if options else None


def select_one_quote(stories):
    """Select at most one quote across the *seven* existing stories.

    If no article has a safe quote, keep all seven regular news cards.
    Prefer middle slides for a natural editorial carousel rhythm.
    """
    if len(stories) != CAROUSEL_SIZE:
        raise ValueError("Quote-card preview requires exactly seven stories")
    eligible = []
    for idx, story in enumerate(stories):
        quote = best_quote(story.get("article_text", ""),
                           story.get("title", ""))
        if quote:
            # Avoid first/last slide where possible without forcing weak copy.
            mid_bonus = 1 if 1 <= idx <= CAROUSEL_SIZE - 2 else 0
            eligible.append((quote["score"] + mid_bonus, idx, quote))
    if not eligible:
        return None, None
    _, idx, quote = max(eligible, key=lambda item: (item[0], -item[1]))
    return idx, quote


def quote_matches_source(story, quote):
    """Re-check original article text and speaker before drawing anything."""
    if not isinstance(quote, dict):
        return False
    options = attributed_quote_candidates(
        story.get("article_text", ""), story.get("title", "")
    )
    return any(
        q["text"] == quote.get("text")
        and q["speaker"] == quote.get("speaker")
        for q in options
    )
