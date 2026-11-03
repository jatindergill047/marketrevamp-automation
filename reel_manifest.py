"""Validate optional Reel upload and timing metadata without touching carousel."""
import json
import math
from pathlib import Path
from urllib.parse import urlsplit


def load_reel_metadata(upload_path, segments_path=Path("reel_segments.json")):
    """Return validated Reel details, or None when no upload is available."""
    upload_path = Path(upload_path)
    if not upload_path.is_file():
        return None
    data = json.loads(upload_path.read_text(encoding="utf-8"))
    url = data.get("secure_url", "")
    parts = urlsplit(url)
    if (
        parts.scheme != "https"
        or parts.hostname != "res.cloudinary.com"
        or "/video/upload/" not in parts.path
        or not parts.path.lower().endswith(".mp4")
    ):
        raise ValueError("Invalid Cloudinary Reel video URL")
    if data.get("resource_type") != "video":
        raise ValueError("Cloudinary upload is not a video")
    timings = json.loads(Path(segments_path).read_text(encoding="utf-8"))
    seconds = float(timings["duration_seconds"])
    if not math.isfinite(seconds) or seconds <= 0:
        raise ValueError("Reel duration must be positive and finite")
    if len(timings.get("segments", [])) != 7:
        raise ValueError("Reel requires seven segments")
    return {"video_url": url, "duration_seconds": seconds}
