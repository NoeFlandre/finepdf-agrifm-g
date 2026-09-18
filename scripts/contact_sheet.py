"""Render labelled contact sheets of a build, so images can be judged in batches (issue #24).

Each cell is captioned with the index the labeller refers to and the image's short hash.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw

CELL = 260
COLS = 6
PER_SHEET = 36


def images_of(build: Path) -> list[tuple[str, str, int, int]]:
    records = [
        json.loads(line)
        for line in (build / "metadata.jsonl").read_text(encoding="utf-8").splitlines()
        if line
    ]
    return [
        (image["path"], image["sha256"], image["width"], image["height"])
        for record in records
        for image in record["images"]
    ]


def sheet(build: Path, entries: list[tuple[str, str, int, int]], first: int, out: Path) -> None:
    rows = -(-len(entries) // COLS)
    canvas = Image.new("RGB", (COLS * CELL, rows * CELL), "white")
    draw = ImageDraw.Draw(canvas)
    for position, (path, sha, width, height) in enumerate(entries):
        picture = Image.open(build / path).convert("RGB")
        picture.thumbnail((CELL - 24, CELL - 28))
        x, y = (position % COLS) * CELL, (position // COLS) * CELL
        canvas.paste(picture, (x + 12, y + 26))
        draw.text((x + 6, y + 8), f"{first + position} {sha[:8]} {width}x{height}", fill="black")
        draw.rectangle([x, y, x + CELL - 2, y + CELL - 2], outline="#cccccc")
    canvas.save(out)


def main(build_dir: str, out_dir: str) -> int:
    build, out = Path(build_dir), Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    entries = images_of(build)
    index = {}
    for start in range(0, len(entries), PER_SHEET):
        batch = entries[start : start + PER_SHEET]
        sheet(build, batch, start, out / f"sheet_{start:04d}.png")
        index.update({start + offset: item[1] for offset, item in enumerate(batch)})
    (out / "index.json").write_text(json.dumps(index, indent=1), encoding="utf-8")
    print(f"{len(entries)} images across {-(-len(entries) // PER_SHEET)} sheets", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1], sys.argv[2]))
