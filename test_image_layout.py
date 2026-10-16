"""Safe image layout smoke test, no external APIs or Instagram publishing."""
import tempfile
from pathlib import Path
from unittest.mock import patch

from PIL import Image, ImageDraw
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
    assert "Playfair Display" in ig.font(36, bold=False).getname()[0]
    assert "Playfair Display" in ig.font(36, bold=True).getname()[0]
    assert ig.font(36, bold=True).getname() != ig.font(36, bold=False).getname()

    with tempfile.TemporaryDirectory() as folder:
        logo = Path(folder) / "logo.png"
        sample_logo = Image.new("RGBA", (150, 150), (0, 0, 0, 0))
        ImageDraw.Draw(sample_logo).rectangle((0, 0, 74, 149), fill=(0, 210, 235, 255))
        sample_logo.save(logo)
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
                # Top-right PNG logo retains its transparent half.
                assert image.getpixel((945, 55)) == (0, 210, 235)
                baseline = ig.background(ig.COLORS[category], 1)
                assert image.getpixel((1010, 55)) == baseline.getpixel((1010, 55))
                # Removed header wordmark and tagline must leave background intact.
                assert image.getpixel((580, 62)) == baseline.getpixel((580, 62))
                assert image.getpixel((610, 100)) == baseline.getpixel((610, 100))
    print("PASS: four categories render as 1080x1350 with transparent top-right PNG logo")

if __name__ == "__main__":
    test()
