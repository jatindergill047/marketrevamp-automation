"""Offline-only MarketRevamp one-quote-card newspaper preview renderer.

Not imported by the production image generator or publisher. Every quote
is re-validated against literal article text before rendering.
"""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from carousel_config import CAROUSEL_SIZE
import image_generator as news
from newspaper_design import INK, CYAN, ORANGE
from quote_cards import quote_matches_source, select_one_quote


def draw_quote_card(story, index, total, date_label, quote):
    """Render a distinctly marked experimental card, preserving C2 branding."""
    if not 1 <= index <= total == CAROUSEL_SIZE:
        raise ValueError("Expected slide index 1–7 of 7")
    if not quote_matches_source(story, quote):
        raise ValueError("Quote text or speaker is not supported by article")
    _, valid = news.summary_for_card(story)
    if not valid:
        raise ValueError("Cannot display an unreviewable article")
    headline = (story.get("title") or "").strip()
    if not headline:
        raise ValueError("Cannot draw a quote without a headline")

    image = news.background(index)
    draw = ImageDraw.Draw(image)
    left, right = 67, 1013
    draw.rectangle((left - 10, 37, right + 6, 190), fill=(249, 248, 245))
    news.paste_horizontal_masthead(image)
    draw = ImageDraw.Draw(image)

    draw.text((news.WIDTH // 2, 151),
              "GLOBAL NEWS  •  SMART INSIGHTS  •  BIGGER PERSPECTIVE",
              font=news.font(14, bold=True), fill=(65, 74, 85), anchor="mt")
    draw.line((left, 203, right, 203), fill=(153, 164, 171), width=2)

    category = news.story_category(story)
    label = {"AI": "ARTIFICIAL INTELLIGENCE", "Technology": "TECHNOLOGY",
             "Crypto": "CRYPTOCURRENCY", "Markets": "FINANCIAL MARKETS"}[category]
    ribbon_width = min(550, max(265, len(label) * 17 + 54))
    draw.polygon([(left + 17, 220), (left + ribbon_width, 220),
                  (left + ribbon_width - 18, 271), (left, 271)], fill=ORANGE)
    draw.text((left + 27, 230), label, font=news.font(25, bold=True),
              fill=(255, 255, 255))
    draw.text((right, 230), f"{index:02d}/{total:02d}",
              font=news.font(26, bold=True), fill=INK, anchor="ra")

    # Keep the title prominent, but let the quotation own the visual focus.
    h_face, h_lines, h_lead = news._fit_text(
        draw, headline, 930, 235, 47, 32, bold=True
    )
    news._draw_lines(draw, h_lines, left, 300, h_face, INK, h_lead)
    h_bottom = 300 + len(h_lines) * h_lead
    label_y = h_bottom + 28
    if label_y + 54 >= 845:
        raise ValueError("Quote headline would crowd the text panel")

    draw.rounded_rectangle((left, label_y, left + 244, label_y + 52),
                           radius=22, fill=INK)
    draw.text((left + 25, label_y + 10), "DIRECT QUOTE",
              font=news.font(24, bold=True), fill=(255, 255, 255))
    draw.line((left + 264, label_y + 28, right, label_y + 28),
              fill=INK, width=2)

    # Pull-quote design: airy typography, subtle ink rules, and one
    # source-accurate attribution. No quotations or roles are invented.
    top = label_y + 73
    text_y = top + 116
    quote_x = left + 60
    # Preserve every word; decrease type only when the full quotation, plus
    # its speaker attribution, fits above the publication footer.
    selected = None
    for size in range(49, 33, -1):
        face = news.font(size)
        lines = news.wrap_lines(draw, quote["text"], face, 824)
        leading = size + 13
        separator_y = text_y + len(lines) * leading + 15
        attribution_label_y = separator_y + 15
        speaker_y = attribution_label_y + 22
        bottom = speaker_y + 55
        if bottom <= 1135:
            selected = (face, lines, leading, separator_y,
                        attribution_label_y, speaker_y, bottom)
            break
    if selected is None:
        raise ValueError("Exact source quote cannot fit without clipping")

    (q_face, lines, leading, separator_y,
     attribution_label_y, speaker_y, bottom) = selected
    draw.rounded_rectangle((left, top, right, bottom),
                           radius=19, fill=(240, 247, 250))
    draw.rectangle((left, top, left + 7, bottom), fill=CYAN)

    # A proper oversized editorial opening quotation mark (not a fake image)
    # gives the card a distinct voice without changing the quoted source.
    try:
        opener = ImageFont.truetype(
            "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf", 106
        )
    except OSError:
        opener = news.font(106, bold=True)
    draw.text((left + 43, top + 2), "“",
              font=opener, fill=CYAN)
    draw.line((left + 128, top + 70, left + 220, top + 70),
              fill=ORANGE, width=5)
    news._draw_lines(draw, lines, quote_x, text_y,
                     q_face, INK, leading)

    # Separate the speaker from the quote, so the name reads as
    # attribution rather than an extension of the quoted sentence.
    draw.line((left + 53, separator_y, right - 52, separator_y),
              fill=(198, 217, 227), width=2)
    draw.text((left + 56, attribution_label_y), "ATTRIBUTED TO",
              font=news.font(15, bold=True), fill=(84, 110, 128))
    draw.text((left + 56, speaker_y), quote["speaker"],
              font=news.font(27, bold=True), fill=INK)
    # This visual is always marked as a non-publishable experiment.
    draw.text((left, 1160), "EXPERIMENT  •  NOT FOR PUBLICATION",
              font=news.font(17, bold=True), fill=(110, 111, 108))

    draw.line((left, 1200, right, 1200), fill=INK, width=2)
    draw.text((left, 1216), "SOURCE:", font=news.font(18, bold=True), fill=INK)
    source = news.source_name(story.get("url", ""))
    src_face, src_lines, _ = news._fit_text(
        draw, source, 530, 33, 21, 16, bold=True
    )
    if len(src_lines) != 1:
        raise ValueError("Source domain cannot fit in quote card footer")
    draw.text((left + 110, 1214), src_lines[0], font=src_face, fill=CYAN)
    draw.text((left, 1252), news._article_date(story, date_label),
              font=news.font(18), fill=(72, 75, 78))
    draw.text((right, 1223), "SWIPE  ›",
              font=news.font(23, bold=True), fill=INK, anchor="ra")
    disclaimer = "MARKETREVAMP  •  NEWS, NOT INVESTMENT ADVICE"
    draw.text((left, news.FOOTER_DISCLAIMER_Y), disclaimer,
              font=news.font(16, bold=True), fill=(85, 91, 95))
    if image.size != (1080, 1350):
        raise AssertionError("Quote-card image size must remain 1080x1350")
    return image


def render_trial(stories, output, date_label="Oct 20, 2026"):
    """Seven safe local preview PNGs: at most one quote, all else unchanged.

    If nothing meets source and readability checks, all seven stay standard.
    This never calls the production carousel creator, uploader or publisher.
    """
    if len(stories) != CAROUSEL_SIZE:
        raise ValueError("Preview requires exactly seven distinct stories")
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    quote_index, quote = select_one_quote(stories)
    selected = None
    if quote is not None:
        # The source may be quotable but its card might be too long to fit.
        try:
            selected = draw_quote_card(
                stories[quote_index], quote_index + 1, CAROUSEL_SIZE,
                date_label, quote,
            )
        except ValueError:
            quote_index, quote = None, None

    regular_comparison = None
    for idx, story in enumerate(stories):
        if idx == quote_index:
            card = selected
            regular_comparison = news.draw_card(
                story, idx + 1, CAROUSEL_SIZE, date_label)
        else:
            card = news.draw_card(story, idx + 1, CAROUSEL_SIZE, date_label)
        card.save(output / f"slide_{idx + 1:02d}.png",
                  "PNG", optimize=True)

    if quote_index is not None:
        selected.save(output / "quote_card_experiment.png",
                      "PNG", optimize=True)
        regular_comparison.save(output / "standard_card_comparison.png",
                                "PNG", optimize=True)
        side_by_side = Image.new("RGB", (2160, 1350), (249, 248, 245))
        side_by_side.paste(regular_comparison, (0, 0))
        side_by_side.paste(selected, (1080, 0))
        side_by_side.save(output / "before_after.png",
                          "PNG", optimize=True)
    return {
        "quote_count": 1 if quote_index is not None else 0,
        "quote_slide": quote_index + 1 if quote_index is not None else None,
        "speaker": quote["speaker"] if quote else None,
    }
