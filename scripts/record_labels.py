"""Turn a compact labelling spec into `data/labels/relevance_v1.jsonl` (issue #24).

A spec is `{"stratum": ..., "build": ..., "sheets": ..., "labels": {index: "class"},
"keeps": {index: {...}}}`. Every index in the sheets must appear, so a forgotten image is an
error rather than a silent reject.
"""

from __future__ import annotations

import json
import sys
from datetime import UTC, datetime
from pathlib import Path

OUT = Path("data/labels/relevance_v1.jsonl")
POLICY_VERSION = 1
REJECT_CLASSES = {
    "icon",
    "diagram",
    "chart",
    "logo",
    "screenshot",
    "text_page",
    "signature",
    "portrait",
    "blank",
    "map",
    "microscopy",
    "unrelated",
}


def main(spec_path: str) -> int:
    spec = json.loads(Path(spec_path).read_text())
    index = json.loads((Path(spec["sheets"]) / "index.json").read_text())
    labels = {int(key): value for key, value in spec["labels"].items()}
    keeps = {int(key): value for key, value in spec.get("keeps", {}).items()}
    borderlines = {int(key): value for key, value in spec.get("borderlines", {}).items()}

    missing = set(map(int, index)) - set(labels) - set(keeps) - set(borderlines)
    if missing:
        raise SystemExit(f"unlabelled images: {sorted(missing)}")

    now = datetime.now(UTC).isoformat(timespec="seconds")
    lines = []
    for position, sha in sorted(index.items(), key=lambda item: int(item[0])):
        position = int(position)
        if position in keeps or position in borderlines:
            source = keeps.get(position) or borderlines[position]
            record = {
                "image_sha256": sha,
                "label": "keep" if position in keeps else "borderline",
                "class": source["class"],
                "family": source.get("family"),
                "species": source.get("species", ""),
                "note": source.get("note", ""),
            }
        else:
            klass = labels[position]
            if klass not in REJECT_CLASSES:
                raise SystemExit(f"unknown reject class {klass!r} at {position}")
            record = {
                "image_sha256": sha,
                "label": "reject",
                "class": klass,
                "family": None,
                "species": "",
                "note": "",
            }
        record |= {
            "stratum": spec["stratum"],
            "build": spec["build"],
            "policy_version": POLICY_VERSION,
            "labelled_at": now,
            "labelled_by": "claude-opus-5",
        }
        lines.append(json.dumps(record, sort_keys=True))

    OUT.parent.mkdir(parents=True, exist_ok=True)
    existing = OUT.read_text().splitlines() if OUT.exists() else []
    seen = {json.loads(line)["image_sha256"] for line in existing}
    fresh = [line for line in lines if json.loads(line)["image_sha256"] not in seen]
    OUT.write_text("".join(f"{line}\n" for line in existing + fresh), encoding="utf-8")
    print(f"{len(fresh)} new labels, {len(existing) + len(fresh)} total", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1]))
