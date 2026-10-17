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


def illustration_topic(headline, category):
    """Select an editorial motif from the headline, without external APIs.

    Strong, specific phrases take precedence over the generic news category.
    An ambiguous headline falls back to the category's existing illustration.
    """
    import re
    title = re.sub(r"[^a-z0-9]+", " ", (headline or "").casefold())
    def mentions(*terms):
        return any(re.search(r"\b" + re.escape(t) + r"\b", title) for t in terms)
    if mentions("regulation", "regulator", "regulators", "lawmakers",
                "legislation", "policy", "lawsuit", "court", "ban",
                "antitrust", "compliance", "safety rules"):
        return "policy"
    if mentions("glasses", "smart glasses", "ray ban", "headset", "wearable"):
        return "glasses"
    if mentions("security", "hack", "hacked", "breach", "breached",
                "malware", "cyberattack", "vulnerability", "privacy"):
        return "security"
    if category == "AI" and mentions("model", "models", "launch", "released",
                                      "release", "inference", "llm", "agent"):
        return "chip"
    if category == "Technology" and mentions("phone", "smartphone", "iphone"):
        return "phone"
    return {"AI": "network", "Technology": "glasses",
            "Crypto": "ledger", "Markets": "market"}.get(category, "network")


def draw_editorial_illustration(image, top, index=1, category="AI", headline=""):
    """Draw centered, headline-aware 2D artwork only in available whitespace.

    Artwork contains no invented news facts, metrics or chart price history.
    It never covers the summary or the publication footer.
    """
    top = int(top) + 27
    bottom = 1174
    if bottom - top < 155:
        return False

    draw = ImageDraw.Draw(image)
    left, right = 67, 1013
    navy = (37, 70, 95)
    muted = (142, 177, 191)
    pale = (210, 226, 232)
    topic = illustration_topic(headline, category)

    # One fine divider instead of a redundant category label.
    draw.line((left, top, right, top), fill=(197, 208, 212), width=2)
    art_top, art_bottom = top + 20, bottom - 10
    cx, cy = 540, (art_top + art_bottom) // 2
    scale = min(1.25, (art_bottom - art_top) / 160)
    def point(x, y):
        return (round(cx + x * scale), round(cy + y * scale))
    def line(points, color=muted, width=3):
        draw.line([point(x, y) for x, y in points], fill=color,
                  width=max(1, round(width * scale)), joint="curve")
    def circle(x, y, radius, outline=muted, width=3, fill=None):
        a, b = point(x - radius, y - radius), point(x + radius, y + radius)
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

    if topic in ("network", "chip"):
        nodes = [(-105, -43), (-108, 38), (-40, -68), (-40, 65),
                 (53, -68), (55, 63), (113, -32), (111, 42)]
        for x, y in nodes:
            line([(x, y), (0, 0)], pale, 2)
        rect(-35, -31, 35, 31, navy, 3, 9)
        if topic == "chip":
            for y in (-20, 0, 20):
                line([(-47, y), (-35, y)], CYAN, 3)
                line([(35, y), (47, y)], ORANGE, 3)
            for x in (-20, 0, 20):
                line([(x, -43), (x, -31)], CYAN, 3)
                line([(x, 31), (x, 43)], ORANGE, 3)
            circle(0, 0, 13, CYAN, 3)
        else:
            circle(0, 0, 10, CYAN, 3)
        for x, y in nodes:
            circle(x, y, 8, CYAN if x < 0 else ORANGE, 3)
    elif topic == "glasses":
        line([(-132, -12), (-105, -34), (-32, -34), (-15, -14),
              (15, -14), (32, -34), (105, -34), (132, -12)], navy, 4)
        rect(-107, -26, -22, 42, navy, 4, 18)
        rect(22, -26, 107, 42, navy, 4, 18)
        line([(-21, -7), (0, -15), (21, -7)], CYAN, 4)
        line([(-132, -12), (-149, 15)], muted, 3)
        line([(132, -12), (149, 15)], muted, 3)
    elif topic == "security":
        # Stylized cybersecurity shield and keyhole.
        line([(0, -78), (88, -49), (82, 18), (60, 57),
              (0, 89), (-60, 57), (-82, 18), (-88, -49),
              (0, -78)], navy, 4)
        circle(0, -8, 19, CYAN, 4)
        line([(0, 11), (0, 47)], ORANGE, 5)
    elif topic == "policy":
        # Regulation / governance: document with a shield seal.
        rect(-69, -85, 64, 83, navy, 4, 8)
        for y in (-54, -29, -4):
            line([(-45, y), (37, y)], pale, 5)
        line([(-45, 23), (-9, 23)], pale, 5)
        circle(38, 42, 30, CYAN, 4)
        line([(24, 42), (34, 53), (53, 30)], ORANGE, 5)
    elif topic == "phone":
        rect(-57, -89, 57, 89, navy, 4, 17)
        rect(-42, -66, 42, 59, pale, 3, 6)
        circle(0, 73, 5, CYAN, 2)
    elif topic == "ledger":
        for x, y in [(-110, -45), (-110, 45), (105, -45), (105, 45)]:
            line([(x, y), (0, 0)], pale, 3)
            circle(x, y, 12, CYAN, 3)
        circle(0, 0, 62, navy, 4)
        circle(0, 0, 48, muted, 2)
        draw.text(point(0, -33), "B", font=_serif(max(16, round(68 * scale))),
                  fill=ORANGE, anchor="mt")
        line([(-9, -37), (-9, 40)], ORANGE, 2)
        line([(7, -37), (7, 40)], ORANGE, 2)
    else:
        # Abstract market bars, deliberately without axes, prices or dates.
        for x, h in [(-120, 38), (-73, 72), (-26, 49),
                     (21, 91), (68, 62), (115, 80)]:
            rect(x - 13, 75 - h, x + 13, 75, pale, 2, 4)
            line([(x, 75 - h), (x, 75)], CYAN if x < 0 else ORANGE, 4)
        line([(-143, 78), (144, 78)], muted, 2)
    return True
