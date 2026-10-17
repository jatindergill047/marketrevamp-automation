"""MarketRevamp: create seven branded 1080x1350 Instagram news cards.

Run: python image_generator.py
Input: news_results.json from news_collector.py
Output: instagram_images/slide_01.png ... slide_07.png
Requires: Pillow>=11.0,<13.0
"""

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

from PIL import Image, ImageDraw, ImageFont
from newspaper_design import newspaper_background, draw_editorial_illustration, INK, CYAN, ORANGE

WIDTH, HEIGHT = 1080, 1350
INPUT = Path("news_results.json")
OUTPUT = Path("instagram_images")
LOGO = Path("marketrevamp_logo.png")
NAVY = (6, 18, 38)
WHITE = (246, 250, 255)
MUTED = (158, 181, 205)
COLORS = {
    "AI": (4, 207, 224),
    "Technology": (111, 135, 255),
    "Crypto": (245, 177, 66),
    "Markets": (67, 223, 161),
}
MIN_SUMMARY_WORDS = 30
MAX_SUMMARY_WORDS = 90


OPEN_SANS_FONT = Path("fonts/OpenSans[wdth,wght].ttf")


def font(size, bold=False):
    """Use Open Sans variable font for every slide text field.

    Fail closed rather than silently publishing using a different font.
    prepare_fonts.py downloads the OFL-licensed font before rendering.
    """
    if not OPEN_SANS_FONT.is_file():
        raise FileNotFoundError(
            "Open Sans is missing. Run python prepare_fonts.py before image generation."
        )
    face = ImageFont.truetype(str(OPEN_SANS_FONT), size)
    # Detect axis order rather than assuming how the variable font is stored.
    axes = face.get_variation_axes()
    values = []
    weight_found = False
    for axis in axes:
        name = axis["name"].decode("utf-8", errors="replace").lower()
        if "weight" in name:
            target = 700 if bold else 400
            weight_found = True
        elif "width" in name:
            target = 100
        else:
            target = axis["default"]
        values.append(max(axis["minimum"], min(axis["maximum"], target)))
    if not weight_found:
        raise RuntimeError("Open Sans variable font has no weight axis")
    face.set_variation_by_axes(values)
    return face


def wrap_lines(draw, text, face, max_width):
    """Wrap by measured pixel width, splitting exceptionally long tokens if needed."""
    words = re.sub(r"\s+", " ", str(text)).strip().split()
    lines = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if draw.textbbox((0, 0), candidate, font=face)[2] <= max_width:
            current = candidate
            continue
        if current:
            lines.append(current)
            current = ""
        # Extremely long URLs/tokens should never spill outside the card.
        if draw.textbbox((0, 0), word, font=face)[2] > max_width:
            chunk = ""
            for character in word:
                test = chunk + character
                if chunk and draw.textbbox((0, 0), test, font=face)[2] > max_width:
                    lines.append(chunk)
                    chunk = character
                else:
                    chunk = test
            current = chunk
        else:
            current = word
    if current:
        lines.append(current)
    return lines


def fit_headline(draw, text, max_width=902, max_lines=6, max_height=300):
    for size in range(70, 25, -2):
        face = font(size, bold=True)
        lines = wrap_lines(draw, text, face, max_width)
        line_height = size + 17
        if len(lines) <= max_lines and len(lines) * line_height <= max_height:
            return face, lines, line_height
    raise ValueError(f"Headline cannot fit without truncation: {text}")


def fit_summary(draw, text, max_width=865, max_height=235):
    """Use larger readable text without clipping or truncation."""
    for size in range(36, 15, -1):
        face = font(size)
        lines = wrap_lines(draw, text, face, max_width)
        line_height = size + 10

        if len(lines) * line_height <= max_height:
            return face, lines, line_height

    raise ValueError(
        "Summary is too long for readable text. "
        "Shorten the summary or increase the available space."
    )


def background(accent, index):
    """Compatibility wrapper for the all-white 2D editorial background."""
    return newspaper_background(index)


def source_name(url):
    host = urlparse(url or "").netloc.lower().removeprefix("www.")
    return host or "Source unavailable"


def story_category(story):
    """Editorial category takes precedence over the source feed category."""
    for key in ("display_category", "selected_category", "category"):
        value = story.get(key)
        if value in COLORS:
            return value
    return "Technology"


