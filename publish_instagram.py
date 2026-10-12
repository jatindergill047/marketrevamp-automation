
import json
import os
import sys
import time
import hashlib
import subprocess
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo

import requests
from urllib.parse import urlsplit, urlunsplit

API_VERSION = "v24.0"
API_BASE = f"https://graph.instagram.com/{API_VERSION}"

MANIFEST_FILE = Path("instagram_carousel_manifest.json")
HISTORY_FILE = Path("instagram_publish_history.json")

PUBLISH_ENABLED = (
    os.getenv("INSTAGRAM_PUBLISH_ENABLED", "false").lower() == "true"
)

def normalize_article_url(url):
    """Normalize article URLs for duplicate detection."""
    if not isinstance(url, str):
        raise ValueError("Invalid article URL.")

    parts = urlsplit(url.strip())

    if parts.scheme != "https" or not parts.hostname:
        raise ValueError("Invalid article URL.")

    return urlunsplit((
        "https",
        parts.netloc.lower(),
        parts.path.rstrip("/") or "/",
        "",
        ""
    ))

def load_history():
    if not HISTORY_FILE.exists():
        raise RuntimeError("Publishing history is missing.")

    history = json.loads(HISTORY_FILE.read_text(encoding="utf-8"))

    if not isinstance(history, dict):
        raise RuntimeError("Invalid publishing history.")

    return history



def save_history(history):
    history_checkout = Path("publishing-history")
    branch_file = history_checkout / HISTORY_FILE.name

    if not history_checkout.is_dir():
        raise RuntimeError(
            "Publishing history checkout is missing."
        )

    content = json.dumps(history, indent=2) + "\n"

    HISTORY_FILE.write_text(content, encoding="utf-8")
    branch_file.write_text(content, encoding="utf-8")

    def git(*args):
        subprocess.run(
            ["git", "-C", str(history_checkout), *args],
            check=True,
            timeout=60,
        )

    git("config", "user.name", "github-actions[bot]")
    git(
        "config",
        "user.email",
        "41898282+github-actions[bot]@users.noreply.github.com",
    )

    git("add", HISTORY_FILE.name)

    changes = subprocess.run(
        [
            "git", "-C", str(history_checkout),
            "diff", "--cached", "--quiet",
        ],
        check=False,
        timeout=60,
    )

    if changes.returncode == 0:
        return

    if changes.returncode != 1:
        raise RuntimeError("Could not inspect history changes.")

    git("commit", "-m", "Update Instagram publishing history")
    git("push", "origin", "HEAD:publishing-history")

    print("Publishing history saved to GitHub.")

def load_manifest():
    if not MANIFEST_FILE.exists():
        raise RuntimeError("Instagram carousel manifest is missing.")

    data = json.loads(MANIFEST_FILE.read_text(encoding="utf-8"))
    slides = data.get("slides", [])

    if len(slides) != 5:
        raise RuntimeError("Exactly five slides are required.")

    urls = []

    for slide in slides:
        url = slide.get("image_url") or slide.get("secure_url")

        if not url or not url.startswith("https://"):
            raise RuntimeError("Invalid image URL.")

        if "res.cloudinary.com/" not in url:
            raise RuntimeError("Image must be hosted on Cloudinary.")

        urls.append(url)

    if len(set(urls)) != 5:
        raise RuntimeError("Duplicate images detected.")

    return data, urls


