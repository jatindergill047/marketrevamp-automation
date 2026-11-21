"""R67: fail-closed, daily news candidates for Reel editorial review.

Reuses the existing source-screened news collector; it never authorizes a render,
upload, editorial approval, or Instagram publication. Source-backed does not
mean independently fact-checked.
"""
import argparse
import json
import re
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo

from news_collector import normalize_article_url
from news_quality import same_event

TOPICS = frozenset(("AI", "Technology", "Crypto", "Markets"))
REQUIRED_STORIES = 7
MAX_AGE_HOURS = 48
TORONTO = ZoneInfo("America/Toronto")


def _source(url):
    if not isinstance(url, str):
        raise ValueError("Article URL must be a string")
    parsed = urlsplit(url.strip())
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError("Article URL must be an HTTPS publisher address")
    if parsed.port not in (None, 443):
        raise ValueError("Unexpected article URL port")
    if parsed.hostname in ("localhost",) or not re.fullmatch(
        r"[a-z0-9.-]+\.[a-z]{2,}", parsed.hostname.lower()
    ):
        raise ValueError("Article URL must have a valid publisher hostname")
    normalized = normalize_article_url(url)
    if not normalized:
        raise ValueError("Could not normalize article URL")
    return normalized


def load_published_history(path):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("Published history must be a JSON object")
    urls = set()
    for record in data.values():
        if not isinstance(record, dict):
            raise ValueError("Malformed publishing history entry")
        if record.get("status") == "published":
            articles = record.get("article_urls")
            if not isinstance(articles, list):
                raise ValueError("Published entry missing article URL list")
            for link in articles:
                urls.add(_source(link))
    return urls


def review_package(results, published_urls, *, now):
    """Reject incomplete, stale, unsupported, or duplicate inputs any day."""
    local = now.astimezone(TORONTO)
    if not isinstance(results, dict) or not isinstance(results.get("selected_stories"), list):
        raise ValueError("Missing collector selection")
    stories = results["selected_stories"]
    if len(stories) != REQUIRED_STORIES or results.get("selected_count") != REQUIRED_STORIES:
        raise ValueError("Exactly seven source-screened stories are required")
    if not isinstance(published_urls, set):
        raise ValueError("Authoritative published URLs are required")
    if not isinstance(results.get("feed_status"), dict) or not any(
        status.get("status") == "success" for status in results["feed_status"].values()
        if isinstance(status, dict)
    ):
        raise ValueError("No successful verified source feed")
    chosen = []
    seen = set()
    for story in stories:
        if not isinstance(story, dict):
            raise ValueError("Invalid story entry")
        url = _source(story.get("url"))
        if url in published_urls or url in seen:
            raise ValueError("Previously published or repeated source URL")
        title = story.get("title")
        category = story.get("selected_category")
        summary = story.get("summary")
        source_text = story.get("article_text")
        check = story.get("summary_screening", {})
        if not isinstance(title, str) or not title.strip() or len(title) > 180:
            raise ValueError("Missing or excessive headline")
        if category not in TOPICS:
            raise ValueError("Missing or unsupported editorial topic")
        if not isinstance(summary, str) or not 30 <= len(summary.split()) <= 90:
            raise ValueError("Unusable article summary")
        if not isinstance(source_text, str) or not source_text.strip():
            raise ValueError("Missing extracted publisher text")
        if not isinstance(check, dict) or not check.get("passed") or (
            check.get("reason") != "source_matched_not_fact_checked"
        ):
            raise ValueError("Summary not supported by publisher extraction")
        if story.get("screening_passed") is not True or story.get("fact_checked") is not False:
            raise ValueError("Source provenance screen failed")
        published = datetime.fromisoformat(story.get("published", ""))
        if published.tzinfo is None:
            raise ValueError("Article timestamp must contain timezone")
        age = (now - published).total_seconds()/3600
        if not 0 <= age <= MAX_AGE_HOURS:
            raise ValueError("Outside current 48-hour source window")
        if any(same_event(title, other["headline"]) for other in chosen):
            raise ValueError("Overlapping news event detected")
        seen.add(url)
        chosen.append({
            "headline": title.strip(),
            "category": category,
            "summary": summary.strip(),
            "source_url": url,
            "source_name": story.get("feed_name") or urlsplit(url).hostname,
            "published_at": published.isoformat(),
            "fact_check_status": "source_matched_not_independently_fact_checked",
            "corroboration_status": story.get("corroboration_status", "single_source"),
            "editorial_approved": False,
        })
    categories = {story["category"] for story in chosen}
    if len(categories) < 3:
        raise ValueError("Insufficient category diversity")
    return {
        "version": "R67",
        "status": "review_only",
        "toronto_date": local.date().isoformat(),
        "collected_at": now.isoformat(),
        "story_count": REQUIRED_STORIES,
        "editorial_approved": False,
        "published": False,
        "cloudinary_uploaded": False,
        "instagram_published": False,
        "render_authorized": False,
        "fact_check_disclaimer": "Publisher text matched; independent editorial fact checking pending",
        "stories": chosen,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description="Never-publish R67 daily collector")
    parser.add_argument("--collector-result", default="news_results.json")
    parser.add_argument("--history", required=True)
    parser.add_argument("--output", default="r67_review/review_sources.json")
    args = parser.parse_args(argv)
    now = datetime.now(TORONTO)
    published = load_published_history(args.history)
    # Import lazily: do not run network collection for offline review package tests.
    from news_collector import collect_news
    if args.collector_result == "news_results.json":
        collect_news(history_path=Path(args.history))
    results = json.loads(Path(args.collector_result).read_text(encoding="utf-8"))
    package = review_package(results, published, now=now)
    target = Path(args.output)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(package, indent=2, ensure_ascii=False)+"\n", encoding="utf-8")
    print("R67_REVIEW_ONLY", package["toronto_date"], package["story_count"])


if __name__ == "__main__":
    main()
