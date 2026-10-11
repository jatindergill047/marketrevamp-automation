
import json
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

# Free public RSS feeds
FEEDS = {
    "AI": "https://techcrunch.com/category/artificial-intelligence/feed/",
    "Technology": "https://www.theverge.com/rss/index.xml",
    "Crypto": "https://www.coindesk.com/arc/outboundfeeds/rss/",
    "Markets": "https://www.cnbc.com/id/100003114/device/rss/rss.html",
}

HEADERS = {
    "User-Agent": "MarketRevampNewsCollector/1.0"
}


def get_text(item, names):
    for name in names:
        element = item.find(name)
        if element is not None and element.text:
            return element.text.strip()
    return ""


def collect_news():
    articles = []
    cutoff = datetime.now(timezone.utc) - timedelta(hours=36)

    for category, url in FEEDS.items():
        try:
            request = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(request, timeout=20) as response:
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
                        date = date.replace(tzinfo=timezone.utc)
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

            print(f"{category}: feed checked successfully")

        except Exception as error:
            print(f"{category}: feed unavailable - {error}")

    articles.sort(
        key=lambda article: article["published"],
        reverse=True,
    )

    unique = []
    seen = set()

    for article in articles:
        key = article["url"].split("?")[0].rstrip("/")
        if key not in seen:
            seen.add(key)
            unique.append(article)

    output = {
        "collected_at": datetime.now(timezone.utc).isoformat(),
        "article_count": len(unique),
        "articles": unique,
    }

    Path("news_results.json").write_text(
        json.dumps(output, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print(f"Saved {len(unique)} recent articles")


if __name__ == "__main__":
    collect_news()
