"""R15 local artifact-only comparison of natural-news voice candidates."""
import json
import os
from pathlib import Path

from reel_script import build_narration
from tts import VOICE_CANDIDATES, duration, speak

SAMPLES = [
    {"headline": "AI research", "summary": "Researchers are testing a new way to measure how reliably AI systems solve difficult problems. The early findings are promising, but independent verification is still needed."},
    {"headline": "Semiconductors", "summary": "A chip designer is exploring more efficient processors. The big question is whether the approach can deliver meaningful savings at scale."},
]

def main():
    if any(os.getenv(key, "false").lower() == "true" for key in
           ("REEL_ENABLED", "REEL_UPLOAD_ENABLED", "INSTAGRAM_PUBLISH_ENABLED")):
        raise RuntimeError("Voice comparison requires all publish and upload flags disabled")
    out = Path("r15_voice_comparison")
    out.mkdir(exist_ok=True)
    results = []
    for label, voice in VOICE_CANDIDATES.items():
        for i, story in enumerate(SAMPLES, 1):
            narration = build_narration(story, i, len(SAMPLES))
            path = out / f"{label}_story_{i}.mp3"
            speak(narration, path, voice=voice)
            seconds = duration(path)
            results.append({"candidate": label, "voice": voice, "story": i,
                            "file": path.name, "duration_seconds": round(seconds, 3),
                            "narration": narration})
    (out / "comparison.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    (out / "LISTENING_GUIDE.md").write_text(
        "# R15 Voice Listening Review\n\n"
        "Compare all three voices on the same two sample stories.\n\n"
        "Score: human-like delivery, phrase stress, pronunciation, natural pauses, "
        "consistent volume, and fit for MarketRevamp.\n\n"
        "Do not choose a winner from duration or technical validation alone.\n"
        "These are editorial demo stories, not real-world news claims.\n"
        "No Cloudinary upload or Instagram publishing.\n", encoding="utf-8")
    assert len(results) == 6 and all(x["duration_seconds"] > 0 for x in results)
    print("R15 PASS: six voice comparison MP3s generated locally; no uploads or publishing")

if __name__ == "__main__":
    main()
