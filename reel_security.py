"""R8: validate and fingerprint opt-in Reel approval."""
import hashlib
import json
import math
from urllib.parse import urlsplit


def validated_reel(manifest):
    if manifest.get("media_kind") != "reel":
        raise ValueError("Expected reel media kind")
    reel = manifest.get("reel")
    if not isinstance(reel, dict):
        raise ValueError("Missing Reel block")
    video, cover = reel.get("video_url"), reel.get("cover_url")
    if not isinstance(video, str) or not isinstance(cover, str):
        raise ValueError("Missing Reel media URL")
    v, c = urlsplit(video), urlsplit(cover)
    if (v.scheme != "https" or v.netloc != "res.cloudinary.com"
            or "/video/upload/" not in v.path or not v.path.endswith(".mp4")
            or v.query or v.fragment):
        raise ValueError("Invalid Cloudinary Reel video")
    if (c.scheme != "https" or c.netloc != "res.cloudinary.com"
            or "/image/upload/" not in c.path or c.query or c.fragment):
        raise ValueError("Invalid Cloudinary Reel cover")
    if cover != (manifest.get("slides") or [{}])[0].get("image_url"):
        raise ValueError("Reel cover must match first slide")
    if reel.get("caption") != manifest.get("caption") or not isinstance(reel.get("caption"), str):
        raise ValueError("Reel caption mismatch")
    duration = reel.get("duration_seconds")
    if isinstance(duration, bool) or not isinstance(duration, (int, float)) or not math.isfinite(duration) or duration <= 0:
        raise ValueError("Invalid Reel duration")
    return {"video_url": video, "cover_url": cover, "duration_seconds": duration, "caption": reel["caption"]}


def reel_fingerprint(manifest, image_urls):
    from publish_instagram import approval_fingerprint
    reel = validated_reel(manifest)
    carousel_fp = approval_fingerprint({**manifest, "media_kind": "carousel"}, image_urls)
    content = {"media_kind": "reel", "carousel_fingerprint": carousel_fp, "reel": reel}
    canonical = json.dumps(content, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
