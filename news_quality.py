from carousel_config import CAROUSEL_SIZE
"""Conservative source-aware quality checks for MarketRevamp news selection.

This is heuristic screening, NOT independent fact-checking or confirmation.
"""
import re
from urllib.parse import urlsplit

GENERIC = {
    "the", "and", "for", "with", "from", "that", "this", "have",
    "into", "about", "after", "before", "while", "will", "could",
    "would", "says", "said", "over", "under", "what", "why", "how",
    "its", "their", "new", "latest", "today", "update", "updates",
    "market", "markets", "stock", "stocks", "shares", "investors",
    "tech", "technology", "company", "companies", "report", "reports",
    "analysis", "breaking", "amid", "more", "than", "some", "most",
    "news", "year", "years", "week", "next", "sees", "seen", "rise",
    "rises", "fall", "falls", "higher", "lower", "price", "prices",
    "billion", "million", "trillion", "percent", "dollar", "dollars",
}


def story_terms(title):
    tokens = re.findall(r"[a-z0-9]+", str(title).casefold())
    return {token for token in tokens if len(token) >= 3 and token not in GENERIC}


def same_event(title_a, title_b):
    """Flag unusually close story headlines, not merely a shared topic."""
    a, b = story_terms(title_a), story_terms(title_b)
    if len(a) < 3 or len(b) < 3:
        return False
    intersection = len(a & b)
    if intersection < 3:
        return False
    # Require both high containment and high overlap, preventing broad
    # collisions such as unrelated Bitcoin stories or earnings releases.
    containment = intersection / min(len(a), len(b))
    jaccard = intersection / len(a | b)
    return containment >= 0.8 and jaccard >= 0.55


def is_repeat_event(story, selected):
    return any(same_event(story["title"], chosen["title"]) for chosen in selected)


def source_domain(url):
    host = urlsplit(url).hostname or ""
    return host.lower().removeprefix("www.")


def prioritize_diversity(candidates, inferred_category):
    """Yield highest-ranked candidate in each of four topics, then backups.

    Re-evaluate after extraction failure without sacrificing category diversity.
    """
    ordered = sorted(candidates, key=lambda x: (x["score"], x["published"]), reverse=True)
    categories = ("AI", "Technology", "Crypto", "Markets")
    first = []
    visited = set()
    for category in categories:
        for story in ordered:
            if inferred_category(story) == category and story["url"] not in visited:
                first.append(story)
                visited.add(story["url"])
                break
    return first + [story for story in ordered if story["url"] not in visited]



# These checks establish fidelity to the publisher's extracted article,
# not independent factual verification.
CLAIM_TERMS = re.compile(
    r"\b(?:record(?:ed|ing|s)?|spy|spied|steal|stole|stolen|hack(?:ed|ing|s)?|"
    r"breach(?:ed|es)?|leak(?:ed|s)?|fraud|scam|illegal|"
    r"without (?:consent|permission)|violat(?:ed|es|ing))\b", re.I
)
ATTRIBUTION = re.compile(
    r"\b(?:according to|reported|reports|reportedly|alleged|allegedly|"
    r"claimed|claims|said|says|stated|told|accused|"
    r"users? (?:say|said|reported|claim)|researchers? (?:say|said|reported)|"
    r"the company (?:said|says|reported)|"
    r"documents? (?:show|showed)|investigators? (?:say|said|found))\b", re.I
)


def _normalized_text(value):
    import unicodedata
    value = unicodedata.normalize("NFKC", str(value))
    value = value.translate(str.maketrans({
        "\u2018": "'", "\u2019": "'", "\u201c": '"',
        "\u201d": '"', "\u2014": "-", "\u2013": "-",
        "\u00a0": " ",
    }))
    return re.sub(r"\s+", " ", value).casefold().strip()


SECTION_HEADINGS = ("unanswered questions", "what happens next", "the bigger picture", "why it matters", "what to know", "what we know", "looking ahead", "the bottom line", "the takeaway", "key takeaways")


def strip_section_heading(sentence):
    """Discard a known article subheading joined to a complete sentence."""
    for heading in SECTION_HEADINGS:
        prefix = heading + " "
        if sentence.casefold().startswith(prefix):
            tail = sentence[len(prefix):]
            if tail and tail[0].isupper():
                return tail
    return sentence


