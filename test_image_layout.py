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
    assert "Open Sans" in ig.font(36, bold=False).getname()[0]
    assert "Open Sans" in ig.font(36, bold=True).getname()[0]
    assert bytes(ig.font(36, bold=True).getmask("MARKETS")) != bytes(ig.font(36, bold=False).getmask("MARKETS"))

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
                }, 1, 7, "Oct 14, 2026")
                assert image.size == (1080, 1350)
                assert image.mode == "RGB"
                # Newspaper template is high-key; logo is inset into a white masthead.
                baseline = ig.background(1)
                assert all(channel > 225 for channel in baseline.getpixel((540, 520)))
                assert image.getpixel((80, 70)) == (0, 210, 235)
                assert image.getpixel((185, 55)) == (255, 255, 255)
                # Header, section ribbon, and source area are visibly rendered.
                assert image.getpixel((80, 260)) == (245, 127, 19)
                assert image.getpixel((100, 1201)) != baseline.getpixel((100, 1201))
    print("PASS: four categories render as 1080x1350 white editorial cards with transparent top-left PNG logo")

if __name__ == "__main__":
    test()
