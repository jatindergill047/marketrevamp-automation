"""Download the pinned, OFL-licensed Open Sans font for Pillow.

Only executes in image-generation or non-publishing CI workflows.
"""
from pathlib import Path
from urllib.request import Request, urlopen

FONT_DIR = Path("fonts")
FONT_FILE = FONT_DIR / "OpenSans[wdth,wght].ttf"
LICENSE_FILE = FONT_DIR / "OFL.txt"
GOOGLE_FONTS_COMMIT = "main"
BASE = (
    "https://raw.githubusercontent.com/google/fonts/"
    + GOOGLE_FONTS_COMMIT + "/ofl/opensans/"
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
        download("OpenSans%5Bwdth%2Cwght%5D.ttf", FONT_FILE)
    if not LICENSE_FILE.is_file():
        download("OFL.txt", LICENSE_FILE)
    data = FONT_FILE.read_bytes()
    if len(data) < 100_000 or data[:4] not in (b"\x00\x01\x00\x00", b"OTTO"):
        FONT_FILE.unlink(missing_ok=True)
        raise RuntimeError("Downloaded font is not a valid TrueType/OpenType font")
    if b"SIL OPEN FONT LICENSE" not in LICENSE_FILE.read_bytes().upper():
        raise RuntimeError("Open Sans license document invalid")
    print("Open Sans font and OFL license ready")


if __name__ == "__main__":
    prepare()
