"""MarketRevamp: create five branded 1080x1350 Instagram news cards.

Run: python image_generator.py
Input: news_results.json from news_collector.py
Output: instagram_images/slide_01.png ... slide_05.png
Requires: Pillow>=11.0,<13.0
"""

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

from PIL import Image, ImageDraw, ImageFont, ImageFilter

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


def font(size, bold=False):
    candidates = (
        ["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
         "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf"]
        if bold else
        ["/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
         "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf"]
    )
    for path in candidates:
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def wrap_lines(draw, text, face, max_width):
    words = re.sub(r"\s+", " ", str(text)).strip().split()
    lines = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if draw.textbbox((0, 0), candidate, font=face)[2] <= max_width:
            current = candidate
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def fit_headline(draw, text, max_width=902, max_lines=6, max_height=300):
    for size in range(75, 27, -2):
        face = font(size, bold=True)
        lines = wrap_lines(draw, text, face, max_width)
        line_height = size + 17

        if (
            len(lines) <= max_lines
            and len(lines) * line_height <= max_height
        ):
            return face, lines, line_height

    raise ValueError(
        f"Headline cannot fit without truncation: {text}"
    )


def background(accent, index):
    image = Image.new("RGB", (WIDTH, HEIGHT))
    draw = ImageDraw.Draw(image)
    for y in range(HEIGHT):
        t = y / HEIGHT
        draw.line([(0, y), (WIDTH, y)], fill=(
            int(6 + 4 * t), int(18 + 9 * t), int(38 + 15 * t)
        ))

    # Abstract editorial illustration: layered orbital rings and glowing sphere.
    overlay = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    cx, cy = 795, 435
    for radius in range(290, 95, -9):
        alpha = max(0, int(65 * (290 - radius) / 195))
        od.ellipse((cx-radius, cy-radius, cx+radius, cy+radius),
                   outline=(*accent, alpha), width=2)
    for radius in range(160, 15, -5):
        alpha = max(0, int(3 + (160-radius) / 160 * 8))
        od.ellipse((cx-radius, cy-radius, cx+radius, cy+radius),
                   fill=(*accent, alpha))
    for j in range(11):
        x = 680 + j * 31
        od.line([(x, 80), (x-340, 820)], fill=(*accent, 13), width=2)
    blur = overlay.filter(ImageFilter.GaussianBlur(12))
    image = Image.alpha_composite(image.convert("RGBA"), blur)
    image = Image.alpha_composite(image, overlay)
    return image.convert("RGB")


def source_name(url):
    host = urlparse(url or "").netloc.lower().removeprefix("www.")
    return host or "Source unavailable"


def draw_card(story, index, total, date_label):
    category = story.get("display_category") or story.get("category") or "Technology"
    if category not in COLORS:
        category = "Technology"
    accent = COLORS[category]
    image = background(accent, index)
    draw = ImageDraw.Draw(image)

    # Top brand bar: use the actual uploaded MarketRevamp logo, not a drawn imitation.
    if not LOGO.exists():
        raise FileNotFoundError("Missing marketrevamp_logo.png in the repository root")
    with Image.open(LOGO) as original_logo:
        logo = original_logo.convert("RGBA")
        logo.thumbnail((112, 112), Image.Resampling.LANCZOS)
        image.paste(logo, (65, 55), logo)
    draw.text((192, 76), "MARKETREVAMP", font=font(32, bold=True), fill=WHITE)
    draw.text((192, 126), "AI  •  TECH  •  MARKETS  •  BLOCKCHAIN",
              font=font(17, bold=True), fill=MUTED)
    draw.text((74, 177), "THE DAILY BRIEF", font=font(23, bold=True), fill=MUTED)
    draw.line((74, 219, 1006, 219), fill=(55, 77, 101), width=2)

    # Small category label and story number.
    draw.rounded_rectangle((74, 285, 325, 346), radius=19, fill=accent)
    draw.text((98, 301), category.upper(), font=font(24, bold=True), fill=NAVY)
    draw.text((823, 298), f"{index:02d} / {total:02d}",
              font=font(28, bold=True), fill=WHITE)

    draw.text((74, 395), "TODAY'S HEADLINE", font=font(24, bold=True), fill=accent)
    title = story.get("title") or "News update"
    headline_font, lines, line_height = fit_headline(
        draw, title, max_height=300
    )

    y = 465

    for line in lines:
        draw.text(
            (69, y),
            line,
            font=headline_font,
            fill=WHITE,
            stroke_width=0
        )
        y += line_height
    # Readable 40-60 word summary. Never invent facts from RSS headlines.
    summary = (story.get("verified_summary") or story.get("summary") or "").strip()
    valid_summary = 40 <= len(summary.split()) <= 60
    if not valid_summary:
        summary = "Verified 40–60 word summary pending. Review the full source article before publishing this slide."

    summary_top = 815
    draw.rounded_rectangle((70, summary_top, 1010, 1110), radius=24,
                           fill=(16, 35, 59), outline=(51, 79, 103), width=2)
    draw.text((100, summary_top + 22), "KEY DETAILS", font=font(27, bold=True), fill=accent)
    summary_size = 33
    while summary_size >= 23:
        summary_face = font(summary_size)
        summary_lines = wrap_lines(draw, summary, summary_face, 865)
        summary_line_height = summary_size + 12
        if len(summary_lines) * summary_line_height <= 202:
            break
        summary_size -= 1
    for i, line in enumerate(summary_lines):
        draw.text((100, summary_top + 79 + i * summary_line_height), line,
                  font=summary_face, fill=WHITE if valid_summary else MUTED)

    # Footer separated from headline, with publisher attribution.
    draw.line((74, 1135, 1006, 1135), fill=(55, 77, 101), width=2)
    draw.text((74, 1160), "SOURCE", font=font(19, bold=True), fill=MUTED)
    draw.text((74, 1194), source_name(story.get("url", "")),
              font=font(25, bold=True), fill=WHITE)
    draw.text((1005, 1194), date_label.upper(), font=font(20, bold=True),
              fill=MUTED, anchor="ra")
    draw.text((74, 1270), "MARKETREVAMP  •  NEWS, NOT INVESTMENT ADVICE",
              font=font(16, bold=True), fill=MUTED)
    return image


def main():
    if not LOGO.exists():
        raise SystemExit("Missing marketrevamp_logo.png. Upload the official logo to the repository root.")
    if not INPUT.exists():
        raise SystemExit("Missing news_results.json. Run news_collector.py first.")
    data = json.loads(INPUT.read_text(encoding="utf-8"))
    stories = data.get("selected_stories", [])
    if len(stories) != 5:
        raise SystemExit(f"Expected exactly 5 selected stories; found {len(stories)}. No images created.")

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
        print(f"Created {path} | {story.get('display_category', story.get('category', ''))} | {story.get('title', '')}")
    print(f"Finished: {len(stories)} separate 1080x1350 images in {OUTPUT}/")
    print("Images are local files only. Nothing has been published or uploaded.")


if __name__ == "__main__":
    main()
