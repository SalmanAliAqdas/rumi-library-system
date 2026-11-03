"""Download unmodified OFL fonts from Google Fonts, for local serving only."""

import re
from pathlib import Path
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parent.parent / "static" / "fonts"
FONTS = [
    ("Newsreader", "newsreader"),
    ("NotoNaskhArabic", "notonaskharabic"),
    ("NotoNastaliqUrdu", "notonastaliqurdu"),
]


def main():
    ROOT.mkdir(parents=True, exist_ok=True)
    for family, directory in FONTS:
        base = f"https://raw.githubusercontent.com/google/fonts/main/ofl/{directory}/"
        # Full TTF avoids Latin-only subset mistakes for Urdu and Arabic.
        from json import loads

        listing = loads(
            urlopen(f"https://api.github.com/repos/google/fonts/contents/ofl/{directory}", timeout=30).read()
        )
        filename = next(
            item["name"]
            for item in listing
            if re.match(r"[^/]+\[.*\]\.ttf$", item["name"]) and "Italic" not in item["name"]
        )
        from urllib.parse import quote

        (ROOT / f"{family}.ttf").write_bytes(urlopen(base + quote(filename), timeout=30).read())
        (ROOT / f"{family}-OFL.txt").write_bytes(urlopen(base + "OFL.txt", timeout=30).read())
        print(f"Downloaded {family} and OFL license")


if __name__ == "__main__":
    main()
