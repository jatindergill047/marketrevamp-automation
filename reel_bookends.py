"""R70 short spoken hook and follow call-to-action for review-only Reels.

One uninterrupted neural narration contains intro, seven source-linked stories,
and outro. No scripts, dates, claims, or publishing approvals are generated.
"""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from reel_r51_design import CAPTION_DARK, PAPER, SUBTITLE_BOX

HOOK_LINE = "You're watching MarketRevamp. Here are today's top stories in AI, tech, crypto, and markets."
FOLLOW_LINE = "Follow MarketRevamp for quick, clear updates. Stay informed."
MAX_DURATION_SECONDS = 90.0
TOTAL_SEGMENTS = 9
STORY_COUNT = 7
_FONT_REG = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
_FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
_RED = (172, 32, 44)
_INK = (16, 25, 38)
_MUTED = (88, 98, 109)


def narration_segments(stories):
    """Return nine exact spoken segments, including seven unchanged stories."""
    if not isinstance(stories, list) or len(stories) != STORY_COUNT:
        raise ValueError("Hooked Reel requires seven stories")
    result = [{"narration_text": HOOK_LINE, "role": "intro"}]
    for story in stories:
        text = story.get("narration_text") if isinstance(story, dict) else None
        if not isinstance(text, str) or not text.strip():
            raise ValueError("Every story needs sourced narration")
        result.append({"narration_text": text, "role": "story"})
    result.append({"narration_text": FOLLOW_LINE, "role": "outro"})
    return result


def joined_narration(segments):
    if len(segments) != TOTAL_SEGMENTS:
        raise ValueError("Expected intro, seven stories and outro")
    return " ".join(item["narration_text"] for item in segments)


def build_bookends(logo, output_dir, prefix):
    """Render restrained visual cards matching the approved R68 Reel style."""
    if not isinstance(logo, Image.Image):
        raise ValueError("Official MarketRevamp logo is required")
    folder = Path(output_dir)
    folder.mkdir(parents=True, exist_ok=True)
    frames = []
    for role in ("intro", "outro"):
        image = Image.new("RGB", (1080, 1920), PAPER)
        draw = ImageDraw.Draw(image)
        draw.rectangle((0, 0, 1080, 16), fill=_RED)
        image.paste(logo, (70, 74))
        draw.text((73, 229), "MARKETREVAMP  /  THE DAILY BRIEF",
                  font=ImageFont.truetype(_FONT_BOLD, 24), fill=_MUTED)
        draw.line((72, 336, 1007, 336), fill=_RED, width=3)
        if role == "intro":
            headline = "TODAY'S TOP STORIES"
            supporting = "AI   /   TECHNOLOGY   /   CRYPTO   /   MARKETS"
            callout = "YOUR DAILY NEWS BRIEF"
        else:
            headline = "STAY INFORMED."
            supporting = "FOLLOW MARKETREVAMP"
            callout = "MORE CLEAR, QUICK UPDATES"
        face = ImageFont.truetype(_FONT_BOLD, 67 if role == "intro" else 76)
        draw.text((72, 505), headline, font=face, fill=_INK)
        draw.text((74, 665), supporting,
                  font=ImageFont.truetype(_FONT_BOLD, 29), fill=_RED)
        # Restrained original 2D geometry, echoing carousel illustration motifs.
        for x, y in ((275, 905), (535, 855), (795, 905), (535, 1080)):
            draw.ellipse((x-24, y-24, x+24, y+24),
                         fill=(225, 233, 236), outline=(0, 158, 215), width=4)
        draw.line([(275, 905), (535, 855), (795, 905)],
                  fill=(142, 177, 191), width=5)
        draw.line([(275, 905), (535, 1080), (795, 905)],
                  fill=(172, 32, 44), width=4)
        draw.rounded_rectangle(SUBTITLE_BOX, radius=26, fill=CAPTION_DARK)
        draw.line((72, 1605, 1007, 1605), fill=(216, 216, 215), width=3)
        draw.text((72, 1650), callout,
                  font=ImageFont.truetype(_FONT_BOLD, 26), fill=_INK)
        draw.text((72, 1780), "Market news • Not financial advice",
                  font=ImageFont.truetype(_FONT_REG, 23), fill=_MUTED)
        draw.line((72, 1852, 1008, 1852), fill=_RED, width=5)
        path = folder / f"{prefix}_{role}.png"
        image.save(path, optimize=True)
        # The original 2D motif track is intentionally blank on intro/outro.
        Image.new("RGBA", (860, 370), (0, 0, 0, 0)).save(
            folder / f"{prefix}_artwork_{role}.png")
        frames.append(path)
    return frames


def validate_bookend_timing(cuts):
    """Catch missing hook, CTA, story drift or overly long Reel."""
    if len(cuts) != TOTAL_SEGMENTS + 1:
        raise ValueError("Hooked Reel requires nine segment starts and one end")
    durations = [b-a for a, b in zip(cuts, cuts[1:])]
    if not 2.2 <= durations[0] <= 8:
        raise ValueError("Intro hook timing outside expected bounds")
    if not 2.0 <= durations[-1] <= 8:
        raise ValueError("Follow outro timing outside expected bounds")
    if any(length < 4 for length in durations[1:-1]):
        raise ValueError("A source-linked story was cut too short")
    if cuts[-1] > MAX_DURATION_SECONDS:
        raise ValueError("Hook and CTA Reel exceeds 90 seconds")
    return {"intro_seconds": round(durations[0], 2),
            "outro_seconds": round(durations[-1], 2),
            "story_count": STORY_COUNT, "presentation_segments": TOTAL_SEGMENTS}
