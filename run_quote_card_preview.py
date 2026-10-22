"""Create a seven-slide synthetic quote experiment, never a live post.

Runs only in Safe Validation on the test PR. No feeds, tokens, secrets,
Cloudinary uploads, production artifact names or Instagram API calls.
"""
from pathlib import Path
from quote_card_preview import render_trial
from test_quote_cards import synthetic_stories

OUTPUT = Path("quote_card_trial")

if __name__ == "__main__":
    result = render_trial(synthetic_stories(), OUTPUT)
    if result != {"quote_count": 1, "quote_slide": 4, "speaker": "Maya Chen"}:
        raise SystemExit(f"Quote preview invariant failed: {result}")
    images = list(OUTPUT.glob("slide_*.png"))
    if len(images) != 7:
        raise SystemExit("Safe quote preview failed seven-slide contract")
    print(f"SAFE TEST ONLY: {len(images)} slides, ONE quoted card at slide 4.")
    print("All headlines, quotes, and speaker names are synthetic demo content.")
    print("Comparison preview: quote_card_trial/before_after.png")
    print("No Instagram post created, uploaded, scheduled or published.")
