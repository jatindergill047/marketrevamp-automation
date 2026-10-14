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
MIN_SUMMARY_WORDS = 30
MAX_SUMMARY_WORDS = 90


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
    for size in range(36, 19, -1):
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
    """Brighter electric-blue rings, directional rays and an understated navy base."""
    image = Image.new("RGB", (WIDTH, HEIGHT))
    base = ImageDraw.Draw(image)
    for y in range(HEIGHT):
        t = y / HEIGHT
        base.line([(0, y), (WIDTH, y)], fill=(
            int(4 + 3 * t), int(18 + 9 * t), int(43 + 21 * t)
        ))
    glow = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    g = ImageDraw.Draw(glow)
    cx, cy = 840, 435
    for radius in range(300, 95, -10):
        a = int(65 + (300 - radius) / 205 * 105)
        g.ellipse((cx-radius, cy-radius, cx+radius, cy+radius),
                  outline=(*accent, min(a, 210)), width=3)
    for radius in range(235, 140, -15):
        g.arc((cx-radius, cy-radius, cx+radius, cy+radius),
              288, 83, fill=(255, 171, 45, 170), width=5)
    for j in range(11):
        x = 710 + j * 38
        g.line([(x, 0), (x - 445, 760)], fill=(*accent, 75), width=2)
    soft = glow.filter(ImageFilter.GaussianBlur(20))
    image = Image.alpha_composite(image.convert("RGBA"), soft)
    image = Image.alpha_composite(image, glow)
    return image.convert("RGB")


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


def draw_card(story, index, total, date_label):
    """1080x1350 approved layout: one header row, headline higher, roomy details."""
    category = story_category(story)
    accent = COLORS[category]
    image = background(accent, index)
    draw = ImageDraw.Draw(image)

    if not LOGO.exists():
        raise FileNotFoundError("Missing marketrevamp_logo.png in the repository root")
    with Image.open(LOGO) as original_logo:
        logo = original_logo.convert("RGBA")
        logo.thumbnail((102, 102), Image.Resampling.LANCZOS)
        image.paste(logo, (42, 26), logo)

    # Header: logo LEFT, brief label, category and position all INSIDE the header.
    draw.text((151, 43), "MARKETREVAMP", font=font(32, bold=True), fill=WHITE)
    draw.text((152, 89), "AI  •  TECH  •  MARKETS  •  BLOCKCHAIN",
              font=font(15, bold=True), fill=MUTED)
    draw.line((524, 34, 524, 128), fill=(84, 131, 161), width=2)
    draw.text((549, 44), "TODAY'S", font=font(24, bold=True), fill=accent)
    draw.text((549, 75), "HEADLINE", font=font(24, bold=True), fill=accent)
    draw.rounded_rectangle((720, 40, 885, 113), radius=19, fill=accent)
    cat_size = 22 if len(category) >= 9 else 27
    draw.text((740, 61), category.upper(), font=font(cat_size, bold=True),
              fill=NAVY)
    draw.line((903, 39, 903, 116), fill=(84, 131, 161), width=2)
    draw.text((922, 60), f"{index:02d}/{total:02d}",
              font=font(27, bold=True), fill=WHITE)
    draw.line((41, 148, 1038, 148), fill=accent, width=3)

    # Headlines move upward immediately under the header.
    headline = story.get("title") or "News update"
    headline_font, lines, line_height = fit_headline(
        draw, headline, max_width=970, max_lines=7, max_height=485
    )
    y = 184
    headline_bottom_limit = 716
    if y + len(lines) * line_height > headline_bottom_limit:
        raise ValueError("Headline exceeds allocated headline region")
    for line_number, line in enumerate(lines):
        color = accent if line_number == 0 else WHITE
        draw.text((54, y), line, font=headline_font, fill=color)
        y += line_height

    # Larger KEY DETAILS panel and more readable body text.
    summary, valid_summary = summary_for_card(story)
    top, bottom = 750, 1174
    border = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    border_draw = ImageDraw.Draw(border)
    border_draw.rounded_rectangle((43, top, 1037, bottom), radius=25,
                                  outline=(*accent, 155), width=8)
    image = Image.alpha_composite(image.convert("RGBA"),
                                  border.filter(ImageFilter.GaussianBlur(13)))
    image = image.convert("RGB")
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((46, top, 1034, bottom), radius=25,
                           fill=(10, 29, 56), outline=accent, width=4)
    # Compact visual icon to leave most of the width for summary text.
    draw.rounded_rectangle((79, 896, 183, 1005), radius=15,
                           outline=accent, width=5)
    for ypos in (924, 945, 966):
        draw.line((101, ypos, 161, ypos), fill=accent, width=5)
    draw.line((215, 784, 215, 1140), fill=accent, width=2)
    draw.text((243, 778), "KEY DETAILS" if valid_summary else "REVIEW REQUIRED",
              font=font(31, bold=True), fill=accent)
    summary_face, summary_lines, summary_height = fit_summary(
        draw, summary, max_width=745, max_height=bottom - 861 - 26
    )
    for line_index, line in enumerate(summary_lines):
        draw.text((243, 861 + line_index * summary_height), line,
                  font=summary_face, fill=WHITE if valid_summary else MUTED)

    # Source, date and disclaimer remain inside the Instagram safe margin.
    draw.line((55, 1210, 1026, 1210), fill=(101, 159, 192), width=2)
    draw.text((57, 1228), "SOURCE", font=font(17, bold=True), fill=MUTED)
    src = source_name(story.get("url", ""))
    source_face = font(22, bold=True)
    if draw.textbbox((0, 0), src, font=source_face)[2] > 600:
        src = src[:42]
    draw.text((57, 1255), src, font=source_face, fill=WHITE)
    draw.text((1024, 1253), date_label.upper(), font=font(19, bold=True),
              fill=MUTED, anchor="ra")
    draw.text((57, 1312), "MARKETREVAMP  •  NEWS, NOT INVESTMENT ADVICE",
              font=font(16, bold=True), fill=MUTED)
    assert image.size == (1080, 1350)
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
        category = story_category(story)
        summary, valid = summary_for_card(story)
        print(f"Created {path} | {category} | Summary: {'draft_ready_for_review' if valid else 'REVIEW_REQUIRED'} | {story.get('title', '')}")
    print(f"Finished: {len(stories)} separate 1080x1350 images in {OUTPUT}/")
    print("Images are local files only. Nothing has been published or uploaded.")


if __name__ == "__main__":
    main()
