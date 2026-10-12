
import json
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

SOURCE = Path("cloudinary_uploads.json")
OUTPUT = Path("instagram_carousel_manifest.json")
NEWS_SOURCE = Path("news_results.json")

data = json.loads(SOURCE.read_text(encoding="utf-8"))
images = data["images"]
news_data = json.loads(
    NEWS_SOURCE.read_text(encoding="utf-8")
)

stories = news_data.get("selected_stories", [])

if len(stories) != 5:
    raise ValueError(
        f"Expected 5 news stories, found {len(stories)}"
    )

for index, story in enumerate(stories, start=1):
    if story.get("summary_status") != "ready_for_review":
        raise ValueError(
            f"Story {index} failed summary quality screening."
        )

if len(images) != 5:
    raise ValueError(f"Expected 5 images, found {len(images)}")

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
        "is_carousel_item": True
    })
from urllib.parse import urlsplit

caption_lines = [
    "🚀 MARKETREVAMP | DAILY NEWS BRIEF",
    "",
    "Today's top 5 stories in AI, Technology, Crypto & Markets:",
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
    "#MarketRevamp #AI #Technology #Crypto #Bitcoin #StockMarket",
    "",
    "News and information only. Not investment advice."
])

caption = "\n".join(caption_lines)

if len(caption) > 2200:
    raise ValueError(
        "Instagram caption exceeds 2,200 characters."
    )
manifest = {
    "instagram_user_id_env": "INSTAGRAM_USER_ID",
    "publish_enabled": False,
    "editorial_approved": False,
    "media_type": "CAROUSEL",
    "caption": caption,
    "slides": slides
}

OUTPUT.write_text(
    json.dumps(manifest, indent=2),
    encoding="utf-8"
)

print("Carousel manifest prepared successfully.")
print("Images:", len(slides))
print("Publishing: DISABLED")
print("Saved:", OUTPUT)
