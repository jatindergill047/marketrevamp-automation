"""R30: editorial audit of real-news Reel drafts, without automatic approval.

Flags duplicated subjects, questionable category fit and unverified claims.
Never synthesizes voice or publishes.
"""
import json
import re
from pathlib import Path
from urllib.parse import urlparse

TOPIC_MARKERS = {
    "AI": ("ai", "anthropic", "openai", "chatgpt", "artificial intelligence", "gemini", "nvidia"),
    "Technology": ("amazon", "apple", "microsoft", "cybersecurity", "technology", "software"),
    "Crypto": ("bitcoin", "crypto", "ethereum", "blockchain", "stablecoin"),
    "Markets": ("stocks", "shares", "investors", "nasdaq", "retail sales", "market", "investment"),
}
EVENT_TOKENS = ("bitcoin", "anthropic", "amazon", "ethereum", "openai", "nvidia", "tesla")
REQUIRED_FIELDS = ("title", "summary", "source_url")


def audit(input_path="r29_review/draft_stories.json", output_path="r30_review/audit.json"):
    source = json.loads(Path(input_path).read_text(encoding="utf-8"))
    stories = source.get("selected_stories")
    if not isinstance(stories, list) or len(stories) != 7:
        raise ValueError("R30 requires exactly seven real source-linked stories")
    output = []
    seen = {}
    for index, story in enumerate(stories, 1):
        if not isinstance(story, dict) or any(
            not isinstance(story.get(k), str) or not story[k].strip()
            for k in REQUIRED_FIELDS
        ):
            raise ValueError(f"Story {index} lacks required source fields")
        parsed = urlparse(story["source_url"])
        if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
            raise ValueError(f"Story {index} has an invalid HTTPS source")
        title = story["title"].casefold()
        summary = story["summary"].casefold()
        combined = title + " " + summary
        category = story.get("category")
        category_terms = TOPIC_MARKERS.get(category, ())
        flags = []
        if not any(term in combined for term in category_terms):
            flags.append("weak_category_match")
        entities = [term for term in EVENT_TOKENS if re.search(r"\b" + re.escape(term) + r"\b", title)]
        for entity in entities:
            if entity in seen:
                flags.append(f"repeated_headline_subject:{entity}:story_{seen[entity]}")
            else:
                seen[entity] = index
        if story.get("editorial_approved") is True:
            flags.append("unexpected_preapproval_requires_recheck")
        output.append({
            "story": index, "title": story["title"], "category": category,
            "source_url": story["source_url"],
            "flags": flags,
            "fact_check": "requires_independent_article_review",
            "narration": "pending",
            "editorial_approved": False,
        })
    report = {
        "status": "editorial_review_required",
        "publication": "disabled",
        "automatic_fact_verification": False,
        "stories": output,
        "flagged_stories": sum(bool(item["flags"]) for item in output),
        "next_step": "Verify each source and replace weak or repetitive stories before narration approval.",
    }
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return report


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--input", default="r29_review/draft_stories.json")
    p.add_argument("--output", default="r30_review/audit.json")
    a = p.parse_args()
    print(json.dumps(audit(a.input, a.output), indent=2))
