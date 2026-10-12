
import json
import os
import sys
import time
import hashlib
from pathlib import Path

import requests

API_VERSION = "v24.0"
API_BASE = f"https://graph.instagram.com/{API_VERSION}"

MANIFEST_FILE = Path("instagram_carousel_manifest.json")
HISTORY_FILE = Path("instagram_publish_history.json")

PUBLISH_ENABLED = os.getenv(
    "INSTAGRAM_PUBLISH_ENABLED", "false"
).lower() == "true"


def load_manifest():
    if not MANIFEST_FILE.exists():
        raise RuntimeError("Instagram carousel manifest is missing.")

    data = json.loads(MANIFEST_FILE.read_text(encoding="utf-8"))
    slides = data.get("slides", [])

    if len(slides) != 5:
        raise RuntimeError("Exactly five carousel slides are required.")

    urls = []

    for slide in slides:
        url = slide.get("image_url") or slide.get("secure_url")

        if not url or not url.startswith("https://"):
            raise RuntimeError("Invalid carousel image URL.")

        if "res.cloudinary.com/" not in url:
            raise RuntimeError("Image must be hosted on Cloudinary.")

        urls.append(url)

    if len(set(urls)) != 5:
        raise RuntimeError("Duplicate carousel images detected.")

    return data, urls


def api_request(method, endpoint, token, payload=None):
    url = f"{API_BASE}/{endpoint}"

    response = requests.request(
        method,
        url,
        headers={"Authorization": f"Bearer {token}"},
        data=payload if method == "POST" else None,
        params=payload if method == "GET" else None,
        timeout=60,
    )

    try:
        result = response.json()
    except ValueError:
        raise RuntimeError(
            f"Instagram API returned HTTP {response.status_code}"
        )

    if not response.ok or "error" in result:
        error = result.get("error", {})
        raise RuntimeError(
            f"Instagram API error: "
            f"{error.get('message', 'Unknown error')}"
        )

    return result


def wait_for_container(container_id, token):
    for _ in range(20):
        result = api_request(
            "GET",
            container_id,
            token,
            {"fields": "status_code"},
        )

        status = result.get("status_code")

        if status == "FINISHED":
            return

        if status in ("ERROR", "EXPIRED"):
            raise RuntimeError(f"Media processing failed: {status}")

        time.sleep(15)

    raise RuntimeError("Timed out waiting for Instagram media processing.")


def main():
    manifest, image_urls = load_manifest()

    fingerprint = hashlib.sha256(
        json.dumps(image_urls, sort_keys=True).encode()
    ).hexdigest()

    print("Validated five unique Cloudinary image URLs.")

    if not PUBLISH_ENABLED:
        print("DRY RUN: Instagram publishing is disabled.")
        print("No Instagram API publishing requests were made.")
        return

    token = os.getenv("INSTAGRAM_ACCESS_TOKEN")
    account_id = os.getenv("INSTAGRAM_USER_ID")

    if not token or not account_id:
        raise RuntimeError("Instagram credentials are missing.")

    if HISTORY_FILE.exists():
        history = json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
        if fingerprint in history:
            print("Duplicate carousel detected. Skipping.")
            return

    caption = manifest.get("caption", "").strip()

    if not caption:
        raise RuntimeError("Instagram caption is missing.")

    child_ids = []

    for index, image_url in enumerate(image_urls, start=1):
        result = api_request(
            "POST",
            f"{account_id}/media",
            token,
            {
                "image_url": image_url,
                "is_carousel_item": "true",
            },
        )

        child_ids.append(result["id"])
        print(f"Created carousel item {index}/5.")

    result = api_request(
        "POST",
        f"{account_id}/media",
        token,
        {
            "media_type": "CAROUSEL",
            "children": ",".join(child_ids),
            "caption": caption,
        },
    )

    carousel_id = result["id"]
    wait_for_container(carousel_id, token)

    # This is the only operation that publishes the post.
    published = api_request(
        "POST",
        f"{account_id}/media_publish",
        token,
        {"creation_id": carousel_id},
    )

    print(f"Instagram carousel published: {published['id']}")

    history = {}
    if HISTORY_FILE.exists():
        history = json.loads(HISTORY_FILE.read_text(encoding="utf-8"))

    history[fingerprint] = {
        "instagram_media_id": published["id"],
        "published_at": int(time.time()),
    }

    HISTORY_FILE.write_text(
        json.dumps(history, indent=2),
        encoding="utf-8",
    )


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"Publishing stopped: {error}", file=sys.stderr)
        sys.exit(1)
