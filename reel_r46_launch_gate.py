"""R46 fail-closed Reel release gate. Pure validation; never uploads or publishes."""
import hashlib
import json
import re
import subprocess
from datetime import datetime
from pathlib import Path
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo

TORONTO = ZoneInfo("America/Toronto")
ACCEPTED_FACT_CHECK = {"source_supported", "independently_corroborated", "reviewed_allegation"}

class ReleaseBlocked(ValueError):
    pass

def _require(condition, message):
    if not condition:
        raise ReleaseBlocked(message)

def video_info(video):
    path = Path(video)
    _require(path.is_file() and path.suffix.lower() == ".mp4" and path.stat().st_size > 1024, "Missing valid MP4")
    try:
        raw = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries",
             "stream=codec_type,codec_name,width,height:format=duration",
             "-of", "json", str(path)],
            capture_output=True, text=True, check=True, timeout=30
        )
        data = json.loads(raw.stdout)
        streams = data.get("streams", [])
        seconds = float(data.get("format", {}).get("duration", 0))
    except (OSError, subprocess.SubprocessError, ValueError, TypeError, KeyError) as exc:
        raise ReleaseBlocked("MP4 probe failed") from exc
    _require(45 <= seconds <= 90, "Reel duration must be 45 to 90 seconds")
    _require(any(s.get("codec_type") == "video" and s.get("codec_name") == "h264"
                 and (s.get("width"), s.get("height")) == (1080, 1920) for s in streams),
             "Reel must contain 1080x1920 H.264 video")
    _require(any(s.get("codec_type") == "audio" and s.get("codec_name") == "aac" for s in streams),
             "Reel must contain AAC narration")
    return {"duration_seconds": round(seconds, 3), "width": 1080, "height": 1920}

def validate_and_fingerprint(metadata, stories, video, now=None):
    """Approve only today's independently editorial-approved, technically sound package."""
    _require(isinstance(metadata, dict), "Missing release metadata")
    _require(isinstance(stories, list) and len(stories) == 7, "Exactly seven stories required")
    today = (now or datetime.now(TORONTO)).astimezone(TORONTO).date().isoformat()
    _require(metadata.get("toronto_date") == today, "News package is stale or future-dated")
    _require(metadata.get("editorial_approved") is True, "Editorial approval missing")
    _require(metadata.get("visual_qa_approved") is True, "Visual QA missing")
    _require(metadata.get("audio_qa_approved") is True, "Audio QA missing")
    _require(metadata.get("official_logo_verified") is True, "Official logo not verified")
    _require(metadata.get("word_timing_origin") == "tts_word_boundaries", "Measured TTS word boundaries required")
    _require(metadata.get("voice") == "en-US-AndrewNeural", "Unreviewed voice change")
    reviewer = metadata.get("reviewed_by")
    _require(isinstance(reviewer, str) and bool(reviewer.strip()), "Missing human reviewer")
    caption = metadata.get("caption")
    _require(isinstance(caption, str) and 1 <= len(caption) <= 2200, "Invalid Instagram caption")
    _require("source" in caption.lower(), "Caption must attribute sources")
    links = []
    for index, story in enumerate(stories, 1):
        _require(isinstance(story, dict) and story.get("editorial_approved") is True,
                 f"Story {index} lacks approval")
        _require(story.get("fact_check_status") in ACCEPTED_FACT_CHECK,
                 f"Story {index} has unsupported fact-check status")
        for field in ("headline", "narration_text", "source_url"):
            _require(isinstance(story.get(field), str) and bool(story[field].strip()),
                     f"Story {index} is missing {field}")
        url = urlsplit(story["source_url"])
        _require(url.scheme == "https" and bool(url.hostname) and
                 not url.username and not url.password and "." in url.hostname,
                 f"Story {index} has an invalid source URL")
        links.append(story["source_url"])
    _require(len(set(links)) == 7, "Duplicate article sources")
    details = video_info(video)
    digest = hashlib.sha256(Path(video).read_bytes()).hexdigest()
    payload = {"media_kind": "reel", "toronto_date": today,
               "reviewed_by": reviewer.strip(), "video_sha256": digest,
               "video": details, "caption": caption, "source_urls": links,
               "voice": metadata["voice"], "word_timing_origin": "tts_word_boundaries",
               "editorial_approved": True, "visual_qa_approved": True,
               "audio_qa_approved": True, "official_logo_verified": True}
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    payload["release_fingerprint"] = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return payload

def authorize_publication(release, approved_fingerprint, history, now=None):
    """No network calls. Match exact fingerprint and reject duplicate/uncertain attempts."""
    today = (now or datetime.now(TORONTO)).astimezone(TORONTO).date().isoformat()
    _require(release.get("media_kind") == "reel" and release.get("toronto_date") == today,
             "Reel release is stale or invalid")
    fp = release.get("release_fingerprint", "")
    _require(isinstance(fp, str) and re.fullmatch(r"[a-f0-9]{64}", fp), "Bad fingerprint")
    _require(approved_fingerprint == fp, "Exact video fingerprint approval missing")
    _require(isinstance(history, dict), "Publishing history unavailable")
    for key, record in history.items():
        if not isinstance(record, dict):
            raise ReleaseBlocked("Malformed publishing history")
        if key == fp:
            raise ReleaseBlocked("This exact Reel was already attempted")
        if record.get("media_kind") == "reel" and record.get("toronto_date") == today and \
                record.get("status") in ("pending", "published", "unknown"):
            raise ReleaseBlocked("Reel publication already pending or completed for today")
    return True
