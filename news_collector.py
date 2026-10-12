                selected.append(chosen)
                selected_urls.add(article["url"])
                break

    for article in candidates:
        if len(selected) >= 5:
            break
        if article["url"] not in selected_urls:
            chosen = {
                **article,
                "selected_category": (
                    article.get("matched_categories") or [article["category"]]
                )[0],
            }
            selected.append(chosen)
            selected_urls.add(article["url"])

    selected.sort(
        key=lambda item: (item["score"], item["published"]),
        reverse=True,
    )
    return selected[:5]


def collect_news():
    articles = []
    cutoff = datetime.now(timezone.utc) - timedelta(hours=36)
    feed_status = {}

    for category, url in FEEDS.items():
        count = 0
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

    selected = select_top_five(unique)
    output = {
        "collected_at": datetime.now(timezone.utc).isoformat(),
        "article_count": len(unique),
        "eligible_count": sum(article["score"] > 0 for article in unique),
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
