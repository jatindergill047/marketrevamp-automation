"""R47 staging-only Instagram Reel-container processing check. NEVER calls media_publish."""
import json
import os
import time
from pathlib import Path
from urllib.parse import urlsplit

from publish_instagram import api_request

ALLOWED_CLOUDINARY_PREFIX = "/video/upload/"

def validate_staging(video_url, account_id, token):
    for key in ("REEL_ENABLED", "REEL_UPLOAD_ENABLED", "INSTAGRAM_PUBLISH_ENABLED"):
        if os.environ.get(key, "false").lower() == "true":
            raise RuntimeError(f"R47 staging forbids enabled {key}")
    url = urlsplit(video_url)
    if url.scheme != "https" or url.hostname != "res.cloudinary.com" or \
            ALLOWED_CLOUDINARY_PREFIX not in url.path or not url.path.lower().endswith(".mp4") or \
            url.query or url.fragment:
        raise ValueError("Expected an HTTPS Cloudinary staging MP4 URL")
    if not account_id or not account_id.isdigit() or not token:
        raise ValueError("Missing Instagram staging connection")
    return video_url

def inspect_container(video_url, account_id, token, request=api_request, pause=time.sleep,
                      max_polls=15):
    validate_staging(video_url, account_id, token)
    container = request("POST", f"{account_id}/media", token, {
        "media_type": "REELS", "video_url": video_url,
        "caption": "MARKETREVAMP NONPUBLIC STAGING CONTAINER - NOT FOR PUBLICATION",
        "share_to_feed": "false",
    })
    container_id = str(container.get("id", ""))
    if not container_id.isdigit():
        raise RuntimeError("Instagram did not return a valid Reel container ID")
    for attempt in range(max_polls):
        result = request("GET", container_id, token, {"fields": "status_code"})
        status = result.get("status_code")
        if status == "FINISHED":
            return {"container_id": container_id, "status": status,
                    "instagram_published": False}
        if status in ("ERROR", "EXPIRED"):
            raise RuntimeError(f"Instagram staging Reel processing failed: {status}")
        if status not in ("IN_PROGRESS", "PUBLISHED"):
            # Refuse unknown future statuses rather than silently proceeding.
            raise RuntimeError(f"Unexpected Instagram container status: {status!r}")
        if attempt < max_polls - 1:
            pause(10)
    raise RuntimeError("Instagram Reel staging container did not finish before timeout")

def main():
    url = os.environ["REEL_STAGING_PUBLIC_URL"]
    account = os.environ["INSTAGRAM_USER_ID"]
    token = os.environ["INSTAGRAM_ACCESS_TOKEN"]
    result = inspect_container(url, account, token)
    Path("reel_r47_container_result.json").write_text(
        json.dumps(result, indent=2) + "\n", encoding="utf-8"
    )
    print(f"INSTAGRAM_REEL_CONTAINER_READY: {result['container_id']}")
    print("No media_publish request was made. No Instagram post was created.")

if __name__ == "__main__":
    main()
