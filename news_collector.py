import json
import urllib.request
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
import re
from html import unescape
from urllib.parse import urlsplit, urlunsplit
from news_quality import select_usable, CLAIM_TERMS, ATTRIBUTION, strip_section_heading


FEEDS = {
    "AI": "https://techcrunch.com/category/artificial-intelligence/feed/",
    "Technology": "https://feeds.arstechnica.com/arstechnica/index",
    "Crypto": "https://www.coindesk.com/arc/outboundfeeds/rss/",
    "Markets": "https://www.cnbc.com/id/100003114/device/rss/rss.html",
    "BBC Technology": "https://feeds.bbci.co.uk/news/technology/rss.xml",
    "BBC Business": "https://feeds.bbci.co.uk/news/business/rss.xml",
}

FEED_CATEGORY = {"BBC Technology": "Technology", "BBC Business": "Markets"}

HEADERS = {"User-Agent": "MarketRevampNewsCollector/1.0"}

KEYWORDS = {
    "AI": [
        "artificial intelligence", " ai ", "ai’s", "ai-", "openai", "chatgpt",
        "anthropic", "claude", "gemini", "nvidia", "machine learning",
        "llm", "gpu", "data center", "datacenter", "robotics",
        "neural network", "ai model", "ai agent",
    ],
    "Technology": [
        "apple", "google", "microsoft", "amazon", "meta", "tesla",
        "semiconductor", "chipmaker", "microchip", "software",
        "cybersecurity", "cloud computing", "quantum computing",
        "startup", "technology", "smartphone", "iphone", "android",
        "computing", "robot", "product launch",
    ],
    "Crypto": [
        "bitcoin", "btc", "ethereum", "ether", "crypto", "blockchain",
        "stablecoin", "tokenized", "tokenization", "defi", "solana",
        "coinbase", "digital asset", "web3", "prediction market",
    ],
    "Markets": [
        "stock", "shares", "nasdaq", "s&p 500", "dow jones",
        "earnings", "inflation", "federal reserve", "interest rate",
        "bond", "treasury", "fixed income", "jpmorgan", "goldman sachs",
        "wall street", "investment", "investor", "401(k)",
        "private funds", "retailers", "retail sales", "economic growth",
        "recession", "oil prices", "gold prices", "commodities",
        "tariff", "ipo", "equity market",
    ],
}

EXCLUDE = [
    "celebrity", "fashion", "football", "soccer", "recipe",
    "wedding", "movie review", "press secretary", "houthi", "ceasefire",
]


# Summary length is shared with editorial validation.
SUMMARY_MIN_WORDS = 30
SUMMARY_MAX_WORDS = 90


def _tokens(text):
    """Normalize words for comparing a headline with an extracted sentence."""
    return re.findall(r"[a-z0-9]+(?:'[a-z0-9]+)?", text.casefold().replace("’", "'"))


def _strip_headline_prefix(text, headline):
    """Remove repeated article titles, including titles with no trailing period.

    Trafilatura can return 'Headline First paragraph...' as one text block.
    Without this step, sentence selection can reproduce the headline verbatim.
    """
    if not headline:
        return text
    title_words = _tokens(headline)
    if not title_words:
        return text
    # Only strip at the beginning or a line boundary. Do not erase a later
    # mention of the headline from the article body.
    for _ in range(3):
        match = re.match(r"^\s*(?:[^\w\n]*)([^\n]{0,300})", text)
        if not match:
            break
        first_line = match.group(1)
        word_matches = list(re.finditer(r"[A-Za-z0-9]+(?:['’][A-Za-z0-9]+)?", first_line))
        if len(word_matches) < len(title_words):
            break
        prefix = first_line[:word_matches[len(title_words)-1].end()]
        if _tokens(prefix) != title_words:
            break
        # Strip title punctuation too, but keep the first word of the body.
        rest = first_line[len(prefix):]
        rest = re.sub(r"^[\s:|–—\-]+", "", rest)
        if rest.startswith((".", "!", "?")):
            rest = rest[1:].lstrip()
        text = rest + text[match.end():]
        text = text.lstrip()
    return text


