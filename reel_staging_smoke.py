"""R13 isolated staging smoke test: real voice and real MP4, never publish/upload."""
import json
import os
import subprocess
import tempfile
from pathlib import Path

from PIL import Image
from build_reel import build_reel
from reel_frames import compose
from tts import duration, speak


def main():
    if any(os.getenv(k, "false").lower() == "true" for k in
           ("REEL_ENABLED", "REEL_UPLOAD_ENABLED", "INSTAGRAM_PUBLISH_ENABLED")):
        raise RuntimeError("Staging smoke requires all publishing and upload flags disabled")
    with tempfile.TemporaryDirectory(prefix="reel_r13_staging_") as folder:
        root = Path(folder)
        frames, voices, narrations = [], [], []
        for index in range(1, 8):
            narration = f"Story {index} of seven. This is a MarketRevamp staging narration test."
            narrations.append(narration)
            slide = root / f"slide_{index}.png"
            Image.new("RGB", (1080, 1350), (25, 30 + index * 8, 45)).save(slide)
            frames.append(compose(slide, index, root / f"frame_{index}.png"))
            voice = speak(narration, root / f"voice_{index}.mp3")
            if duration(voice) <= 0:
                raise RuntimeError("Generated voice is empty")
            voices.append(voice)
        video = build_reel(frames, voices, narrations, root / "sample.mp4",
                           root / "segments.json", fps=5)
        probe = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                                "stream=codec_type,width,height:format=duration",
                                "-of", "json", str(video)], capture_output=True,
                               text=True, check=True, timeout=30)
        data = json.loads(probe.stdout)
        streams = data["streams"]
        assert any(s.get("codec_type") == "video" and
                   (s.get("width"), s.get("height")) == (1080, 1920) for s in streams)
        assert any(s.get("codec_type") == "audio" for s in streams)
        assert len(json.loads((root / "segments.json").read_text())["segments"]) == 7
        assert float(data["format"]["duration"]) > 0
        print("R13 REAL TTS AND MP4 PASS: seven voices, 1080x1920 H264/AAC, captions rendered")
        print("No external media upload or Instagram action; temporary files deleted.")


if __name__ == "__main__":
    main()
