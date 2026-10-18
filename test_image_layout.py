"""Branding and 1080x1350 layout regression, with an offline preview artifact."""
from pathlib import Path

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
    assert "Open Sans" in ig.font(36, bold=False).getname()[0]
    assert "Open Sans" in ig.font(36, bold=True).getname()[0]
    assert bytes(ig.font(36, bold=True).getmask("MARKETS")) != bytes(
        ig.font(36, bold=False).getmask("MARKETS")
    )

    assert ig.LOGO.name == "marketrevamp_logo_horizontal.png"
    with Image.open(ig.LOGO) as approved:
        assert approved.format == "PNG"
        assert approved.width > approved.height * 2.5
        assert approved.convert("RGBA").getchannel("A").getbbox()

    baseline = ig.background(1)
    assert all(channel > 225 for channel in baseline.getpixel((540, 520)))
    for category in ("AI", "Technology", "Crypto", "Markets"):
        card = ig.draw_card({
            "title": "AI safety advances reshape the next wave of enterprise technology",
            "summary": SAMPLE,
            "summary_status": "ready_for_review",
            "url": "https://example.com/market-news",
            "selected_category": category,
        }, 1, 7, "Oct 17, 2026")
        assert card.size == (1080, 1350)
        assert card.mode == "RGB"
        # Both original icon and uploaded wordmark must be visibly present.
        for rectangle in ((80, 50, 205, 167), (240, 56, 895, 158)):
            assert card.crop(rectangle).tobytes() != baseline.crop(rectangle).tobytes()
        # The category ribbon and article footer are unchanged.
        assert card.getpixel((80, 260)) == (245, 127, 19)
        assert card.getpixel((100, 1201)) != baseline.getpixel((100, 1201))
        if category == "AI":
            card.save("marketrevamp_brand_preview.png", "PNG", optimize=True)
    print("PASS: approved horizontal PNG renders on four 1080x1350 editorial cards")
    print("PREVIEW: marketrevamp_brand_preview.png (offline, not published)")


if __name__ == "__main__":
    test()