def _sentence_candidates(article_text, headline=""):
    """Get clean complete sentences; reject titles, boilerplate and duplicates."""
    if not article_text:
        return []
    text = unescape(re.sub(r"<[^>]+>", " ", article_text))
    text = re.sub(r"[ \t]+", " ", text).strip()
    text = _strip_headline_prefix(text, headline)
    text = re.sub(r"\s+", " ", text).strip()
    # Splitting at punctuation is conservative: keep complete sentences.
    parts = re.split(r"(?<=[.!?])\s+(?=[\"'“‘(]*[A-Z0-9])", text)
    headline_tokens = _tokens(headline)
    headline_set = set(headline_tokens)
    unwanted = (
        "subscribe", "newsletter", "advertisement", "sign up", "read more",
        "click here", "all rights reserved", "cookie policy", "privacy policy",
        "follow us", "terms of service", "accept cookies", "share this article",
        "related articles", "download our app", "sign in", "log in",
    )
    results = []
    seen = []
    for position, part in enumerate(parts):
        sentence = strip_section_heading(part.strip(" \t\r\n-•"))
        words = sentence.split()
        if not 8 <= len(words) <= 45 or not re.search(r"[.!?][\"'”’)]?$", sentence):
            continue
        lower = sentence.casefold()
        if any(phrase in lower for phrase in unwanted):
            continue
        tokens = _tokens(sentence)
        token_set = set(tokens)
        if len(token_set) < 7:
            continue
        # A full headline or near-identical sentence adds no news value.
        if headline_tokens:
            overlap = len(token_set & headline_set)
            precision = overlap / max(len(token_set), 1)
            recall = overlap / max(len(headline_set), 1)
            if (precision >= 0.82 and recall >= 0.80) or (
                tokens[:len(headline_tokens)] == headline_tokens
            ):
                continue
        if any(len(token_set & old) / max(min(len(token_set), len(old)), 1) >= 0.76
               for old in seen):
            continue
        seen.append(token_set)
        results.append((position, sentence, len(words), token_set))
    return results


