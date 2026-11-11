"""Resilient text-to-speech for opt-in MarketRevamp Reels."""

import asyncio
import json
import shutil
import subprocess
import time
from pathlib import Path

from reel_config import VOICE

# Conservative prosody tuning for a conversational news-presenter delivery.
# These are TTS controls, not a guarantee of human-sounding speech.
VOICE_RATE = "-5%"
VOICE_PITCH = "-2Hz"

# Preview-only candidates: compare actual generated audio before selecting a voice.
VOICE_CANDIDATES = {
    "ava": "en-US-AvaNeural",
    "andrew": "en-US-AndrewNeural",
    "jenny": "en-US-JennyNeural",
}


class ReelBuildError(RuntimeError):
    """An optional Reel audio build step failed."""


def available() -> bool:
    """Return whether ffprobe is installed and executable."""
    return shutil.which("ffprobe") is not None


def speak(text: str, out_path: str | Path, *, voice: str | None = None, rate: str | None = None, pitch: str | None = None) -> Path:
    """Generate MP3 narration with three attempts, raising on failure."""
    if not isinstance(text, str) or not text.strip():
        raise ReelBuildError("Cannot synthesize empty narration")
    try:
        import edge_tts
    except ImportError as exc:
        raise ReelBuildError("edge-tts is not installed") from exc

    destination = Path(out_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    last_error = None
    for attempt in range(3):
        try:
            destination.unlink(missing_ok=True)
            asyncio.run(edge_tts.Communicate(text, voice or VOICE, rate=rate or VOICE_RATE, pitch=pitch or VOICE_PITCH).save(str(destination)))
            if not destination.is_file() or destination.stat().st_size == 0:
                raise ReelBuildError("TTS produced no audio")
            return destination
        except Exception as exc:
            last_error = exc
            destination.unlink(missing_ok=True)
            if attempt < 2:
                time.sleep(2**attempt)
    raise ReelBuildError("TTS failed after 3 attempts") from last_error


def duration(path: str | Path) -> float:
    """Read a positive audio duration using ffprobe."""
    if not available():
        raise ReelBuildError("ffprobe is unavailable")
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "json", str(Path(path))],
            capture_output=True,
            text=True,
            check=True,
            timeout=30,
        )
        value = float(json.loads(result.stdout)["format"]["duration"])
        if not 0 < value < float("inf"):
            raise ValueError("Duration must be finite and positive")
        return value
    except (OSError, subprocess.SubprocessError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        raise ReelBuildError("Could not determine audio duration") from exc


def speak_with_boundaries(text, out_path, boundaries_path):
    """Synthesize once and save service-provided WordBoundary offsets in seconds."""
    if not isinstance(text, str) or not text.strip():
        raise ReelBuildError("Cannot synthesize empty narration")
    try:
        import edge_tts
    except ImportError as exc:
        raise ReelBuildError("edge-tts is not installed") from exc
    destination, timing = Path(out_path), Path(boundaries_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    timing.parent.mkdir(parents=True, exist_ok=True)

    async def generate():
        events = []
        with destination.open("wb") as audio:
            communicator = edge_tts.Communicate(text, VOICE, rate=VOICE_RATE,
                                                 pitch=VOICE_PITCH, boundary="WordBoundary")
            async for chunk in communicator.stream():
                if chunk["type"] == "audio":
                    audio.write(chunk["data"])
                elif chunk["type"] == "WordBoundary":
                    events.append({"text": chunk["text"],
                                   "start_seconds": chunk["offset"] / 10000000,
                                   "duration_seconds": chunk["duration"] / 10000000})
        return events

    try:
        events = asyncio.run(generate())
        if not events or not destination.is_file() or destination.stat().st_size == 0:
            raise ReelBuildError("TTS returned no word boundaries or audio")
        timing.write_text(json.dumps(events, indent=2) + "\n", encoding="utf-8")
        return destination, timing
    except Exception as exc:
        destination.unlink(missing_ok=True)
        timing.unlink(missing_ok=True)
        raise ReelBuildError("R24 timed TTS synthesis failed") from exc
