"""Summarise the label set: counts per stratum, class mix, and the reweighted base rate.

The candidate stratum is deliberately over-sampled, so a naive rate over all labels would be
meaningless. The true rate is estimated from the uniform stratum alone; the candidate stratum
exists to supply positives, not to estimate prevalence.
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

LABELS = Path("data/labels/relevance_v1.jsonl")


def load() -> list[dict]:
    return [json.loads(line) for line in LABELS.read_text().splitlines() if line]


def main() -> int:
    labels = load()
    print(f"{len(labels)} labelled images\n")
    for stratum in sorted({label["stratum"] for label in labels}):
        subset = [label for label in labels if label["stratum"] == stratum]
        keeps = [label for label in subset if label["label"] == "keep"]
        rate = len(keeps) / len(subset)
        print(f"{stratum}: {len(subset)} images, {len(keeps)} keep ({rate:.1%})")
        if keeps:
            families = Counter(keep["family"] for keep in keeps)
            print(f"  families: {dict(sorted(families.items(), key=lambda i: str(i[0])))}")
            print(f"  classes:  {dict(Counter(keep['class'] for keep in keeps))}")
    uniform = [label for label in labels if label["stratum"] == "uniform"]
    if uniform:
        keeps = sum(1 for label in uniform if label["label"] == "keep")
        rate = keeps / len(uniform)
        print(f"\nbase rate (uniform stratum only): {keeps}/{len(uniform)} = {rate:.2%}")
    rejects = Counter(label["class"] for label in labels if label["label"] == "reject")
    print("\nreject classes:")
    for name, count in rejects.most_common():
        print(f"  {name:12s} {count:4d}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
