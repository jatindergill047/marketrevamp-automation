"""Safe image layout smoke test, no external APIs or Instagram publishing."""
import tempfile
from pathlib import Path
from unittest.mock import patch

from PIL import Image
import image_generator as ig

SAMPLE = (
    "Major advances in AI safety are accelerating enterprise adoption, "
    "as new guardrails, monitoring tools, and governance frameworks "
    "reduce risk and build trust, paving the way for broader, more secure "
    "deployment across industries. Regulators and researchers are reviewing "
    "methods that make AI systems safer for businesses."
)


def test():
    assert ig.WIDTH == 1080 and ig.HEIGHT == 1350
    with tempfile.TemporaryDirectory() as folder:
        logo = Path(folder) / "logo.png"
        Image.new("RGBA", (150, 150), (0, 210, 235, 255)).save(logo)
        with patch.object(ig, "LOGO", logo):
            for category in ("AI", "Technology", "Crypto", "Markets"):
                image = ig.draw_card({
                    "title": "AI safety advances reshape the next wave of enterprise technology",
                    "summary": SAMPLE,
                    "summary_status": "ready_for_review",
                    "url": "https://example.com/market-news",
                    "selected_category": category,
                }, 1, 5, "Oct 14, 2026")
                assert image.size == (1080, 1350)
                assert image.mode == "RGB"
    assert ig.visual_theme({"title": "Bitcoin rises", "selected_category": "Crypto"}) == "bitcoin"
    assert ig.visual_theme({"title": "Nvidia GPU launch", "selected_category": "Technology"}) == "chip"
    assert ig.visual_theme({"title": "Security breach", "selected_category": "AI"}) == "security"
    assert ig.visual_theme({"title": "Retail earnings", "selected_category": "Markets"}) == "markets"
    assert ig.visual_theme({"title": "Other story", "selected_category": "AI"}) == "chip"
    # Tight space intentionally omits the illustration, preserving text clarity.
    assert ig.draw_story_visual(Image.new("RGB", (1080, 1350)),
                                {"title": "Bitcoin", "category": "Crypto"}, 500, 620) is False
    assert ig.draw_story_visual(Image.new("RGB", (1080, 1350)),
                                {"title": "Bitcoin", "category": "Crypto"}, 390, 650) is True
    print("PASS: responsive 4:5 rendering and six free-story-visual checks")


if __name__ == "__main__":
    test()
