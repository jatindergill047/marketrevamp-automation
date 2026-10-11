
import json
import re
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

FEEDS = {
    "AI": "https://techcrunch.com/category/artificial-intelligence/feed/",
    "Technology": "https://feeds.arstechnica.com/arstechnica/index",
    "Crypto": "https://www.coindesk.com/arc/outboundfeeds/rss/",
    "Markets": "https://www.cnbc.com/id/100003114/device/rss/rss.html",
}

HEADERS = {
    "User-Agent": "MarketRevampNewsCollector/1.0"
}

KEYWORDS = {
    "AI": [
        "artificial intelligence", " ai ", "openai",
        "chatgpt", "anthropic", "claude", "gemini",
        "nvidia", "machine learning", "llm", "gpu",
        "data center", "datacenter", "robotics",
    ],
    "Technology": [
        "apple", "google", "microsoft", "amazon",
        "meta", "tesla", "semiconductor", "chip",
        "software", "cybersecurity", "cloud",
        "quantum", "startup", "technology",
    ],
    "Crypto": [
        "bitcoin", "btc", "ethereum", "ether",
        "crypto", "blockchain", "stablecoin",
        "token", "defi", "solana", "coinbase",
        "etf", "digital asset",
    ],
    "Markets": [
        "stock", "shares", "nasdaq", "s&p 500",
        "dow jones", "earnings", "inflation",
        "federal reserve", "fed rate", "interest rate",
        "bond", "treasury", "oil price", "gold price",
        "market", "investor", "tariff",
    ],
}

EXCLUDE = [
    "celebrity", "fashion", "football", "soccer",
    "recipe", "wedding", "movie review",
    "press secretary", "houthi", "ceasefire",
]


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
        matches = sum(
            1 for keyword in keywords
            if keyword in title
        )

        if matches:
            score += matches * 3
            matched_categories.append(category)

    if not matched_categories:
        return 0

    if article["category"] in matched_categories:
        score += 3

    age_hours = (
        datetime.now(timezone.utc)
        - datetime.fromisoformat(article["published"])
    ).total_seconds() / 3600

    if age_hours <= 12:
        score += 3
    elif age_hours <= 24:
        score += 2
    else:
        score += 1

    article["matched_categories"] = matched_categories
    return score


def select_top_five(articles):
    candidates = [
        article for article in articles
        if article["score"] > 0
    ]

    candidates.sort(
        key=lambda item: (
            item["score"],
            item["published"],
        ),
        reverse=True,
    )

    selected = []
    selected_urls = set()

    # First, attempt to represent each news category.
    for category in FEEDS:
        for article in candidates:
            if (
                category in article["matched_categories"]
                and article["url"] not in selected_urls
            ):
                selected.append(article)
                selected_urls.add(article["url"])
                break

    # Fill remaining slots with highest-scoring stories.
    for article in candidates:
        if len(selected) >= 5:
            break

        if article["url"] not in selected_urls:
            selected.append(article)
            selected_urls.add(article["url"])

    return selected[:5]


def collect_news():
    articles = []
    cutoff = datetime.now(timezone.utc) - timedelta(hours=36)
    feed_status = {}

    for category, url in FEEDS.items():
        count = 0

        try:
            request = urllib.request.Request(
                url, headers=HEADERS
            )

            with urllib.request.urlopen(
                request, timeout=20
            ) as response:
                xml_data = response.read()

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
                        date = date.replace(
                            tzinfo=timezone.utc
                        )
                except (ValueError, TypeError):
                    continue

                if date < cutoff:
                    continue

                articles.append({
                    "category": category,
                    "title": title,
                    "url": link,
                    "published": date.isoformat(),
                })
                count += 1

            feed_status[category] = {
                "status": "success",
                "articles": count,
            }

        except Exception as error:
            feed_status[category] = {
                "status": "error",
                "message": str(error),
            }

        print(f"{category}: {feed_status[category]}")

    unique = []
    seen = set()

    for article in articles:
        key = article["url"].split("?")[0].rstrip("/")

        if key not in seen:
            seen.add(key)
            article["score"] = score_article(article)
            unique.append(article)

    selected = select_top_five(unique)

    output = {
        "collected_at": datetime.now(timezone.utc).isoformat(),
        "article_count": len(unique),
        "eligible_count": sum(
            article["score"] > 0 for article in unique
        ),
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
        print(f"{index}. [{story['category']}] {story['title']}")


if __name__ == "__main__":
    collect_news()
