"""R49 controlled first-live Reel delivery. Explicit manual approval, never scheduled.

This module is NOT a daily publisher. It publishes one reviewed source package when
both publishing flags and an exact fingerprint approval are present.
"""
import os
import time
from pathlib import Path

from publish_instagram import api_request, normalize_article_url, wait_for_container
from reel_cloudinary import upload_video
from reel_r46_launch_gate import ReleaseBlocked, authorize_publication, validate_and_fingerprint


def _require(test, reason):
    if not test:
        raise ReleaseBlocked(reason)


def _check_article_reuse(stories, history):
    """Reject recycled news articles from published Reels *or* carousels."""
    current = {normalize_article_url(s["source_url"]) for s in stories}
    _require(len(current) == 7, "Reel sources must be unique after canonicalization")
    for record in history.values():
        _require(isinstance(record, dict), "Malformed publishing history")
        if record.get("status") != "published":
            continue
        previous = {normalize_article_url(u) for u in record.get("article_urls", [])}
        if current & previous:
            raise ReleaseBlocked("Previously published article found in Reel script")


def publish_once(metadata, stories, video_path, history, *, approved_fingerprint,
                 cloud, preset, account_id, token, api_key="", api_secret="",
                 uploader=upload_video, request=api_request, saver=None,
                 now=None, sleep=time.sleep):
    """Only execute irreversible Instagram calls after gated QA + durable checkpoints."""
    release = validate_and_fingerprint(metadata, stories, video_path, now=now)
    _require(os.environ.get("REEL_FIRST_LIVE_ENABLED", "false") == "true",
             "First-live Reel flag not enabled")
    _require(os.environ.get("INSTAGRAM_PUBLISH_ENABLED", "false") == "true",
             "Instagram publishing not enabled for this manual run")
    _require(os.environ.get("REEL_UPLOAD_ENABLED", "false") == "true",
             "Cloudinary Reel upload not enabled for this manual run")
    _require(callable(saver), "Durable publishing history writer is required")
    _require(account_id and str(account_id).isdigit() and bool(token),
             "Instagram credentials unavailable")
    _require(bool(cloud) and bool(preset) and bool(api_key) and bool(api_secret),
             "Signed Cloudinary upload credentials required")
    authorize_publication(release, approved_fingerprint, history, now=now)
    _check_article_reuse(stories, history)

    # Cloudinary upload is non-Instagram. Do not create IG containers until
    # a public HTTPS video URL is verified.
    uploaded = uploader(Path(video_path), cloud, preset, api_key, api_secret)
    _require(isinstance(uploaded, dict), "Cloudinary upload returned invalid data")
    video_url = uploaded.get("secure_url", "")
    from urllib.parse import urlsplit
    parts = urlsplit(video_url)
    _require(parts.scheme == "https" and parts.hostname == "res.cloudinary.com"
             and parts.path.startswith("/" + cloud + "/video/upload/")
             and parts.path.lower().endswith(".mp4")
             and not parts.query and not parts.fragment,
             "Cloudinary URL is not a valid public MP4")

    fp = release["release_fingerprint"]
    from datetime import datetime
    from zoneinfo import ZoneInfo
    today = (now or datetime.now(ZoneInfo("America/Toronto"))).astimezone(
        ZoneInfo("America/Toronto")).date().isoformat()

    record = {
        "media_kind": "reel", "status": "pending", "toronto_date": today,
        "created_at": int(time.time()), "release_fingerprint": fp,
        "video_sha256": release["video_sha256"],
        "article_urls": release["source_urls"], "video_url": video_url,
        "instagram_container_id": None, "instagram_media_id": None,
    }
    history[fp] = record
    saver(history)  # Durable checkpoint before any Instagram operation.

    # If a request fails after the container call, keep status pending.
    # Never automatically retry an uncertain Instagram outcome.
    created = request("POST", f"{account_id}/media", token, {
        "media_type": "REELS", "video_url": video_url,
        "caption": release["caption"], "share_to_feed": "true"
    })
    container_id = str(created.get("id", ""))
    _require(container_id.isdigit(), "Instagram did not provide a Reel container ID")
    record["instagram_container_id"] = container_id
    saver(history)

    for attempt in range(24):
        state = request("GET", container_id, token, {"fields": "status_code"})
        status = state.get("status_code")
        if status == "FINISHED":
            break
        if status in ("ERROR", "EXPIRED") or status != "IN_PROGRESS":
            raise RuntimeError(f"Instagram Reel processing blocked: {status}")
        if attempt < 23:
            sleep(10)
    else:
        raise RuntimeError("Instagram Reel processing timed out; inspect pending record")

    # Critical irreversible boundary. Failure after this checkpoint is UNKNOWN,
    # even if the API responds with an error or times out.
    record["publish_attempted_at"] = int(time.time())
    saver(history)
    result = request("POST", f"{account_id}/media_publish", token,
                     {"creation_id": container_id})
    media_id = str(result.get("id", ""))
    _require(media_id.isdigit(), "Instagram publication result ambiguous; reconcile first")
    record.update({"status": "published", "instagram_media_id": media_id,
                   "published_at": int(time.time())})
    saver(history)
    return {"instagram_media_id": media_id, "release_fingerprint": fp,
            "cloudinary_url": video_url, "status": "published"}
