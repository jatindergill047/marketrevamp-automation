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
    """Quiet high-key newspaper stock, with decoration confined to margins.

    The central headline and details column remains clear for readability.
    """
    image = Image.new("RGB", (WIDTH, HEIGHT), PAPER)
    draw = ImageDraw.Draw(image)
    rng = random.Random(20261016 + index)

    # Paper fiber / ink speckles: visible at full resolution, never on top
    # of content as large decorative words.
    for _ in range(18000):
        x, y = rng.randrange(WIDTH), rng.randrange(HEIGHT)
        tone = rng.choice((226, 232, 239, 245))
        draw.point((x, y), fill=(tone, tone, min(255, tone + 1)))

    # Newspaper top and bottom bands, not behind article copy.
    draw.rectangle((0, 0, WIDTH, 34), fill=(239, 238, 233))
    draw.rectangle((0, 1325, WIDTH, HEIGHT), fill=(238, 237, 232))
    for y in (32, 191, 1330):
        draw.line((0, y, WIDTH, y), fill=(205, 207, 206), width=1)

    # Editorial microprint confined to a thin strip at the bottom edge.
    micro = "GLOBAL MARKETS  •  TECHNOLOGY  •  BUSINESS  •  CRYPTO  •  ECONOMY"
    draw.text((30, 1330), micro, font=_serif(11), fill=(150, 156, 159))

    # Very subtle vertical margins and clipped corner dot-grid accents.
    for x in (23, 1057):
        draw.line((x, 40, x, 1320), fill=(223, 224, 221), width=1)
    for row in range(8):
        for col in range(15):
            x, y = 830 + col * 15, 49 + row * 15
            draw.ellipse((x, y, x + 2, y + 2), fill=(218, 221, 222))

    # 2D financial chart watermark only at far right, kept behind a wash.
    pts = [(840 + i * 9, 1065 - (i * 9 + 14 * math.sin(i * .9)))
           for i in range(24)]
    draw.line(pts, fill=(217, 223, 226), width=2, joint="curve")
    for i in range(11):
        x = 865 + i * 18
        h = 22 + (i * 19) % 64
        draw.line((x, 1165 - h, x, 1173), fill=(223, 227, 228), width=2)
        draw.rectangle((x - 3, 1152 - h, x + 3, 1160 - h),
                       fill=(223, 227, 228))

    # Strong white reading surface, faintly translucent at the outer edges.
    wash = Image.new("RGBA", (WIDTH, HEIGHT), (255, 255, 255, 0))
    w = ImageDraw.Draw(wash)
    w.rounded_rectangle((44, 280, 1035, 1195), radius=18,
                        fill=(255, 255, 255, 208))
    wash = wash.filter(ImageFilter.GaussianBlur(16))
    return Image.alpha_composite(image.convert("RGBA"), wash).convert("RGB")
