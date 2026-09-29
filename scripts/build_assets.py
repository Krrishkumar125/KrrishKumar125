#!/usr/bin/env python3
"""Build README assets: embed subsetted Geist + Geist Mono into each SVG.

Reads assets/src/*.svg and writes assets/*.svg.
Each output carries only the glyphs it actually uses (a few KB per font),
so text renders in Geist wherever GitHub shows the image.
Missing fonts fall back to system fonts.

pip install fonttools brotli
python scripts/build_assets.py
"""
from __future__ import annotations

import base64
import io
import sys
from pathlib import Path
from xml.etree import ElementTree as ET

from fontTools import subset
from fontTools.ttLib import TTFont

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "assets" / "src"
OUT = ROOT / "assets"
FONT_DIR = ROOT / "scripts" / "fonts"

# CSS family name -> (filename prefix, substring the filename must not contain)
FAMILIES = {
    "Geist": ("Geist", "Mono"),
    "Geist Mono": ("GeistMono", None),
}


def find_font(prefix: str, exclude: str | None) -> Path | None:
    hits = [
        p for p in FONT_DIR.rglob("*.ttf")
        if p.name.startswith(prefix)
        and not (exclude and exclude in p.name)
    ]
    # Prefer the variable font so every weight is available.
    hits.sort(key=lambda p: ("Variable" not in p.name and "[" not in p.name, p.name))
    return hits[0] if hits else None


def used_text(svg: str) -> str:
    chars = {" "}
    for el in ET.fromstring(svg).iter():
        if el.tag.rsplit("}", 1)[-1] == "text":
            chars.update("".join(el.itertext()))
    return "".join(sorted(chars))


def subset_woff2(path: Path, text: str) -> str:
    font = TTFont(path)
    options = subset.Options()
    options.layout_features = ["*"]
    subsetter = subset.Subsetter(options)
    subsetter.populate(text=text)
    subsetter.subset(font)
    font.flavor = "woff2"
    buf = io.BytesIO()
    font.save(buf)
    return base64.b64encode(buf.getvalue()).decode("ascii")


def main() -> int:
    fonts = {family: find_font(*spec) for family, spec in FAMILIES.items()}
    for family, path in fonts.items():
        print(f"{family:<11} {path.name if path else 'not found, using system fallback'}")

    sources = sorted(SRC.glob("*.svg"))
    if not sources:
        print(f"No SVGs found in {SRC}", file=sys.stderr)
        return 1

    OUT.mkdir(parents=True, exist_ok=True)
    for src in sources:
        svg = src.read_text(encoding="utf-8")
        text = used_text(svg)
        faces = "".join(
            f'@font-face{{font-family:"{family}";font-weight:100 900;font-display:block;'
            f'src:url(data:font/woff2;base64,{subset_woff2(path, text)}) format("woff2")}}'
            for family, path in fonts.items()
            if path
        )
        out = svg.replace("<defs>", f"<defs><style>{faces}</style>", 1) if faces else svg
        (OUT / src.name).write_text(out, encoding="utf-8")
        print(f"built {src.name:<16} {len(out.encode()) / 1024:6.1f} KB")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
