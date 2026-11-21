"""R84 controlled first or recurring Reel delivery, never self-authorizing.

Never invoke this from a news collector. GitHub production release workflow
must first validate the source run, exact artifact and owner-approved gate.
No Cloudinary or Instagram calls occur in prepare_only mode.
"""
import argparse
import hashlib
import json
import os
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo

from publish_instagram import api_request, load_history, save_history
from reel_daily_release_policy import release_decision
from reel_r49_first_live import publish_once

TORONTO = ZoneInfo("America/Toronto")
ROOT = Path("r84_release")
REVIEW = Path("r72_review")


def read_json(path):
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError(f"Invalid release data file {path}")
    return value


def exact_media(video):
    payload = video.read_bytes()
    if len(payload) < 1024:
        raise RuntimeError("Missing Reel MP4")
    return hashlib.sha256(payload).hexdigest()


def release_data(*, mode, activation, history, expected_sha=""):
    """Recheck the owner-authorized safety policy every time."""
    if mode not in {"first", "daily"}:
        raise ValueError("Unsupported release mode")
    qa = read_json(REVIEW / "r72_qa.json")
    pending = read_json(REVIEW / "editorial_pending_stories.json")
    sources = read_json("r67_review/review_sources.json")
    video = REVIEW / "marketrevamp-r72-real-news-review-only.mp4"
    if not video.is_file():
        raise RuntimeError("R72 real news video artifact missing")
    if mode == "first" and expected_sha != exact_media(video):
        raise RuntimeError("First Reel approved video hash does not match")
    # This never trusts flags carried by the review artifact as publication
    # approval; only this dedicated production policy may promote content.
    return release_decision(qa, pending, sources, video, history,
                            activation=activation, first_live=(mode == "first"),
                            approved_video_sha256=expected_sha,
                            now=datetime.now(TORONTO))


def prepare(*, mode, expected_sha=""):
    """Offline gated publication package; no public upload."""
    activation = read_json("r83_reel_autopublish_state.json")
    release = release_data(mode=mode, activation=activation,
                           history=load_history(), expected_sha=expected_sha)
    ROOT.mkdir(parents=True, exist_ok=True)
    (ROOT / "release_metadata.json").write_text(
        json.dumps(release["metadata"], indent=2, ensure_ascii=False)+"\n")
    (ROOT / "release_stories.json").write_text(
        json.dumps(release["stories"], indent=2, ensure_ascii=False)+"\n")
    (ROOT / "release_gate.json").write_text(
        json.dumps({k: v for k, v in release.items()
                    if k not in ("metadata", "stories")}, indent=2)+"\n")
    print("R84 EXACT RELEASE POLICY READY", mode,
          release["video_sha256"], release["fingerprint"])
    return release


def delivery(*, mode, expected_sha="",
             request=api_request, upload_and_publish=publish_once,
             save=save_history):
    """Publish once and verify Instagram readback before unlocking future Reels."""
    release = release_data(mode=mode,
                           activation=read_json("r83_reel_autopublish_state.json"),
                           history=load_history(), expected_sha=expected_sha)
    prepared = read_json(ROOT / "release_gate.json")
    if (prepared.get("video_sha256") != release["video_sha256"] or
            prepared.get("fingerprint") != release["fingerprint"] or
            prepared.get("first_live") != release["first_live"]):
        raise RuntimeError("Prepared exact release fingerprint changed")
    cloud = os.environ.get("CLOUDINARY_CLOUD_NAME", "")
    preset = os.environ.get("CLOUDINARY_REEL_UPLOAD_PRESET") or os.environ.get(
        "CLOUDINARY_UPLOAD_PRESET", ""
    )
    user_id = os.environ.get("INSTAGRAM_USER_ID", "")
    token = os.environ.get("INSTAGRAM_ACCESS_TOKEN", "")
    published = upload_and_publish(
        release["metadata"], release["stories"],
        REVIEW / "marketrevamp-r72-real-news-review-only.mp4",
        load_history(), approved_fingerprint=release["fingerprint"],
        cloud=cloud, preset=preset, account_id=user_id, token=token,
        api_key=os.environ.get("CLOUDINARY_API_KEY", ""),
        api_secret=os.environ.get("CLOUDINARY_API_SECRET", ""),
        saver=save,
    )
    media_id = str(published.get("instagram_media_id", ""))
    if not media_id.isdigit() or published.get("status") != "published":
        raise RuntimeError("Instagram publication not confirmed")
    # One explicit readback: never trigger a new Instagram upload on ambiguous
    # GET failures; the published history entry must remain for reconciliation.
    verified = request("GET", media_id, token,
                       {"fields": "id,media_type,permalink"})
    url = str(verified.get("permalink", ""))
    parts = urlsplit(url)
    if (str(verified.get("id", "")) != media_id or
            str(verified.get("media_type", "")).upper() != "VIDEO" or
            parts.scheme != "https" or
            parts.hostname not in {"www.instagram.com", "instagram.com"}):
        raise RuntimeError("Instagram media readback unverified; do not re-publish")
    # Mark the verified R72 media in the authoritative history. The previous
    # published checkpoint remains recorded even if this final save fails.
    history = load_history()
    fingerprint = release["fingerprint"]
    record = history.get(fingerprint)
    if not isinstance(record, dict) or record.get("status") != "published" or \
            str(record.get("instagram_media_id")) != media_id:
        raise RuntimeError("Published Reel history record could not be reconciled")
    record.update({
        "template_version": "R72",
        "release_mode": mode,
        "instagram_readback_verified": True,
        "instagram_permalink": url,
        "instagram_verified_at": int(time.time()),
    })
    save(history)
    ROOT.mkdir(parents=True, exist_ok=True)
    result = {"status": "published", "template_version": "R72",
              "release_mode": mode,
              "instagram_media_id": media_id, "instagram_permalink": url,
              "release_fingerprint": fingerprint,
              "video_sha256": release["video_sha256"],
              "instagram_readback_verified": True}
    (ROOT / "publication_result.json").write_text(
        json.dumps(result, indent=2)+"\n", encoding="utf-8")
    print("R84 VERIFIED INSTAGRAM R72 REEL", media_id, url)
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description="R84 exact-review Reel publication gate")
    parser.add_argument("--mode", required=True, choices=("first", "daily"))
    parser.add_argument("--action", required=True, choices=("prepare", "publish"))
    parser.add_argument("--approved-sha256", default="")
    args = parser.parse_args(argv)
    if args.action == "prepare":
        prepare(mode=args.mode, expected_sha=args.approved_sha256)
    else:
        delivery(mode=args.mode, expected_sha=args.approved_sha256)


if __name__ == "__main__":
    main()
