"""R68: reusable carousel-style 2D artwork for review-only 9:16 Reels.

Original Pillow illustration motifs come from the seven-slide carousel design.
Render transparent per-scene PNGs; FFmpeg floats them gently above lower
karaoke subtitles. No generative API, news claims, uploading, or publication.
"""
from pathlib import Path
import re

from PIL import Image, ImageDraw

from newspaper_design import draw_editorial_illustration, illustration_topic

ARTWORK_SIZE = (860, 370)
ARTWORK_X = 110
ARTWORK_Y = 822
ARTWORK_ZONE = (ARTWORK_X, 814, ARTWORK_X + ARTWORK_SIZE[0], 1200)
ANIMATION_PX = 8
ANIMATION_SECONDS = 3.6
CAPTION_CENTER_Y = 1365
SUBTITLE_ZONE = (65, 1225, 1015, 1505)


def _visual_headline(headline):
    """Map common security synonyms to the existing carousel shield motif."""
    value = str(headline or "")
    if re.search(r"\b(?:cybersecurity|ransomware|phishing)\b", value, re.I):
        return "security " + value
    return value


def story_theme(story):
    """Reuse the seven-slide headline/category motif selector."""
    return illustration_topic(
        _visual_headline(story.get("headline", "")),
        str(story.get("category", "")),
    )


def render_artwork(story, output_path):
    """Make centered, transparent 2D artwork with the carousel's actual motif.

    The crop excludes the carousel's separator line and publication elements.
    Decorative backdrop is intentionally abstract and reports no quantities.
    """
    if not isinstance(story, dict) or not str(story.get("headline", "")).strip():
        raise ValueError("Artwork requires a story headline")
    category = str(story.get("category", "Technology"))
    headline = _visual_headline(story["headline"])
    canvas = Image.new("RGBA", (1080, 1350), (0, 0, 0, 0))
    if not draw_editorial_illustration(
        canvas, 745, category=category, headline=headline
    ):
        raise ValueError("Carousel illustration could not fit")
    # Extract only the transparent illustration—never the carousel's labels.
    motif = canvas.crop((190, 805, 890, 1165)).resize(
        (840, 360), Image.Resampling.LANCZOS
    )
    image = Image.new("RGBA", ARTWORK_SIZE, (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    # Thin, editorial graphic shapes match MarketRevamp's off-white paper.
    draw.ellipse((248, 12, 610, 358),
                 fill=(218, 232, 237, 68),
                 outline=(153, 183, 196, 118), width=2)
    draw.arc((128, 28, 730, 343), 20, 145,
             fill=(172, 32, 44, 133), width=3)
    draw.arc((128, 28, 730, 343), 196, 315,
             fill=(0, 158, 215, 133), width=3)
    draw.ellipse((95, 172, 106, 183), fill=(245, 127, 19, 210))
    draw.ellipse((750, 73, 761, 84), fill=(0, 158, 215, 210))
    image.alpha_composite(motif, (10, 0))
    if not image.getbbox():
        raise ValueError("Blank artwork")
    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    image.save(destination, optimize=True)
    return {"theme": story_theme(story), "path": str(destination),
            "width": ARTWORK_SIZE[0], "height": ARTWORK_SIZE[1],
            "animated": True}


def write_artwork_concat(folder, prefix, cuts, *, include_bookends=False):
    """Produce a time-aligned transparent PNG track for the seven news scenes."""
    directory = Path(folder)
    expected = 10 if include_bookends else 8
    if len(cuts) != expected or any(b <= a for a, b in zip(cuts, cuts[1:])):
        raise ValueError("Seven positive story durations required, plus optional hook and CTA")
    files = [directory / f"{prefix}_artwork_{index:02d}.png"
             for index in range(1, 8)]
    if include_bookends:
        files = ([directory / f"{prefix}_artwork_intro.png"] + files
                 + [directory / f"{prefix}_artwork_outro.png"])
    if any(not path.is_file() for path in files):
        raise FileNotFoundError("Missing Reel artwork frame")
    lines = ["ffconcat version 1.0"]
    for index, path in enumerate(files):
        lines.extend((f"file '{path.resolve()}'",
                      f"duration {cuts[index+1]-cuts[index]:.6f}"))
    lines.append(f"file '{files[-1].resolve()}'")
    target = directory / f"{prefix}_artwork.ffconcat"
    target.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return target


def overlay_filter(ass_path):
    """Motion affects artwork only, not logo, headlines or karaoke captions."""
    subtitles = Path(ass_path).resolve().as_posix()
    # Both image concat sources are sampled to 12 FPS before overlay.
    # Audio uses its separate unmodified, mastered source stream.
    y = (f"{ARTWORK_Y}+{ANIMATION_PX}*"
         f"sin(2*PI*t/{ANIMATION_SECONDS})")
    return (
        "[0:v]fps=12,format=yuv420p[base];"
        "[1:v]fps=12,format=rgba[art];"
        f"[base][art]overlay=x={ARTWORK_X}:y='{y}':"
        "eval=frame:shortest=1:format=auto,"
        f"ass={subtitles},format=yuv420p[v]"
    )


def composite_artwork_preview(background, artwork):
    """Static centered proof image, distinct from the animated MP4."""
    base = Image.open(background).convert("RGBA")
    overlay = Image.open(artwork).convert("RGBA")
    if base.size != (1080, 1920) or overlay.size != ARTWORK_SIZE:
        raise ValueError("Preview image dimensions invalid")
    base.alpha_composite(overlay, (ARTWORK_X, ARTWORK_Y))
    return base.convert("RGB")
