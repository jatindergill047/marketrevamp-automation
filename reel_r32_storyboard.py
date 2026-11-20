"""R32: prepare an auditable storyboard from curated R31 copy.

No approval, TTS, video rendering, network access or publishing.
"""
import json
import os
from pathlib import Path
from urllib.parse import urlparse

FLAGS = ("REEL_ENABLED", "REEL_UPLOAD_ENABLED", "INSTAGRAM_PUBLISH_ENABLED")


def prepare(input_path="r31_review/curated_stories.json", output_dir="r32_review"):
    if any(os.getenv(flag, "false").strip().lower() == "true" for flag in FLAGS):
        raise RuntimeError("R32 is review-only: disable Reel and publishing flags")
    data = json.loads(Path(input_path).read_text(encoding="utf-8"))
    stories = data.get("selected_stories")
    if not isinstance(stories, list) or len(stories) != 7:
        raise ValueError("Seven stories required")
    storyboard = []
    for index, story in enumerate(stories, 1):
        fields = ("title", "summary", "narration_text", "editorial_impact", "source_url")
        if any(not isinstance(story.get(k), str) or not story[k].strip() for k in fields):
            raise ValueError(f"Story {index}: incomplete source-linked copy")
        url = urlparse(story["source_url"])
        if url.scheme != "https" or not url.hostname or url.username or url.password:
            raise ValueError(f"Story {index}: invalid source URL")
        if story.get("editorial_approved") is True:
            raise ValueError("R32 must not silently reuse preapproved content")
        storyboard.append({
            "slide": index,
            "headline": story["title"],
            "category": story.get("category"),
            "voiceover": story["narration_text"],
            "editorial_impact": story["editorial_impact"],
            "source_url": story["source_url"],
            "fact_check_status": story.get("fact_check_status", "unverified"),
            "editorial_approved": False,
        })
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    package = {
        "status": "awaiting_independent_fact_check_and_editorial_approval",
        "publication": "disabled",
        "render": "not_started",
        "voiceover": "draft_only",
        "stories": storyboard,
    }
    (output / "storyboard.json").write_text(json.dumps(package, indent=2, ensure_ascii=False)+"\n", encoding="utf-8")
    lines = ["# MarketRevamp R32 — Review-only storyboard", "",
             "Seven proposed stories. No independent fact-check, approval, audio, video, upload or publication.", ""]
    for story in storyboard:
        lines += [f"## Slide {story['slide']}: {story['headline']}", "",
                  f"Category: {story['category']}", "",
                  f"Voiceover: {story['voiceover']}", "",
                  f"Impact: {story['editorial_impact']}", "",
                  f"Source: {story['source_url']}", "",
                  "Verification: PENDING", "Editorial approval: PENDING", ""]
    (output / "STORYBOARD.md").write_text("\n".join(lines), encoding="utf-8")
    return package


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="r31_review/curated_stories.json")
    parser.add_argument("--output", default="r32_review")
    args = parser.parse_args()
    result = prepare(args.input, args.output)
    print(json.dumps({"status": result["status"], "stories": len(result["stories"])}))
