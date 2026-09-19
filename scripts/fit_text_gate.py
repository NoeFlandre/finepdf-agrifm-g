"""Fit the text gate's threshold on the labelled documents (issue #25).

A document counts as positive when at least one of its images was labelled `keep`. The gate is
tuned for **recall of keep images**: a document it rejects is never fetched, so a miss here is
permanent. Precision is not the goal — the later stages handle that.
"""

from __future__ import annotations

import json
from pathlib import Path

from agrifm_g.domain.textgate import agronomy_score

LABELS = Path("data/labels/relevance_v1.jsonl")
LEXICON = Path("data/agronomy_lexicon.txt")
THRESHOLDS = (0.0, 0.001, 0.002, 0.003, 0.004, 0.005, 0.0075, 0.01, 0.015, 0.02, 0.03)


def lexicon() -> frozenset[str]:
    lines = LEXICON.read_text(encoding="utf-8").splitlines()
    return frozenset(line.strip() for line in lines if line.strip() and not line.startswith("#"))


def documents() -> list[dict]:
    """Every labelled document, with its score and how many keeps it holds."""
    keeps = {
        json.loads(line)["image_sha256"]
        for line in LABELS.read_text().splitlines()
        if line and json.loads(line)["label"] == "keep"
    }
    labelled = {
        json.loads(line)["image_sha256"] for line in LABELS.read_text().splitlines() if line
    }
    terms = lexicon()
    found = []
    for metadata in sorted(Path("out/label").rglob("metadata.jsonl")):
        stratum = metadata.parent.parent.name
        for line in metadata.read_text().splitlines():
            record = json.loads(line)
            shas = [image["sha256"] for image in record["images"]]
            if not any(sha in labelled for sha in shas):
                continue
            found.append(
                {
                    "stratum": stratum,
                    "score": agronomy_score(record["text"], terms),
                    "keeps": sum(sha in keeps for sha in shas),
                    "images": len(shas),
                }
            )
    return found


def main() -> int:
    docs = documents()
    total_keeps = sum(doc["keeps"] for doc in docs)
    total_images = sum(doc["images"] for doc in docs)
    print(f"{len(docs)} labelled documents, {total_images} images, {total_keeps} keeps\n")
    print(f"{'threshold':>10} {'docs kept':>10} {'fetch saved':>12} {'keep recall':>12}")
    for threshold in THRESHOLDS:
        passing = [doc for doc in docs if doc["score"] >= threshold]
        recall = sum(doc["keeps"] for doc in passing) / total_keeps if total_keeps else 1.0
        print(
            f"{threshold:>10.4f} {len(passing):>10} "
            f"{1 - len(passing) / len(docs):>11.0%} {recall:>11.0%}"
        )
    print("\nscores of documents holding a keep:")
    for doc in sorted((d for d in docs if d["keeps"]), key=lambda d: d["score"]):
        print(f"  {doc['score']:.4f}  ({doc['keeps']} keep(s), {doc['stratum']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
