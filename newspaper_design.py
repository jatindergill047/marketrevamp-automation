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
    """White archival paper, with intentional editorial texture at the edges.

    Content areas remain bright; artwork is original 2D Pillow geometry.
    """
    image = Image.new("RGB", (WIDTH, HEIGHT), PAPER)
    draw = ImageDraw.Draw(image)
    rng = random.Random(20261016 + index)

    # Reproducible fine-grain paper stock, never an external image.
    for _ in range(22000):
        x, y = rng.randrange(WIDTH), rng.randrange(HEIGHT)
        tone = rng.choice((230, 235, 240, 245))
        draw.point((x, y), fill=(tone, tone, min(255, tone + 1)))

    draw.rectangle((0, 0, WIDTH, 34), fill=(239, 238, 233))
    draw.rectangle((0, 1325, WIDTH, HEIGHT), fill=(238, 237, 232))
    for y in (32, 191, 1326):
        draw.line((0, y, WIDTH, y), fill=(203, 207, 208), width=1)
    for x in (22, 1058):
        draw.line((x, 36, x, 1324), fill=(219, 222, 223), width=1)

    # Decorative dot-matrix globe at the masthead edge.
    # This is abstract artwork, not geographic or financial data.
    for row in range(10):
        for col in range(18):
            u, v = (col - 8.5) / 9.2, (row - 4.5) / 5.3
            if u * u + v * v <= 1:
                x, y = 828 + col * 12, 52 + row * 12
                dot = 2 if (col + row) % 3 else 3
                draw.ellipse((x, y, x + dot, y + dot),
                             fill=(205, 216, 222))
    for k in range(3):
        draw.arc((815 + k * 8, 42 + k * 5, 1053 - k * 8, 172 - k * 5),
                 185, 345, fill=(217, 223, 224), width=1)

    # Subtle fine rules near the footer, but no tiny illegible text.
    draw.line((38, 1321, 1042, 1321), fill=(203, 209, 212), width=1)
    return image


def draw_editorial_illustration(image, top, index=1, category="AI"):
    """Add a premium 2D newspaper engraving ONLY in genuinely unused space.

    Top is the rendered summary panel's bottom edge. The drawing is skipped
    for long articles, and never overlaps the footer at y=1200.
    No simulated financial figures, charts with implied actual data, or API.
    """
    top = int(top) + 30
    bottom = 1174
    available = bottom - top
    if available < 155:
        return False

    draw = ImageDraw.Draw(image)
    left, right = 67, 1013
    muted = (174, 191, 198)
    soft = (213, 224, 229)
    draw.line((left, top, right, top), fill=(191, 201, 204), width=2)
    draw.text((left + 2, top + 13), "THE BIGGER PICTURE",
              font=_serif(19), fill=(67, 87, 102))
    draw.line((left + 280, top + 26, right, top + 26),
              fill=(211, 218, 221), width=1)

    center_y = top + 65 + max(0, (available - 145) // 2)
    center_x = 820
    radius = min(91, max(53, (available - 78) // 2))
    # Stylized globe engraving: concentric circles, meridians and parallels.
    draw.ellipse((center_x - radius, center_y - radius,
                  center_x + radius, center_y + radius),
                 outline=(144, 178, 192), width=3)
    for fraction in (.34, .68):
        rx = int(radius * fraction)
        draw.ellipse((center_x - rx, center_y - radius,
                      center_x + rx, center_y + radius),
                     outline=soft, width=2)
    for fraction in (.35, .70):
        ry = int(radius * fraction)
        draw.ellipse((center_x - radius, center_y - ry,
                      center_x + radius, center_y + ry),
                     outline=soft, width=2)
    draw.arc((center_x - radius - 11, center_y - radius - 11,
              center_x + radius + 11, center_y + radius + 11),
             205, 315, fill=CYAN, width=4)
    draw.arc((center_x - radius - 11, center_y - radius - 11,
              center_x + radius + 11, center_y + radius + 11),
             30, 87, fill=ORANGE, width=4)

    # A restrained newspaper column motif. Lines are deliberately decorative
    # and cannot be mistaken for fabricated reporting.
    col_x = left + 8
    col_y = top + 61
    max_y = min(bottom - 9, col_y + 115)
    lengths = (390, 480, 440, 465, 355)
    for i, width in enumerate(lengths):
        y = col_y + i * 21
        if y + 3 >= max_y:
            break
        draw.rounded_rectangle((col_x, y, col_x + width, y + 4),
                               radius=2, fill=soft)
    draw.rectangle((col_x, max_y + 2, col_x + 72, max_y + 6), fill=CYAN)
    return True
