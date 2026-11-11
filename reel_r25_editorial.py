"""R25 opt-in source-linked editorial review. Never publishes."""
import json
from pathlib import Path
from urllib.parse import urlparse
from reel_script import connected_script

def validate_stories(stories):
    if not isinstance(stories, list) or len(stories) != 7:
        raise ValueError("R25 requires exactly seven stories")
    reviewed = []
    for index, story in enumerate(stories, 1):
        if not isinstance(story, dict):
            raise ValueError(f"Story {index}: invalid record")
        for field in ("title", "summary", "narration_text", "editorial_impact", "source_url"):
            if not isinstance(story.get(field), str) or not story[field].strip():
                raise ValueError(f"Story {index}: missing reviewed {field}")
        url = urlparse(story["source_url"])
        if url.scheme != "https" or not url.hostname or "." not in url.hostname or url.username or url.password:
            raise ValueError(f"Story {index}: invalid source URL")
        if story.get("editorial_approved") is not True:
            raise ValueError(f"Story {index}: explicit editorial approval required")
        reviewed.append({"index": index, "title": story["title"], "source_url": story["source_url"],
                         "narration_text": story["narration_text"], "editorial_impact": story["editorial_impact"]})
    return reviewed

def build_review_package(input_path, output_dir):
    stories = json.loads(Path(input_path).read_text(encoding="utf-8"))["selected_stories"]
    reviewed = validate_stories(stories)
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    (output / "narration.txt").write_text(connected_script(stories) + "\n", encoding="utf-8")
    (output / "editorial_review.json").write_text(json.dumps({
        "status": "editorial_approval_recorded_not_independently_fact_checked",
        "publication": "disabled", "stories": reviewed}, indent=2) + "\n", encoding="utf-8")
    lines = ["# R25 source-linked editorial review", "",
             "Approvals and links are recorded; claims are not independently verified.", ""]
    for s in reviewed:
        lines += [f"## {s['index']}. {s['title']}", "", f"Source: {s['source_url']}", "",
                  f"Narration: {s['narration_text']}", "",
                  f"Why it matters: {s['editorial_impact']}", ""]
    (output / "REVIEW.md").write_text("\n".join(lines), encoding="utf-8")
    return output

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="news_results.json")
    parser.add_argument("--output", default="r25_review")
    args = parser.parse_args()
    print(build_review_package(args.input, args.output))