def screen_summary(summary, article_text):
    """Check exact source sentence support and sensitive-claim attribution."""
    if not isinstance(summary, str) or not isinstance(article_text, str):
        return {"passed": False, "reason": "missing_source_text"}
    source = _normalized_text(article_text)
    if not _normalized_text(summary) or not source:
        return {"passed": False, "reason": "missing_source_text"}
    sentences = re.split(r"(?<=[.!?])\s+(?=[\"'“‘(]*[A-Z0-9])", summary)
    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue
        if strip_section_heading(sentence) != sentence:
            return {"passed": False, "reason": "embedded_section_heading"}
        if _normalized_text(sentence) not in source:
            return {"passed": False, "reason": "summary_not_in_source"}
        if CLAIM_TERMS.search(sentence) and not ATTRIBUTION.search(sentence):
            return {"passed": False, "reason": "unattributed_sensitive_claim"}
    return {"passed": True, "reason": "source_matched_not_fact_checked"}


def select_usable(candidates, infer_category, extract, summarize, min_words=30, max_words=90):
    """Return seven distinct, extractable and source-derived articles or fail closed.

    Prefer uncovered categories throughout fallback selection. No AI rewriting.
    """
    pending = prioritize_diversity(candidates, infer_category)
    # Apply a publisher cap when the candidate pool actually has alternatives.
    # Preserve the seven-story fail-closed contract for thin-source days.
    from collections import Counter
    candidate_domains = Counter(source_domain(item["url"]) for item in candidates)
    available_slots = sum(min(3, count) for count in candidate_domains.values())
    per_domain_cap = 3 if available_slots >= CAROUSEL_SIZE else CAROUSEL_SIZE
    domain_counts = {}
    selected = []
    used_categories = set()
    attempted = set()

    while len(selected) < CAROUSEL_SIZE and pending:
        # Re-prioritize missing categories after any failed extraction.
        choice = next((s for s in pending if infer_category(s) not in used_categories), pending[0])
        pending.remove(choice)
        if choice["url"] in attempted or is_repeat_event(choice, selected):
            continue
        domain = source_domain(choice["url"])
        if domain_counts.get(domain, 0) >= per_domain_cap:
            continue
        attempted.add(choice["url"])
        screening = source_screen(choice, candidates)
        if not screening["screening_passed"]:
            continue
        text = extract(choice["url"])
        if not text or not text.strip():
            continue
        summary = summarize(text, headline=choice["title"])
        count = len(summary.split())
        if not min_words <= count <= max_words:
            continue
        quality = screen_summary(summary, text)
        if not quality["passed"]:
            continue
        story = dict(choice)
        story["selected_category"] = infer_category(story)
        story["article_text"] = text
        story["summary"] = summary
        story["verified_summary"] = ""
        story["summary_word_count"] = count
        story["summary_status"] = "ready_for_review"
        story["summary_screening"] = quality
        # Recording source provenance is not a cross-source verification claim.
        story["source_domain"] = source_domain(story["url"])
        story.update(screening)
        selected.append(story)
        domain_counts[domain] = domain_counts.get(domain, 0) + 1
        used_categories.add(story["selected_category"])

    if len(selected) != CAROUSEL_SIZE:
        raise RuntimeError(
            f"Only {len(selected)} fresh, distinct, usable articles available; "
            "refusing to publish an incomplete carousel."
        )
    return selected


# A second independently published headline can corroborate that an event is
# being reported, but it cannot independently verify every claim or figure.
CAUTION_SIGNALS = (
    "rumor", "rumour", "unconfirmed", "allegedly", "alleged",
    "reportedly", "sources say", "anonymous sources",
)


def independent_coverage(story, candidates):
    """Find distinct publisher domains reporting a closely matched event."""
    original_domain = source_domain(story["url"])
    corroborating = {}
    for other in candidates:
        if other["url"] == story["url"]:
            continue
        other_domain = source_domain(other["url"])
        if not other_domain or other_domain == original_domain:
            continue
        if same_event(story["title"], other["title"]):
            corroborating.setdefault(other_domain, {
                "domain": other_domain,
                "url": other["url"],
                "title": other["title"],
            })
    return list(corroborating.values())


def source_screen(story, candidates):
    """Attach honest coverage metadata; hold uncorroborated speculative claims."""
    supporting = independent_coverage(story, candidates)
    cautious = any(term in story["title"].casefold() for term in CAUTION_SIGNALS)
    return {
        "corroboration_status": "multiple_independent_reports" if supporting else "single_source",
        "corroborating_reports": supporting,
        "requires_independent_support": cautious,
        "screening_passed": not cautious or bool(supporting),
        "fact_checked": False,
    }
