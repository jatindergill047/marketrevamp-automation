"""Download the pinned, OFL-licensed Playfair Display font for Pillow.

Only executes in image-generation or non-publishing CI workflows.
"""
from pathlib import Path
from urllib.request import Request, urlopen

FONT_DIR = Path("fonts")
FONT_FILE = FONT_DIR / "PlayfairDisplay[wght].ttf"
LICENSE_FILE = FONT_DIR / "OFL.txt"
GOOGLE_FONTS_COMMIT = "4a784ead99ba1557ad1780d2e287a5c8abc7ddd5"
BASE = (
    "https://raw.githubusercontent.com/google/fonts/"
    + GOOGLE_FONTS_COMMIT + "/ofl/playfairdisplay/"
)


def download(name, destination):
    req = Request(BASE + name, headers={"User-Agent": "MarketRevamp-font-setup/1.0"})
    with urlopen(req, timeout=45) as response:
        content = response.read()
    if not content:
        raise RuntimeError("Empty download: " + name)
    destination.write_bytes(content)


def prepare():
    FONT_DIR.mkdir(parents=True, exist_ok=True)
    if not FONT_FILE.is_file():
        download("PlayfairDisplay%5Bwght%5D.ttf", FONT_FILE)
    if not LICENSE_FILE.is_file():
        download("OFL.txt", LICENSE_FILE)
    data = FONT_FILE.read_bytes()
    if len(data) < 100_000 or data[:4] not in (b"\x00\x01\x00\x00", b"OTTO"):
        FONT_FILE.unlink(missing_ok=True)
        raise RuntimeError("Downloaded font is not a valid TrueType/OpenType font")
    if b"SIL OPEN FONT LICENSE" not in LICENSE_FILE.read_bytes().upper():
        raise RuntimeError("Playfair Display license document invalid")
    print("Playfair Display font and OFL license ready")


if __name__ == "__main__":
    prepare()
