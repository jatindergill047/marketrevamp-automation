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
    """Draw category-specific 2D editorial line art in otherwise unused space.

    These are explicitly illustrative symbols, never photographs, claims,
    market-price charts, fake metrics, or generic loading-placeholder lines.
    Do not draw anything if the summary leaves insufficient room.
    """
    top = int(top) + 27
    bottom = 1174  # Footer begins at y=1200.
    height = bottom - top
    if height < 155:
        return False

    draw = ImageDraw.Draw(image)
    left, right = 67, 1013
    navy = (37, 70, 95)
    muted = (142, 177, 191)
    pale = (210, 226, 232)
    category = category if category in ("AI", "Technology", "Crypto", "Markets") else "Technology"

    # One modest section label, not a pretend additional news paragraph.
    draw.line((left, top, right, top), fill=(197, 208, 212), width=2)
    label = {"AI": "AI & INTELLIGENCE", "Technology": "TECHNOLOGY & DEVICES",
             "Crypto": "DIGITAL ASSETS", "Markets": "GLOBAL MARKETS"}[category]
    draw.text((left + 3, top + 13), label, font=_serif(19), fill=navy)
    draw.line((left + 330, top + 26, right, top + 26),
              fill=(214, 224, 226), width=1)

    # Restrict all illustrations to a rectangle strictly below the label
    # and above the source footer. Geometry scales for short empty spaces.
    art_top, art_bottom = top + 55, bottom - 9
    cx = 770
    cy = (art_top + art_bottom) // 2
    scale = min(1.0, (art_bottom - art_top) / 150)
    def point(x, y):
        return (round(cx + x * scale), round(cy + y * scale))
    def line(points, color=muted, width=3):
        draw.line([point(x, y) for x, y in points], fill=color,
                  width=max(1, round(width * scale)), joint="curve")
    def circle(x, y, radius, outline=muted, width=3, fill=None):
        a = point(x - radius, y - radius)
        b = point(x + radius, y + radius)
        draw.ellipse((*a, *b), outline=outline,
                     width=max(1, round(width * scale)), fill=fill)
    def rect(x0, y0, x1, y1, outline=muted, width=3, radius=0):
        coords = (*point(x0, y0), *point(x1, y1))
        if radius:
            draw.rounded_rectangle(coords, radius=max(1, round(radius * scale)),
                                   outline=outline, width=max(1, round(width * scale)))
        else:
            draw.rectangle(coords, outline=outline,
                           width=max(1, round(width * scale)))

    if category == "AI":
        # A neural graph: interconnected nodes and an abstract central chip.
        nodes = [(-105, -43), (-108, 38), (-40, -68), (-40, 65),
                 (53, -68), (55, 63), (113, -32), (111, 42)]
        for x, y in nodes:
            line([(x, y), (0, 0)], pale, 2)
        rect(-33, -30, 33, 30, navy, 3, 9)
        for x, y in nodes:
            circle(x, y, 8, CYAN if x < 0 else ORANGE, 3,
                   (249, 248, 245))
        circle(0, 0, 10, CYAN, 3)
    elif category == "Technology":
        # Smart-glasses / connected-device silhouette: recognizable and
        # relevant to device stories, without implying any real photograph.
        line([(-132, -12), (-105, -34), (-32, -34), (-15, -14),
              (15, -14), (32, -34), (105, -34), (132, -12)], navy, 4)
        rect(-107, -26, -22, 42, navy, 4, 18)
        rect(22, -26, 107, 42, navy, 4, 18)
        line([(-21, -7), (0, -15), (21, -7)], CYAN, 4)
        line([(-132, -12), (-149, 15)], muted, 3)
        line([(132, -12), (149, 15)], muted, 3)
        for x, y in [(-85, 55), (-55, 64), (58, 64), (87, 55)]:
            circle(x, y, 3, CYAN, 2, CYAN)
    elif category == "Crypto":
        # Abstract distributed ledger nodes; no fake price action.
        for x, y in [(-110, -45), (-110, 45), (105, -45), (105, 45)]:
            line([(x, y), (0, 0)], pale, 3)
            circle(x, y, 12, CYAN, 3)
        circle(0, 0, 62, navy, 4)
        circle(0, 0, 48, muted, 2)
        draw.text(point(0, -33), "₿", font=_serif(max(16, round(68 * scale))),
                  fill=ORANGE, anchor="mt")
    else:
        # Stylized financial exchange columns, intentionally without
        # axes, numbers or data points: decorative, not a market chart.
        for x, h in [(-120, 38), (-73, 72), (-26, 49),
                     (21, 91), (68, 62), (115, 80)]:
            rect(x - 13, 75 - h, x + 13, 75, pale, 2, 4)
            line([(x, 75 - h), (x, 75)], CYAN if x < 0 else ORANGE, 4)
        line([(-143, 78), (144, 78)], muted, 2)

    # The illustration never changes the story text or attribution.
    return True
