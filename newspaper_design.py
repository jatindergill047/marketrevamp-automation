"""MarketRevamp white newspaper editorial design. All graphics are 2D Pillow drawings.

No AI image service, paid API, downloaded photographs, or 3D rendering.
All decorative microprint is generic and intentionally low-contrast.
"""
import math
import random
from PIL import Image, ImageDraw, ImageFont, ImageFilter

WIDTH, HEIGHT = 1080, 1350
PAPER = (249, 248, 245)
INK = (5, 29, 61)
CYAN = (0, 158, 215)
ORANGE = (245, 127, 19)
LIGHT = (225, 226, 224)
FAINT = (235, 234, 231)


def _serif(size):
    # DejaVu is installed by Ubuntu runners; the editorial art is optional
    # decoration, so use Pillow's default if a system serif is unavailable.
    try:
        return ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf", size)
    except OSError:
        return ImageFont.load_default()


def newspaper_background(index=1):
    """Draw a subtle newspaper-paper backdrop with clean central text space."""
    image = Image.new("RGB", (WIDTH, HEIGHT), PAPER)
    draw = ImageDraw.Draw(image)
    rng = random.Random(20261016 + index)

    # Paper grain: fixed-seed for reproducible builds, no external images.
    for _ in range(15500):
        x, y = rng.randrange(WIDTH), rng.randrange(HEIGHT)
        shade = rng.choice((232, 237, 242, 246))
        draw.point((x, y), fill=(shade, shade, max(225, shade - 2)))

    # Faint newspaper columns and rules live in the page margins.
    for x in (22, 180, 370, 720, 900, 1055):
        draw.line((x, 0, x, HEIGHT), fill=(239, 238, 235), width=1)
    for y in (32, 145, 880, 1190, 1332):
        draw.line((0, y, WIDTH, y), fill=(231, 230, 227), width=1)

    headings = (
        ("GLOBAL MARKETS", (18, 4), 52),
        ("TECHNOLOGY", (24, 1050), 38),
        ("ECONOMY", (765, 1070), 38),
        ("BUSINESS", (835, 900), 33),
    )
    for text, point, size in headings:
        draw.text(point, text, font=_serif(size), fill=(220, 220, 218))

    micro = ("MARKET INSIGHTS  •  GLOBAL ECONOMY  •  TECHNOLOGY  •  "
             "BUSINESS AND FINANCE  •  INDEPENDENT NEWS ROUNDUP")
    tiny = _serif(12)
    for y in (91, 108, 125, 1120, 1137, 1154):
        draw.text((20, y), micro, font=tiny, fill=(224, 223, 220))

    # Faint halftone world motif: two latitude ellipses and dotted longitude.
    for lat in range(-2, 3):
        draw.arc((610, 4 + lat * 14, 1070, 215 + lat * 14),
                 185, 350, fill=(225, 226, 225), width=1)
    for row in range(10):
        for col in range(21):
            x, y = 700 + col * 16, 36 + row * 15
            if ((col - 10) / 12) ** 2 + ((row - 4) / 6) ** 2 < 1:
                draw.ellipse((x, y, x + 2, y + 2), fill=(220, 220, 218))

    # A restrained 2D market line, intentionally behind the whitewash.
    pts = [(630 + i * 17, 930 - (i * 11 + 32 * math.sin(i * .8)))
           for i in range(25)]
    draw.line(pts, fill=(214, 220, 222), width=3, joint="curve")
    for x, y in pts[::4]:
        draw.ellipse((x - 3, y - 3, x + 3, y + 3), fill=(211, 215, 216))
    for i in range(18):
        x = 710 + i * 19
        high = 20 + (i * 23) % 85
        draw.line((x, 1095 - high, x, 1102), fill=(215, 218, 219), width=2)
        draw.rectangle((x - 4, 1080 - high, x + 4, 1090 - high),
                       fill=(220, 223, 223))

    # A broad white wash keeps headline and article copy readable.
    wash = Image.new("RGBA", (WIDTH, HEIGHT), (255, 255, 255, 0))
    w = ImageDraw.Draw(wash)
    w.rounded_rectangle((44, 185, 1037, 1210), radius=30,
                        fill=(255, 255, 255, 183))
    wash = wash.filter(ImageFilter.GaussianBlur(30))
    return Image.alpha_composite(image.convert("RGBA"), wash).convert("RGB")
