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
from newspaper_design import newspaper_background, INK, CYAN, ORANGE

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


def _summary_parts(summary):
    """Extract intro and details from the supplied summary; invent nothing."""
    sentences = re.split(r"(?<=[.!?])\\s+(?=[A-Z0-9])", summary.strip())
    sentences = [s.strip() for s in sentences if s.strip()]
    if len(sentences) <= 1:
        words = summary.split()
        split = min(len(words), max(10, len(words) // 3))
        return " ".join(words[:split]), [" ".join(words[split:])]
    return sentences[0], sentences[1:]


def draw_card(story, index, total, date_label):
    """White newspaper-inspired editorial layout; no external visual APIs.

    All news text is taken from the selected story. Decorative 2D elements
    never depict or assert a factual event.
    """
    category = story_category(story)
    image = background(CYAN, index)
    draw = ImageDraw.Draw(image)
    left, right = 67, 1013

    # Official transparent PNG at top left; preserve original aspect ratio.
    if not LOGO.exists():
        raise FileNotFoundError("Missing marketrevamp_logo.png in the repository root")
    with Image.open(LOGO) as original_logo:
        if original_logo.format != "PNG":
            raise ValueError("MarketRevamp logo must be a PNG file")
        logo = original_logo.convert("RGBA")
        logo.thumbnail((425, 120), Image.Resampling.LANCZOS)
        image.paste(logo, (left, 52), logo)
    draw = ImageDraw.Draw(image)

    # Small newspaper tagline and strong horizontal rule.
    draw.text((left, 171), "GLOBAL NEWS  •  SMART INSIGHTS  •  BIGGER PERSPECTIVE",
              font=font(17, bold=True), fill=INK)
    draw.line((left, 203, right, 203), fill=(170, 176, 179), width=2)

    # Orange section ribbon and seven-slide counter.
    label = {"AI": "ARTIFICIAL INTELLIGENCE", "Technology": "TECHNOLOGY",
             "Crypto": "CRYPTOCURRENCY", "Markets": "FINANCIAL MARKETS"}[category]
    ribbon_x, ribbon_y = left, 220
    ribbon_width = min(550, max(265, len(label) * 17 + 54))
    draw.polygon([(ribbon_x + 17, ribbon_y), (ribbon_x + ribbon_width, ribbon_y),
                  (ribbon_x + ribbon_width - 18, ribbon_y + 51),
                  (ribbon_x, ribbon_y + 51)], fill=ORANGE)
    draw.text((ribbon_x + 27, ribbon_y + 10), label,
              font=font(25, bold=True), fill=(255, 255, 255))
    draw.text((right, ribbon_y + 10), f"{index:02d}/{total:02d}",
              font=font(26, bold=True), fill=INK, anchor="ra")

    headline = story.get("title") or "News update"
    headline_face, headline_lines, headline_leading = _fit_text(
        draw, headline, 942, 305, 65, 31, bold=True)
    headline_end = _draw_lines(draw, headline_lines, left, 296,
                               headline_face, INK, headline_leading)

    summary, valid = summary_for_card(story)
    if not valid:
        raise ValueError("Cannot render a news card with an invalid summary")
    intro, details = _summary_parts(summary)
    intro_y = headline_end + 14
    # The lead paragraph gets up to 130px; fit it without shortening.
    intro_face, intro_lines, intro_leading = _fit_text(
        draw, intro, 930, 128, 28, 20)
    intro_end = _draw_lines(draw, intro_lines, left, intro_y,
                            intro_face, (54, 60, 67), intro_leading)

    # Clean KEY DETAILS heading and horizontal editorial rule.
    section_y = max(775, intro_end + 30)
    if section_y > 906:
        raise ValueError("Headline and intro exceed safe editorial layout area")
    draw.rounded_rectangle((left, section_y, left + 245, section_y + 52),
                           radius=22, fill=INK)
    draw.text((left + 26, section_y + 10), "KEY DETAILS",
              font=font(25, bold=True), fill=(255, 255, 255))
    draw.line((left + 265, section_y + 28, right, section_y + 28),
              fill=INK, width=2)

    # Bullet list is sourced exclusively from extracted article sentences.
    if not details or not any(d.strip() for d in details):
        details = [intro]
    details = [d for d in details if d.strip()]
    detail_text = " ".join(details)
    detail_top = section_y + 75
    detail_height = 1180 - detail_top
    # Wrapped prose remains fully source-derived, even for a one-sentence summary.
    detail_face, detail_lines, detail_leading = _fit_text(
        draw, detail_text, 875, detail_height, 29, 19)
    draw.ellipse((left + 2, detail_top + 5, left + 32, detail_top + 35), fill=CYAN)
    draw.text((left + 17, detail_top + 9), "•", font=font(20, bold=True),
              fill=(255, 255, 255), anchor="mt")
    _draw_lines(draw, detail_lines, left + 54, detail_top,
                detail_face, INK, detail_leading)

    # Fixed footer with source provenance, publication date, and swipe cue.
    draw.line((left, 1200, right, 1200), fill=INK, width=2)
    draw.text((left, 1216), "SOURCE:", font=font(18, bold=True), fill=INK)
    src = source_name(story.get("url", ""))
    src_face, src_lines, _ = _fit_text(draw, src, 530, 33, 21, 16, bold=True)
    if len(src_lines) != 1:
        raise ValueError("Source domain cannot fit in footer")
    draw.text((left + 110, 1214), src_lines[0], font=src_face, fill=CYAN)
    draw.text((left, 1252), f"PUBLISHED: {date_label.upper()}",
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
