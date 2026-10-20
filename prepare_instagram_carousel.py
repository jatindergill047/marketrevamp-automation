"""Validate seven source-grounded stories and prepare Instagram manifest."""

from carousel_config import CAROUSEL_SIZE

import json
from pathlib import Path
from datetime import datetime, timezone, timedelta
from urllib.parse import urlsplit, urlunsplit
from news_quality import screen_summary
from caption_format import compose_caption

SOURCE = Path("cloudinary_uploads.json")
OUTPUT = Path("instagram_carousel_manifest.json")
NEWS_SOURCE = Path("news_results.json")

data = json.loads(SOURCE.read_text(encoding="utf-8"))
images = data["images"]
news_data = json.loads(
    NEWS_SOURCE.read_text(encoding="utf-8")
)

stories = news_data.get("selected_stories", [])

if len(stories) != CAROUSEL_SIZE:
    raise ValueError(
        f"Expected 7 news stories, found {len(stories)}"
    )
    
for index, story in enumerate(stories, start=1):
    # Defense in depth: speculative stories require a second independent
    # publisher's matched coverage; this does not certify factual accuracy.
    if story.get("requires_independent_support") and not story.get("corroborating_reports"):
        raise ValueError(f"Story {index} lacks independent coverage for a speculative headline.")

    if story.get("summary_status") != "ready_for_review":
        raise ValueError(
            f"Story {index} failed summary quality screening."
        )

    summary = story.get("summary", "").strip()

    if not summary:
        raise ValueError(
            f"Story {index} has an empty summary."
        )

    word_count = len(summary.split())

    if not 30 <= word_count <= 90:
        raise ValueError(
            f"Story {index} has {word_count} summary words. "
            "Expected between 30 and 90."
        )

    if story.get("summary_word_count") != word_count:
        raise ValueError(
            f"Story {index} has an inconsistent summary word count."
        )

    # Recheck publisher-text fidelity immediately before enabling publication.
    # This is a source-attribution safeguard, NOT a claim of fact-checking.
    quality = screen_summary(summary, story.get("article_text", ""))
    if not quality["passed"]:
        raise ValueError(
            f"Story {index} failed source fidelity / attribution: {quality['reason']}"
        )
    if story.get("summary_screening", {}).get("passed") is not True:
        raise ValueError(f"Story {index} has no passing summary screening record.")

    article_text = story.get("article_text", "")

    if not isinstance(article_text, str) or not article_text.strip():
        raise ValueError(
            f"Story {index} has no extracted article text."
        )


    try:
        published = datetime.fromisoformat(story["published"])
    except (KeyError, TypeError, ValueError):
        raise ValueError(
            f"Story {index} has an invalid publication date."
        )

    if published.tzinfo is None:
        raise ValueError(
            f"Story {index} has no publication timezone."
        )

    age = datetime.now(timezone.utc) - published

    if not timedelta(0) <= age <= timedelta(hours=36):
        raise ValueError(
            f"Story {index} is outside the 36-hour news window."
        )

if len(images) != CAROUSEL_SIZE:
    raise ValueError(f"Expected 7 images, found {len(images)}")

slides = []

for number, item in enumerate(images, start=1):
    expected = f"slide_{number:02d}.png"

    if item["slide"] != expected:
        raise ValueError(f"Expected {expected}, got {item['slide']}")

    original = item["secure_url"]
    parts = urlsplit(original)

    if parts.scheme != "https" or parts.netloc != "res.cloudinary.com":
        raise ValueError("Unexpected image host")

    prefix = "/image/upload/"
    if prefix not in parts.path:
        raise ValueError("Unexpected Cloudinary URL")

    new_path = parts.path.replace(
        prefix, "/image/upload/f_jpg/", 1
    )

    jpeg_url = urlunsplit((
        parts.scheme, parts.netloc, new_path, "", ""
    ))

    slides.append({
        "slide": number,
        "image_url": jpeg_url,
        "is_carousel_item": True,
        "alt_text": ("MarketRevamp news slide: " + stories[number - 1]["title"])[:950]
    })
caption_lines = [
    "🚀 MARKETREVAMP | DAILY NEWS BRIEF",
    "",
    "Today's top 7 stories in AI, Technology, Crypto & Markets:",
    ""
]

for index, story in enumerate(stories, start=1):
    title = story.get("title", "").strip()
    url = story.get("url", "").strip()

    if not title or not url.startswith("https://"):
        raise ValueError(
            f"Story {index} is missing a valid title or URL."
        )

    source = urlsplit(url).hostname or "Unknown source"
    source = source.removeprefix("www.")

    caption_lines.append(f"{index}. {title}")
    caption_lines.append(f"Source: {source}")
    caption_lines.append("")

caption_lines.extend([
    "Follow @marketrevampdaily for daily updates.",
    "",
    "News and information only. Not investment advice."
])

# Keep hashtags in the visible description. An empty first comment
# prevents a second, failure-prone Instagram comments API request.
caption = compose_caption(caption_lines)
first_comment = ""

manifest = {
    "instagram_user_id_env": "INSTAGRAM_USER_ID",
    "publish_enabled": True,
    "automated_checks_passed": True,
    "editorial_approved": False,
    "media_type": "CAROUSEL",
    "caption": caption,
    "first_comment": first_comment,
    "article_urls": [
        story["url"] for story in stories
    ],
    "slides": slides
}


OUTPUT.write_text(
    json.dumps(manifest, indent=2),
    encoding="utf-8"
)

print("Carousel manifest prepared successfully.")
print("Images:", len(slides))
print("Publishing: manifest enabled; live publishing controlled by workflow")
print("Saved:", OUTPUT)
