"""Second-pass agreement check over an existing label set (issue #24).

`sample` renders a sheet of N already-labelled images in a shuffled order, without showing
their labels. `score` compares a second pass against the stored one.
"""

from __future__ import annotations

import json
import random
import sys
from pathlib import Path

from PIL import Image, ImageDraw

LABELS = Path("data/labels/relevance_v1.jsonl")
SAMPLE = Path("/private/tmp/claude-501/agreement_sample.json")
CELL = 260
COLS = 6


def labels() -> list[dict]:
    return [json.loads(line) for line in LABELS.read_text().splitlines() if line]


def sample(size: int, seed: int, out: Path) -> int:
    chosen = random.Random(seed).sample(labels(), size)
    paths = {}
    for record in chosen:
        build = Path(record["build"])
        for line in (build / "metadata.jsonl").read_text().splitlines():
            document = json.loads(line)
            for image in document["images"]:
                if image["sha256"] == record["image_sha256"]:
                    paths[record["image_sha256"]] = build / image["path"]
    order = [record["image_sha256"] for record in chosen]
    rows = -(-len(order) // COLS)
    canvas = Image.new("RGB", (COLS * CELL, rows * CELL), "white")
    draw = ImageDraw.Draw(canvas)
    for position, sha in enumerate(order):
        picture = Image.open(paths[sha]).convert("RGB")
        picture.thumbnail((CELL - 24, CELL - 28))
        x, y = (position % COLS) * CELL, (position // COLS) * CELL
        canvas.paste(picture, (x + 12, y + 26))
        draw.text((x + 6, y + 8), f"{position} {sha[:8]}", fill="black")
        draw.rectangle([x, y, x + CELL - 2, y + CELL - 2], outline="#cccccc")
    canvas.save(out / "agreement_sheet.png")
    SAMPLE.write_text(json.dumps(order, indent=1))
    print(f"{len(order)} images written to {out}/agreement_sheet.png", file=sys.stderr)
    return 0


def score(second_pass_path: str) -> int:
    order = json.loads(SAMPLE.read_text())
    second = json.loads(Path(second_pass_path).read_text())
    stored = {record["image_sha256"]: record for record in labels()}
    same_label = same_class = 0
    for position, sha in enumerate(order):
        first = stored[sha]
        again = second[str(position)]
        binary_first = "keep" if first["label"] == "keep" else first["label"]
        same_label += binary_first == again["label"]
        same_class += first["class"] == again["class"]
        if binary_first != again["label"] or first["class"] != again["class"]:
            print(
                f"  {position} {sha[:8]}: first={first['label']}/{first['class']} "
                f"second={again['label']}/{again['class']}"
            )
    total = len(order)
    print(f"label agreement: {same_label}/{total} = {same_label / total:.0%}")
    print(f"class agreement: {same_class}/{total} = {same_class / total:.0%}")
    return 0 if same_label / total >= 0.9 else 1


if __name__ == "__main__":
    if sys.argv[1] == "sample":
        raise SystemExit(sample(30, 4242, Path(sys.argv[2])))
    raise SystemExit(score(sys.argv[2]))
