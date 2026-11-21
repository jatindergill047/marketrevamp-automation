"""Render a synthetic, visibly marked R72 full-media news-style integration test.

Uses seven fictional story descriptions from the original R70 demo.
Never fetches current news or creates any publication authorization.
"""
import json
from pathlib import Path

from reel_clean_end_to_end_review import SCENES
from reel_r72_review import render_review

TOPICS = ("AI", "Technology", "Crypto", "Technology",
          "Technology", "AI", "Markets")


def main():
    stories = []
    for index, (headline, deck, narration) in enumerate(SCENES, 1):
        stories.append({
            "headline": headline,
            "deck": deck,
            "narration_text": narration,
            "category": TOPICS[index-1],
            "source_name": "SYNTHETIC DEMO — NOT NEWS",
            "source_url": f"https://example.org/synthetic-review/{index}",
        })
    output_dir = Path("r72_synthetic_review")
    qa = render_review(
        stories, output_dir=output_dir,
        toronto_date="2026-11-23", synthetic=True,
    )
    assert qa["synthetic_content"] is True
    assert qa["real_source_headlines"] is False
    assert qa["status"] == "review_only"
    assert qa["editorial_approved"] is False
    assert qa["published"] is False
    assert qa["cloudinary_uploaded"] is False
    assert qa["instagram_published"] is False
    assert qa["seven_scenes"] == 7 and qa["presentation_segments"] == 9
    assert qa["spoken_hook"] == "Here's what's making headlines today."
    assert qa["spoken_follow_cta"].startswith("Follow MarketRevamp")
    assert 45 <= qa["duration_seconds"] <= 90
    assert qa["alignment_token_ratio"] >= .90
    assert qa["video_codec"] == "h264" and qa["audio_codec"] == "aac"
    print("R72_SYNTHETIC_MEDIA_SMOKE_PASS", json.dumps(qa))


if __name__ == "__main__":
    main()
