"""R25 reviewed real-news preview; explicit approval, no upload or publication."""
import json
import os
from pathlib import Path

from build_reel import build_continuous_reel
from reel_frames import compose
from reel_r25_editorial import build_review_package, validate_stories
from reel_script import build_connected_all, connected_script
from tts import speak_with_boundaries


def render_reviewed_preview(input_path="news_results.json", image_dir="instagram_images",
                            output_dir="r25_review"):
    if any(os.getenv(key, "false").lower() == "true" for key in
           ("REEL_ENABLED", "REEL_UPLOAD_ENABLED", "INSTAGRAM_PUBLISH_ENABLED")):
        raise RuntimeError("R25 review must never run with production/upload flags enabled")
    data = json.loads(Path(input_path).read_text(encoding="utf-8"))
    stories = data["selected_stories"]
    validate_stories(stories)
    source = Path(image_dir)
    slides = [source / f"slide_{i:02d}.png" for i in range(1, 8)]
    if not all(p.is_file() for p in slides):
        raise FileNotFoundError("All seven reviewed carousel slides are required")
    root = build_review_package(input_path, output_dir)
    narrations = build_connected_all(stories)
    frames = [compose(slide, i, root / f"frame_{i:02d}.png")
              for i, slide in enumerate(slides, 1)]
    voice, boundaries = speak_with_boundaries(connected_script(stories),
                                               root / "voice.mp3",
                                               root / "word_boundaries.json")
    video = build_continuous_reel(frames, voice, narrations,
                                  root / "marketrevamp_r25_review.mp4",
                                  root / "segments.json", fps=5,
                                  boundaries_path=boundaries)
    return video


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="news_results.json")
    parser.add_argument("--images", default="instagram_images")
    parser.add_argument("--output", default="r25_review")
    args = parser.parse_args()
    print(render_reviewed_preview(args.input, args.images, args.output))