def summary_for_card(story):
    """Return a draft summary and whether it passes basic length/status checks."""
    summary = (story.get("verified_summary") or story.get("summary") or "").strip()
    count = len(summary.split())
    status = story.get("summary_status", "")
    valid = MIN_SUMMARY_WORDS <= count <= MAX_SUMMARY_WORDS
    if status in ("insufficient_source_text", "summary_needs_manual_review"):
        valid = False
    if not valid:
        # Do not display a misleading, possibly invalid article summary.
        return "Summary requires editorial review. Read the original article before publishing this slide.", False
    return summary, True


def _draw_lines(draw, lines, x, y, face, color, leading):
    for line in lines:
        draw.text((x, y), line, font=face, fill=color)
        y += leading
    return y


def _fit_text(draw, text, width, max_height, largest, smallest, bold=False):
    """Return complete wrapped copy that fits; never truncate article text."""
    for size in range(largest, smallest - 1, -1):
        face = font(size, bold=bold)
        lines = wrap_lines(draw, text, face, width)
        leading = size + (12 if bold else 10)
        if len(lines) * leading <= max_height:
            return face, lines, leading
    raise ValueError("News text does not fit in the editorial card without clipping")


def _fit_editorial(draw, headline, summary):
    """Fit an entire summary in ONE compact section directly below headline.

    Preserve the complete original extractive text in its original order.
    No separate lead paragraph, artificial bullets, or giant empty panel.
    """
    for headline_size in range(56, 31, -2):
        hface = font(headline_size, bold=True)
        hlines = wrap_lines(draw, headline, hface, 930)
        hlead = headline_size + 11
        hbottom = 300 + len(hlines) * hlead
        if hbottom > 680:
            continue

        section_y = hbottom + 35
        text_y = section_y + 77
        for summary_size in range(29, 18, -1):
            sface = font(summary_size)
            slines = wrap_lines(draw, summary, sface, 860)
            slead = summary_size + 12
            text_bottom = text_y + len(slines) * slead
            panel_bottom = text_bottom + 28
            if panel_bottom <= 1170:
                return (hface, hlines, hlead, section_y, sface,
                        slines, slead, text_y, panel_bottom)
    raise ValueError("Complete source summary cannot fit in the unified editorial section")


def _article_date(story, edition_date):
    """Prefer the RSS article timestamp; otherwise label the edition honestly."""
    published = story.get("published")
    if published:
        try:
            stamp = datetime.fromisoformat(str(published).replace("Z", "+00:00"))
            if stamp.tzinfo is None:
                raise ValueError("Timestamp missing timezone")
            return "ARTICLE DATE: " + stamp.strftime("%b %d, %Y").upper()
        except (ValueError, TypeError):
            pass
    return "EDITION: " + str(edition_date).upper()


