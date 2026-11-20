"""R28 independent Reel news selection from an existing collector snapshot.

Does not run the production collector, change its output, approve claims,
create slides, synthesize voice, upload, or publish.
"""
import json
from pathlib import Path

from editorial_config import SUMMARY_MIN_WORDS, SUMMARY_MAX_WORDS
from news_collector import (fetch_article_text, generate_summary, infer_category,
                            normalize_article_url, published_article_urls)
from news_quality import select_usable
from reel_r27_draft import prepare_draft


def select_reel_stories(input_path="news_results.json",
                        history_path="instagram_publish_history.json",
                        output_path="r28_review/reel_news_results.json"):
    data = json.loads(Path(input_path).read_text(encoding="utf-8"))
    candidates = data.get("articles")
    if not isinstance(candidates, list):
        raise ValueError("R28 requires collector articles; no fallback to fabricated stories")
    # Fail closed when publishing history is missing or malformed.
    previously_published = published_article_urls(Path(history_path))
    eligible = []
    for story in candidates:
        if not isinstance(story, dict):
            continue
        url = story.get("url", "")
        if (not isinstance(url, str) or not normalize_article_url(url)
                or normalize_article_url(url) in previously_published):
            continue
        if not isinstance(story.get("score"), (int, float)) or story["score"] <= 0:
            continue
        eligible.append(story)
    selected = select_usable(
        eligible, infer_category, fetch_article_text, generate_summary,
        SUMMARY_MIN_WORDS, SUMMARY_MAX_WORDS, require_quote=False)
    if len(selected) != 7:
        raise RuntimeError("R28 needs seven independently selected usable articles")
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps({
        "collected_at": data.get("collected_at"),
        "selection_status": "source_screened_not_independently_fact_checked",
        "selected_stories": selected,
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return output


def prepare_r28(input_path="news_results.json",
                history_path="instagram_publish_history.json",
                output_dir="r28_review"):
    root = Path(output_dir)
    selected = select_reel_stories(input_path, history_path, root / "reel_news_results.json")
    return prepare_draft(selected, root / "draft_stories.json")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="news_results.json")
    parser.add_argument("--history", default="instagram_publish_history.json")
    parser.add_argument("--output", default="r28_review")
    args = parser.parse_args()
    print(prepare_r28(args.input, args.history, args.output))
