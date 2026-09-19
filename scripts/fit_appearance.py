"""Measure the labelled images and report how the appearance rules perform (issue #26).

The rules may only drop what they are nearly certain about, so the number that matters is the
precision of the *reject* decision: of the images these rules throw away, how many were
labelled reject? Recall of keeps is reported alongside — a keep dropped here is lost for good.
"""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import asdict
from pathlib import Path

from agrifm_g.adapters.appearance import measure
from agrifm_g.domain.appearance import rejection_rule

LABELS = Path("data/labels/relevance_v1.jsonl")
CACHE = Path("data/labels/appearance_metrics.json")


def image_paths() -> dict[str, Path]:
    found: dict[str, Path] = {}
    for metadata in Path("out/label").rglob("metadata.jsonl"):
        for line in metadata.read_text().splitlines():
            record = json.loads(line)
            for image in record["images"]:
                found.setdefault(image["sha256"], metadata.parent / image["path"])
    return found


def metrics_for(labels: list[dict]) -> dict[str, dict]:
    cached = json.loads(CACHE.read_text()) if CACHE.exists() else {}
    paths = image_paths()
    for label in labels:
        sha = label["image_sha256"]
        if sha in cached or sha not in paths:
            continue
        cached[sha] = asdict(measure(paths[sha].read_bytes()))
    CACHE.write_text(json.dumps(cached, indent=0, sort_keys=True))
    return cached


def classify(labels: list[dict], measured: dict[str, dict]) -> tuple[Counter, Counter, int, int]:
    """Split the labelled images into correct drops, wrong drops and survivors."""
    from agrifm_g.domain.appearance import ImageMetrics

    dropped_true: Counter = Counter()
    dropped_false: Counter = Counter()
    kept_keep = kept_reject = 0
    for label in labels:
        raw = measured.get(label["image_sha256"])
        if raw is None:
            continue
        rule = rejection_rule(ImageMetrics(**raw))
        is_keep = label["label"] == "keep"
        if rule is None:
            kept_keep += is_keep
            kept_reject += not is_keep
        elif is_keep:
            dropped_false[rule.value] += 1
        else:
            dropped_true[rule.value] += 1
    return dropped_true, dropped_false, kept_keep, kept_reject


def report(dropped_true: Counter, dropped_false: Counter, kept_keep: int, kept_reject: int) -> None:
    dropped = sum(dropped_true.values()) + sum(dropped_false.values())
    total = dropped + kept_keep + kept_reject
    precision = sum(dropped_true.values()) / dropped if dropped else 1.0
    keeps = kept_keep + sum(dropped_false.values())
    print(f"{total} labelled images measured")
    print(f"dropped: {dropped} ({dropped / total:.1%} of everything)")
    print(f"reject precision: {sum(dropped_true.values())}/{dropped} = {precision:.1%}")
    print(f"keeps surviving: {kept_keep}/{keeps} = {kept_keep / keeps:.0%}")
    print(f"survivors: {kept_keep + kept_reject}, of which {kept_keep} are keeps")
    print("\ncorrect drops by rule:")
    for rule, count in dropped_true.most_common():
        print(f"  {rule:16s} {count:4d}")
    if dropped_false:
        print("\nKEEPS WRONGLY DROPPED:")
        for rule, count in dropped_false.most_common():
            print(f"  {rule:16s} {count:4d}")


def main() -> int:
    labels = [json.loads(line) for line in LABELS.read_text().splitlines() if line]
    report(*classify(labels, metrics_for(labels)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