def api_request(method, endpoint, token, payload=None):
    response = requests.request(
        method,
        f"{API_BASE}/{endpoint}",
        headers={"Authorization": f"Bearer {token}"},
        data=payload if method == "POST" else None,
        params=payload if method == "GET" else None,
        timeout=60,
    )

    try:
        result = response.json()
    except ValueError:
        raise RuntimeError(
            f"Instagram returned HTTP {response.status_code}"
        )

    if not response.ok or "error" in result:
        error = result.get("error", {})
        raise RuntimeError(
            f"Instagram API error: {error.get('message', 'Unknown error')}"
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

    raise RuntimeError("Timed out waiting for media processing.")


def main():
    manifest, image_urls = load_manifest()
    history = load_history()
    
    article_urls = manifest.get("article_urls", [])

    if len(article_urls) != 5:
        raise RuntimeError(
            "Exactly five article URLs are required."
        )

    normalized_urls = [
        normalize_article_url(url)
        for url in article_urls
    ]

    if len(set(normalized_urls)) != 5:
        raise RuntimeError(
            "Duplicate articles found in today's carousel."
        )

    previously_published = set()

    for record in history.values():
        if not isinstance(record, dict):
            raise RuntimeError("Invalid publishing history record.")

        if record.get("status") == "published":
            for url in record.get("article_urls", []):
                previously_published.add(
                    normalize_article_url(url)
                )

    repeated = set(normalized_urls) & previously_published

    if repeated:
        raise RuntimeError(
            f"Publishing blocked: {len(repeated)} "
            "previously published article(s) detected."
        )

    fingerprint = hashlib.sha256(
        json.dumps(image_urls, sort_keys=True).encode()
    ).hexdigest()

    print("Validated five unique Cloudinary image URLs.")

    if fingerprint in history:
        status = history[fingerprint].get("status")
        print(f"Existing publishing record: {status}")
        print("Skipping to prevent duplicate publishing.")
        return

    today = datetime.now(
        ZoneInfo("America/Toronto")
    ).date().isoformat()

    for record in history.values():
        if not isinstance(record, dict):
            raise RuntimeError("Invalid publishing history record.")

        if record.get("toronto_date") == today:
            if record.get("status") in ("pending", "published"):
                print(
                    "A publishing attempt already exists "
                    "for today. Skipping."
                )
                return

    if not PUBLISH_ENABLED:
        print("DRY RUN: Instagram publishing is disabled.")
        print("No Instagram API publishing requests were made.")
        return

    if manifest.get("publish_enabled") is not True:
        raise RuntimeError(
            "Live publishing blocked: carousel manifest is disabled."
        )

    if os.getenv("INSTAGRAM_PERSISTENCE_READY") != "true":
        raise RuntimeError(
            "Live publishing blocked: persistent history is not ready."
        )

    token = os.getenv("INSTAGRAM_ACCESS_TOKEN")
    account_id = os.getenv("INSTAGRAM_USER_ID")

    if not token or not account_id:
        raise RuntimeError("Instagram credentials are missing.")

    caption = manifest.get("caption", "").strip()

    if not caption:
        raise RuntimeError("Instagram caption is missing.")

    if manifest.get("editorial_approved") is not True:
        raise RuntimeError(
            "Publishing blocked: editorial approval is required."
        )

    if len(caption) > 2200:
        raise RuntimeError(
            "Instagram caption exceeds 2,200 characters."
        )

    if not any(
        word in caption.lower()
        for word in ("source:", "sources:", "via:")
    ):
        raise RuntimeError(
            "Instagram caption must include source attribution."
        )

    print("Caption safety checks passed.")

    history[fingerprint] = {
        "status": "pending",
        "toronto_date": today,
        "created_at": int(time.time()),
        "article_urls": normalized_urls,
        "image_urls": image_urls,
        "instagram_container_id": None,
    }
    save_history(history)

    print("Publishing attempt recorded as pending.")

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

    history[fingerprint]["instagram_container_id"] = carousel_id
    save_history(history)

    print(f"Instagram carousel container recorded: {carousel_id}")

    wait_for_container(carousel_id, token)

    published = api_request(
        "POST",
        f"{account_id}/media_publish",
        token,
        {"creation_id": carousel_id},
    )

    history[fingerprint].update({
        "status": "published",
        "toronto_date": today,
        "instagram_media_id": published["id"],
        "published_at": int(time.time()),
        "article_urls": normalized_urls,
    })
    save_history(history)

    print(f"Instagram carousel published: {published['id']}")


if __name__ == "__main__":
    try:
        
        main()
    except Exception as error:
        print(f"Publishing stopped: {error}", file=sys.stderr)
        sys.exit(1)
