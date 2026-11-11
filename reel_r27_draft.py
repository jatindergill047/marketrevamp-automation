"""R27: create a source-linked editorial DRAFT from the existing seven-story feed.

No automatic fact checking, approval, audio, uploads, or publishing.
"""
import json
import re
from pathlib import Path
from urllib.parse import urlparse


def prepare_draft(input_path="news_results.json", output_path="r27_review/draft_stories.json"):
    data = json.loads(Path(input_path).read_text(encoding="utf-8"))
    stories = data.get("selected_stories")
    if not isinstance(stories, list) or len(stories) != 7:
        raise ValueError("R27 needs exactly seven source-selected stories")
    drafts = []
    for i, story in enumerate(stories, 1):
        title, summary = story.get("title"), story.get("summary")
        source_url = story.get("source_url") or story.get("url")
        if not all(isinstance(v, str) and v.strip() for v in (title, summary, source_url)):
            raise ValueError(f"Story {i}: missing title, summary, or source")
        parsed = urlparse(source_url)
        if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
            raise ValueError(f"Story {i}: invalid HTTPS source")
        # Draft uses only existing source-extracted text, without invented implications.
        # Narration remains blank until a human editor checks the article.
        drafts.append({
            "title": title.strip(), "summary": summary.strip(),
            "source_url": source_url, "published": story.get("published"),
            "category": story.get("selected_category", story.get("category")),
            "editorial_impact": "", "narration_text": "",
            "editorial_approved": False, "fact_check_status": "unverified",
            "review_questions": [
                "Does the linked article support every claim and figure?",
                "Are dates, attributions, and uncertainty represented accurately?",
                "What consequential, source-supported impact should the audience know?",
                "Is the final narration natural, accurate, and concise?"
            ],
        })
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps({
        "r27_status": "draft_requires_independent_source_review",
        "source_collected_at": data.get("collected_at"),
        "selected_stories": drafts,
    }, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    review = ["# R27 editorial approval checklist", "",
              "Not fact-checked. Do not mark approved until the linked source is reviewed.",
              "No video, upload, or Instagram publishing is triggered.", ""]
    for i, story in enumerate(drafts, 1):
        review.extend([f"## {i}. {story['title']}", "",
                       f"Source: {story['source_url']}", "",
                       f"Publisher extract: {story['summary']}", "",
                       "Editorial impact: PENDING", "Approved narration: PENDING", ""])
    (output.parent / "EDITORIAL_CHECKLIST.md").write_text("\n".join(review), encoding="utf-8")
    return output


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="news_results.json")
    parser.add_argument("--output", default="r27_review/draft_stories.json")
    args = parser.parse_args()
    print(prepare_draft(args.input, args.output))
