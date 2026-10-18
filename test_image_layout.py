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

    # Option C must be much smaller than the previous 128px/760px
    # emblem/wordmark masthead, and the lockup must stay centered.
    geometry_canvas = Image.new("RGB", (ig.WIDTH, ig.HEIGHT), "white")
    icon_box, word_box = ig.paste_horizontal_masthead(geometry_canvas)
    assert icon_box[2] - icon_box[0] <= 78
    assert icon_box[3] - icon_box[1] <= 78
    assert word_box[2] - word_box[0] <= 410
    assert word_box[3] - word_box[1] <= 78
    assert icon_box[2] < word_box[0]
    assert abs((icon_box[0] + word_box[2]) / 2 - ig.WIDTH / 2) <= 1
    assert 40 <= min(icon_box[1], word_box[1])
    assert max(icon_box[3], word_box[3]) <= 141

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
        for rectangle in (icon_box, word_box):
            assert card.crop(rectangle).tobytes() != baseline.crop(rectangle).tobytes()
        # Outside the centered lockup there is no oversized old wordmark.
        assert card.getpixel((110, 95)) == (249, 248, 245)
        assert card.getpixel((980, 95)) == (249, 248, 245)
        # The category ribbon and article footer are unchanged.
        assert card.getpixel((80, 260)) == (245, 127, 19)
        assert card.getpixel((100, 1201)) != baseline.getpixel((100, 1201))
        if category == "AI":
            card.save("marketrevamp_brand_preview.png", "PNG", optimize=True)
    # A second offline preview targets the tokenization headline and footer.
    tokenization = ig.draw_card({
        "title": "Research report examines real-world asset tokenization",
        "summary": (
            "A research report examines the potential role of tokenized assets "
            "in financial markets. It discusses how digital ownership records "
            "might connect familiar instruments with blockchain infrastructure. "
            "The discussion focuses on market structure and open questions "
            "rather than projecting any asset prices or guaranteed returns."
        ),
        "summary_status": "ready_for_review",
        "url": "https://example.com/tokenization-preview",
        "selected_category": "Crypto",
    }, 3, 7, "Oct 17, 2026")
    tokenization.save("marketrevamp_tokenization_preview.png", "PNG", optimize=True)
    print("PASS: compact Option C horizontal logo is centered and renders on all four 1080x1350 editorial cards")
    print("PREVIEW: marketrevamp_brand_preview.png (offline, not published)")


if __name__ == "__main__":
    test()