def draw_card(story, index, total, date_label):
    """Adaptive editorial news layout; no generated factual imagery or paid APIs."""
    if not 1 <= index <= total == 7:
        raise ValueError("Expected slide index 1–7 of 7")
    summary, valid = summary_for_card(story)
    if not valid:
        raise ValueError("Cannot render a news card with an invalid summary")
    headline = (story.get("title") or "").strip()
    if not headline:
        raise ValueError("Missing article headline")

    image = background(CYAN, index)
    draw = ImageDraw.Draw(image)
    left, right = 67, 1013

    # Give the original square logo a deliberate white newspaper masthead
    # treatment, rather than pretending its dark background is transparent.
    draw.rounded_rectangle((left - 10, 37, 196, 175), radius=13,
                           fill=(255, 255, 255), outline=(200, 207, 210), width=2)
    if not LOGO.exists():
        raise FileNotFoundError("Missing marketrevamp_logo.png in the repository root")
    with Image.open(LOGO) as original_logo:
        if original_logo.format != "PNG":
            raise ValueError("MarketRevamp logo must be a PNG file")
        logo = original_logo.convert("RGBA")
        logo.thumbnail((116, 116), Image.Resampling.LANCZOS)
        image.paste(logo, (74 + (116 - logo.width) // 2, 48 + (116 - logo.height) // 2), logo)

    draw = ImageDraw.Draw(image)
    draw.text((221, 73), "MARKETREVAMP", font=font(48, bold=True), fill=INK)
    draw.text((221, 135), "GLOBAL NEWS  •  SMART INSIGHTS  •  BIGGER PERSPECTIVE",
              font=font(16, bold=True), fill=(65, 74, 85))
    draw.line((left, 203, right, 203), fill=(153, 164, 171), width=2)

    category = story_category(story)
    label = {"AI": "ARTIFICIAL INTELLIGENCE", "Technology": "TECHNOLOGY",
             "Crypto": "CRYPTOCURRENCY", "Markets": "FINANCIAL MARKETS"}[category]
    ribbon_width = min(550, max(265, len(label) * 17 + 54))
    draw.polygon([(left + 17, 220), (left + ribbon_width, 220),
                  (left + ribbon_width - 18, 271), (left, 271)], fill=ORANGE)
    draw.text((left + 27, 230), label, font=font(25, bold=True),
              fill=(255, 255, 255))
    draw.text((right, 230), f"{index:02d}/{total:02d}",
              font=font(26, bold=True), fill=INK, anchor="ra")

    (hface, hlines, hlead, section_y, sface, slines,
     slead, text_y, panel_bottom) = _fit_editorial(draw, headline, summary)
    _draw_lines(draw, hlines, left, 300, hface, INK, hlead)

    # All original summary sentences live together in one compact card.
    # The section begins just below the headline; the background ends
    # just below the last text line instead of filling an empty fixed area.
    draw.rounded_rectangle((left, section_y, left + 245, section_y + 52),
                           radius=22, fill=INK)
    draw.text((left + 26, section_y + 10), "KEY DETAILS",
              font=font(25, bold=True), fill=(255, 255, 255))
    draw.line((left + 265, section_y + 28, right, section_y + 28),
              fill=INK, width=2)

    draw.rounded_rectangle((left, text_y - 14, right, panel_bottom),
                           radius=17, fill=(239, 246, 249))
    draw.rectangle((left, text_y - 14, left + 7, panel_bottom),
                   fill=CYAN)
    _draw_lines(draw, slines, left + 34, text_y, sface, INK, slead)

    # Use the empty lower region as tasteful newspaper art, but never
    # compete with the summary or the fixed publication/source footer.
    draw_editorial_illustration(image, panel_bottom, index=index,
                                category=category)

    draw.line((left, 1200, right, 1200), fill=INK, width=2)
    draw.text((left, 1216), "SOURCE:", font=font(18, bold=True), fill=INK)
    src = source_name(story.get("url", ""))
    src_face, src_lines, _ = _fit_text(draw, src, 530, 33, 21, 16, bold=True)
    if len(src_lines) != 1:
        raise ValueError("Source domain cannot fit in footer")
    draw.text((left + 110, 1214), src_lines[0], font=src_face, fill=CYAN)
    draw.text((left, 1252), _article_date(story, date_label),
              font=font(18), fill=(72, 75, 78))
    draw.text((right, 1223), "SWIPE  ›", font=font(23, bold=True),
              fill=INK, anchor="ra")
    draw.text((left, 1303), "MARKETREVAMP  •  NEWS, NOT INVESTMENT ADVICE",
              font=font(16, bold=True), fill=(85, 91, 95))
    assert image.size == (WIDTH, HEIGHT)
    return image


def main():
    if not LOGO.exists():
        raise SystemExit("Missing marketrevamp_logo.png. Upload the official logo to the repository root.")
    if not INPUT.exists():
        raise SystemExit("Missing news_results.json. Run news_collector.py first.")
    data = json.loads(INPUT.read_text(encoding="utf-8"))
    stories = data.get("selected_stories", [])
    if len(stories) != 7:
        raise SystemExit(f"Expected exactly 7 selected stories; found {len(stories)}. No images created.")

    OUTPUT.mkdir(parents=True, exist_ok=True)
    collected = data.get("collected_at")
    try:
        dt = datetime.fromisoformat(collected.replace("Z", "+00:00"))
    except (AttributeError, ValueError):
        dt = datetime.now(timezone.utc)
    date_label = dt.strftime("%b %d, %Y")

    for index, story in enumerate(stories, 1):
        path = OUTPUT / f"slide_{index:02d}.png"
        draw_card(story, index, len(stories), date_label).save(path, "PNG", optimize=True)
        category = story_category(story)
        summary, valid = summary_for_card(story)
        print(f"Created {path} | {category} | Summary: {'draft_ready_for_review' if valid else 'REVIEW_REQUIRED'} | {story.get('title', '')}")
    print(f"Finished: {len(stories)} separate 1080x1350 images in {OUTPUT}/")
    print("Images are local files only. Nothing has been published or uploaded.")


if __name__ == "__main__":
    main()
