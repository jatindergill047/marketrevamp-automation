"""R26: prepare a real-news Reel review without approving or publishing it.

Input must be an editor-approved seven-story JSON file with matching slides.
No network article fetching or automatic fact verification is implied.
"""
import json
import os
import subprocess
from pathlib import Path

from reel_r25_preview import render_reviewed_preview
from reel_r25_editorial import validate_stories


def prepare_r26(input_path="news_results.json", image_dir="instagram_images",
                output_dir="r26_review"):
    if any(os.getenv(k, "false").strip().lower() == "true" for k in
           ("REEL_ENABLED", "REEL_UPLOAD_ENABLED", "INSTAGRAM_PUBLISH_ENABLED")):
        raise RuntimeError("R26 is review-only; disable all publishing and upload flags")
    source = Path(input_path)
    data = json.loads(source.read_text(encoding="utf-8"))
    stories = data["selected_stories"]
    reviewed = validate_stories(stories)
    slides = [Path(image_dir) / f"slide_{i:02d}.png" for i in range(1, 8)]
    if not all(p.is_file() for p in slides):
        raise FileNotFoundError("Seven original carousel slides are required")
    video = render_reviewed_preview(source, image_dir, output_dir)
    root = Path(output_dir)
    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries",
         "stream=codec_name,codec_type,width,height:format=duration",
         "-of", "json", str(video)],
        capture_output=True, text=True, check=True, timeout=30)
    media = json.loads(probe.stdout)
    streams = media["streams"]
    if not any(s.get("codec_type") == "video" and s.get("codec_name") == "h264"
               and s.get("width") == 1080 and s.get("height") == 1920
               for s in streams):
        raise RuntimeError("R26 output must contain 1080x1920 H264 video")
    if not any(s.get("codec_type") == "audio" and s.get("codec_name") == "aac"
               for s in streams):
        raise RuntimeError("R26 output must contain AAC audio")
    seconds = float(media["format"]["duration"])
    report = {
        "status": "awaiting_human_editorial_and_visual_review",
        "publication": "disabled",
        "independent_fact_check": "not_performed",
        "source_links_recorded": len(reviewed),
        "video_seconds": round(seconds, 2),
        "target_duration_seconds": [60, 90],
        "duration_within_target": 60 <= seconds <= 90,
        "audio_visual_qa": "manual_review_required",
        "source_verification": "manual_review_required",
        "video": video.name,
    }
    (root / "R26_QA.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="news_results.json")
    parser.add_argument("--images", default="instagram_images")
    parser.add_argument("--output", default="r26_review")
    args = parser.parse_args()
    print(json.dumps(prepare_r26(args.input, args.images, args.output), indent=2))