def generate_summary(article_text, min_words=SUMMARY_MIN_WORDS,
                     max_words=SUMMARY_MAX_WORDS, headline=""):
    """Select distinct, complete, relevant article sentences for human review.

    Preferred length is 40–60 words; 30–90 is accepted. This is extractive,
    not a verified or rewritten summary. Returns empty on insufficient quality.
    """
    if not 1 <= min_words <= max_words:
        raise ValueError("Invalid summary word limits")
    candidates = _sentence_candidates(article_text, headline)
    if not candidates:
        return ""
    headline_tokens = set(_tokens(headline))
    ranked = []
    for position, sentence, count, tokens in candidates[:60]:
        relevance = len(tokens & headline_tokens) / max(len(headline_tokens), 1)
        has_number = bool(re.search(r"\d", sentence))
        has_detail = bool(re.search(
            r"\b(?:said|reported|announced|according to|because|after|while|"
            r"however|million|billion|percent|regulation|research)\b",
            sentence, re.I,
        ))
        # Favor attributed reporting; never turn an allegation into a bare fact.
        attribution_bonus = 1.5 if ATTRIBUTION.search(sentence) else 0
        sensitive_penalty = 20 if CLAIM_TERMS.search(sentence) and not ATTRIBUTION.search(sentence) else 0
        score = (5 * relevance + 0.8 * has_number + 0.5 * has_detail
                 + attribution_bonus - sensitive_penalty - 0.10 * position)
        ranked.append((position, sentence, count, tokens, score))

    # Beam search: favor source-relevant facts, coherent nearby sentences,
    # and a natural length. Never shorten a sentence to hit a word count.
    beams = [(0, (), frozenset(), 0.0, None)]
    for index, (position, sentence, count, tokens, score) in enumerate(ranked):
        expanded = list(beams)
        for total, indices, used, quality, last_position in beams:
            if len(indices) >= 4 or total + count > max_words:
                continue
            if used and len(tokens & used) / max(len(tokens), 1) > 0.60:
                continue
            gap_penalty = 0 if last_position is None else 0.18 * max(0, position - last_position - 1)
            expanded.append((total + count, indices + (index,), used | tokens,
                             quality + score - gap_penalty, position))
        buckets = {}
        for state in expanded:
            key = (len(state[1]), state[0] // 5)
            buckets.setdefault(key, []).append(state)
        beams = [state for group in buckets.values()
                 for state in sorted(group, key=lambda x: x[3], reverse=True)[:12]]

    valid = [state for state in beams if min_words <= state[0] <= max_words
             and len(state[1]) >= 2]
    if not valid:
        return ""

    def rank(state):
        total, indices, _, quality, _ = state
        outside_preferred = max(0, 40 - total, total - 60)
        return (quality - 0.22 * outside_preferred - 0.02 * abs(total - 50),
                -len(indices))

    best = max(valid, key=rank)
    chosen = sorted((ranked[i] for i in best[1]), key=lambda item: item[0])
    summary = " ".join(item[1] for item in chosen)
    # Final safety check: no exact title, even if it appeared as a fragment.
    if headline and headline.casefold().strip(" .!?\n") in summary.casefold():
        return ""
    return summary


def fetch_article_text(url):
    """Extract article text using Trafilatura."""
    if not url or not url.startswith(("https://", "http://")):
        return ""

    try:
        import trafilatura

        downloaded = None
        for attempt in range(3):
            try:
                downloaded = trafilatura.fetch_url(url)
            except (OSError, TimeoutError):
                downloaded = None
            if downloaded:
                break
            if attempt < 2:
                time.sleep(2 ** attempt)
        if not downloaded:
            print(f"Could not download article after retries: {url}")
            return ""

        article_text = trafilatura.extract(
            downloaded,
            include_comments=False,
            include_tables=False,
            favor_precision=True,
        )

        if not article_text:
            print(f"Could not extract article text: {url}")
            return ""

        return article_text[:12000]

    except Exception as error:
        print(f"Article extraction failed: {url} ({error})")
        return ""


def get_text(item, names):
    for name in names:
        element = item.find(name)
        if element is not None and element.text:
            return element.text.strip()
    return ""


def score_article(article):
    title = " " + article["title"].lower() + " "

    if any(word in title for word in EXCLUDE):
        return 0

    score = 0
    matched_categories = []

    for category, keywords in KEYWORDS.items():
        matches = sum(1 for keyword in keywords if keyword in title)
        if matches:
            score += matches * 3
            matched_categories.append(category)

    if not matched_categories:
        return 0

    if article["category"] in matched_categories:
        score += 4

    impact_keywords = [
        "earnings", "revenue", "profit", "interest rate",
        "federal reserve", "inflation", "regulation", "regulator",
        "sec ", "lawsuit", "antitrust", "acquisition", "merger",
        "investment", "launch", "breakthrough", "approval", "ban",
        "tariff", "etf", "funding", "billion", "trillion", "imf",
    ]
    impact_matches = sum(1 for word in impact_keywords if word in title)
    score += min(impact_matches * 3, 9)

    age_hours = (
        datetime.now(timezone.utc)
        - datetime.fromisoformat(article["published"])
    ).total_seconds() / 3600

    if age_hours <= 12:
        score += 4
    elif age_hours <= 24:
        score += 2
    else:
        score += 1

    article["matched_categories"] = matched_categories
    article["impact_signals"] = impact_matches
    return score


def infer_category(article):
    """Classify the headline's main subject, not an incidental mentioned asset.

    Explicit AI actors/models take precedence over incidental crypto-wallet
    mentions; explicit blockchain/exchange events remain Crypto. When no
    clear headline-level signal exists, retain the feed/category fallback.
    """
    title = article["title"].casefold()
    def has_any(terms):
        return any(re.search(r"\\b" + re.escape(term) + r"\\b", title)
                   for term in terms)

    ai = has_any(("openai", "chatgpt", "anthropic", "claude", "gemini",
                  "artificial intelligence", "ai model", "ai models",
                  "ai agent", "ai agents", "ai safety", "machine learning",
                  "large language model", "llm"))
    crypto = has_any(("bitcoin", "ethereum", "ether", "crypto", "cryptocurrency",
                      "blockchain", "stablecoin", "solana", "defi", "coinbase",
                      "crypto exchange", "bitcoin etf"))
    technology = has_any(("cybersecurity", "software developer", "software engineer",
                          "coding jobs", "smartphone", "data breach", "malware"))
    # 'crypto wallet' or 'cryptocurrency' as the object of an AI incident
    # should not override the explicit AI subject of the headline.
    if ai:
        return "AI"
    if crypto:
        return "Crypto"
    if technology:
        return "Technology"
    matched = article.get("matched_categories", [])
    category = article.get("category")
    if category in matched:
        return category
    return matched[0] if matched else (category or "Technology")


def normalize_article_url(url):
    """Match publisher normalization, ignoring tracking query strings."""
    parts = urlsplit(url.strip())
    if parts.scheme != "https" or not parts.hostname:
        return ""
    return urlunsplit(("https", parts.netloc.lower(), parts.path.rstrip("/") or "/", "", ""))


def published_article_urls(history_path=Path("instagram_publish_history.json")):
    """Fail closed if publishing history cannot be read or is malformed."""
    if not history_path.exists():
        raise RuntimeError("Publishing history missing: cannot safely select fresh stories.")
    history = json.loads(history_path.read_text(encoding="utf-8"))
    if not isinstance(history, dict):
        raise RuntimeError("Publishing history must be a JSON object.")
    published = set()
    for record in history.values():
        if not isinstance(record, dict):
            raise RuntimeError("Invalid publishing history record.")
        if record.get("status") == "published":
            for url in record.get("article_urls", []):
                normalized = normalize_article_url(url)
                if not normalized:
                    raise RuntimeError("Invalid published article URL in history.")
                published.add(normalized)
    return published


def collect_news():
    articles = []
    cutoff = datetime.now(timezone.utc) - timedelta(hours=36)
    feed_status = {}

    for category, url in FEEDS.items():
        count = 0
        try:
            request = urllib.request.Request(url, headers=HEADERS)
            xml_data = None
            for attempt in range(3):
                try:
                    with urllib.request.urlopen(request, timeout=20) as response:
                        xml_data = response.read()
                    break
                except (OSError, TimeoutError):
                    if attempt == 2:
                        raise
                    time.sleep(2 ** attempt)

            root = ET.fromstring(xml_data)
            for item in root.findall(".//item"):
                title = get_text(item, ["title"])
                link = get_text(item, ["link"])
                published = get_text(item, ["pubDate"])
                if not title or not link or not published:
                    continue

                try:
                    date = parsedate_to_datetime(published)
                    if date.tzinfo is None:
                        date = date.replace(tzinfo=timezone.utc)
                except (ValueError, TypeError):
                    continue

                if date < cutoff:
                    continue

                articles.append({
                    "category": FEED_CATEGORY.get(category, category),
                    "feed_name": category,
                    "title": title,
                    "url": link,
                    "published": date.isoformat(),
                })
                count += 1

            feed_status[category] = {"status": "success", "articles": count}
        except Exception as error:
            feed_status[category] = {"status": "error", "message": str(error)}

        print(f"{category}: {feed_status[category]}")

    unique = []
    seen = set()
    for article in articles:
        key = article["url"].split("?")[0].rstrip("/")
        if key not in seen:
            seen.add(key)
            article["score"] = score_article(article)
            unique.append(article)


    published_urls = published_article_urls()
    eligible = [
        article for article in unique
        if article["score"] > 0
        and normalize_article_url(article["url"]) not in published_urls
    ]
    print(f"Fresh eligible articles: {len(eligible)}")
    # Multiple reports indicate independent coverage, not complete verification.
    # All candidate headlines are supplied for independent-source matching.

    # Apply source-aware near-duplicate screening and maintain coverage when
    # one category's first article fails source extraction or summary checks.
    selected = select_usable(
        eligible,
        infer_category,
        fetch_article_text,
        generate_summary,
        SUMMARY_MIN_WORDS,
        SUMMARY_MAX_WORDS,
    )
    for story in selected:
        print(f"Selected: {story['title']} | summary words: {story['summary_word_count']}")


    output = {
        "collected_at": datetime.now(timezone.utc).isoformat(),
        "article_count": len(unique),
        "eligible_count": len(eligible),
        "feed_status": feed_status,
        "selected_count": len(selected),
        "selected_stories": selected,
        "articles": unique,
    }

    Path("news_results.json").write_text(
        json.dumps(output, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print(f"Collected: {len(unique)} articles")
    print(f"Eligible: {output['eligible_count']}")
    print(f"Selected: {len(selected)} candidate stories")
    for index, story in enumerate(selected, 1):
        print(f"{index}. [{story['selected_category']}] {story['title']}")


if __name__ == "__main__":
    collect_news()
