
import json
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

SOURCE = Path("cloudinary_uploads.json")
OUTPUT = Path("instagram_carousel_manifest.json")
NEWS_SOURCE = Path("news_results.json")

data = json.loads(SOURCE.read_text(encoding="utf-8"))
images = data["images"]

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

manifest = {
    "instagram_user_id_env": "INSTAGRAM_USER_ID",
    "publish_enabled": False,
    "media_type": "CAROUSEL",
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
