"""Create 9:16 Reel frames without modifying original carousel slides."""

from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont, ImageOps

from reel_config import (
    CAPTION_BAND_BOTTOM,
    CAPTION_BAND_TOP,
    REEL_HEIGHT,
    REEL_WIDTH,
    SAFE_TOP,
)


def _font(size: int) -> ImageFont.ImageFont:
    """Choose an available bold font, falling back to Pillow's default."""
    for candidate in (
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf",
        "DejaVuSans-Bold.ttf",
    ):
        try:
            return ImageFont.truetype(candidate, size)
        except OSError:
            continue
    return ImageFont.load_default()


def compose(slide_path: str | Path, index: int, out_path: str | Path) -> Path:
    """Place an unaltered slide over a dark blurred 9:16 background."""
    if not 1 <= index <= 7:
        raise ValueError("Slide index must be between 1 and 7")
    source = Path(slide_path)
    destination = Path(out_path)
    with Image.open(source) as original:
        slide = ImageOps.exif_transpose(original).convert("RGB")
    background = ImageOps.fit(slide, (REEL_WIDTH, REEL_HEIGHT), method=Image.Resampling.LANCZOS)
    background = background.filter(ImageFilter.GaussianBlur(30))
    background = ImageEnhance.Brightness(background).enhance(0.6)
    foreground_height = round(slide.height * REEL_WIDTH / slide.width)
    if SAFE_TOP + foreground_height > CAPTION_BAND_TOP:
        raise ValueError("Slide would overlap the caption band")
    foreground = slide.resize((REEL_WIDTH, foreground_height), Image.Resampling.LANCZOS)
    background.paste(foreground, (0, SAFE_TOP))
    overlay = Image.new("RGBA", (REEL_WIDTH, REEL_HEIGHT), (0, 0, 0, 0))
    drawing = ImageDraw.Draw(overlay)
    drawing.rectangle((0, CAPTION_BAND_TOP, REEL_WIDTH, CAPTION_BAND_BOTTOM), fill=(0, 0, 0, 175))
    drawing.text((54, 68), "MARKETREVAMP", fill="white", font=_font(48), stroke_width=1, stroke_fill="black")
    counter = f"{index:02d}/07"
    font = _font(38)
    bbox = drawing.textbbox((0, 0), counter, font=font)
    drawing.text((REEL_WIDTH - 48 - (bbox[2] - bbox[0]), REEL_HEIGHT - 85), counter, fill="white", font=font)
    final = Image.alpha_composite(background.convert("RGBA"), overlay).convert("RGB")
    destination.parent.mkdir(parents=True, exist_ok=True)
    final.save(destination, format="PNG")
    return destination
