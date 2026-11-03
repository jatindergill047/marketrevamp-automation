"""Optional Reel preparation. Never publishes to Instagram."""
import json
import os
from pathlib import Path

from reel_config import reel_enabled


def prepare():
    if not reel_enabled():
        print("Reels disabled; carousel unchanged.")
        return False
    from reel_script import build_all
    from reel_frames import compose
    from tts import speak
    from build_reel import build_reel
    from reel_cloudinary import upload_video

    stories = json.loads(Path("news_results.json").read_text(encoding="utf-8"))["selected_stories"]
    if len(stories) != 7:
        raise ValueError("Reel requires seven stories")
    if not all(isinstance(s, dict) and s.get("title") and s.get("summary") for s in stories):
        raise ValueError("Reel stories require title and summary")
    narrations = build_all([{"headline": s["title"], "summary": s["summary"]} for s in stories])
    root = Path("reel_output")
    root.mkdir(exist_ok=True)
    frames, audios = [], []
    for index, narration in enumerate(narrations, 1):
        frames.append(compose(Path("instagram_images") / f"slide_{index:02d}.png", index, root / f"frame_{index:02d}.png"))
        audios.append(speak(narration, root / f"voice_{index:02d}.mp3"))
    video = build_reel(frames, audios, narrations, root / "marketrevamp_reel.mp4", Path("reel_segments.json"))
    if os.environ.get("REEL_UPLOAD_ENABLED", "false").lower() != "true":
        print("Reel rendered locally; Cloudinary upload disabled.")
        return True
    upload = upload_video(
        video,
        os.environ["CLOUDINARY_CLOUD_NAME"],
        os.environ["CLOUDINARY_UPLOAD_PRESET"],
        os.environ.get("CLOUDINARY_API_KEY", ""),
        os.environ.get("CLOUDINARY_API_SECRET", ""),
    )
    Path("cloudinary_reel_upload.json").write_text(json.dumps(upload, indent=2) + "\n", encoding="utf-8")
    return True


if __name__ == "__main__":
    prepare()
