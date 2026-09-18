"""Build the stratified sample the labelling pass needs (issue #24).

Uniform alone cannot measure recall at a ~2 % base rate, so this writes two manifests:

- `uniform`   — a plain seeded draw, which is what the true base rate is estimated from
- `candidate` — the documents whose text scores highest against the agronomy lexicon

Metrics are computed per stratum and reweighted; the base rate is never read off the
candidate slice.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from agrifm_g.adapters.finepdf import ParquetRowSource
from agrifm_g.domain.sampling import select_indices
from agrifm_g.pipeline import Manifest

LEXICON = Path("data/agronomy_lexicon.txt")
SEED = 20260918
UNIFORM_SIZE = 150
CANDIDATE_SIZE = 350
ROW_GROUPS = (0, 1, 2)


def lexicon() -> set[str]:
    lines = LEXICON.read_text(encoding="utf-8").splitlines()
    return {line.strip() for line in lines if line.strip() and not line.startswith("#")}


def score(text: str, terms: set[str]) -> float:
    """Share of a document's words that are agronomy terms. Length-invariant."""
    words = re.findall(r"[a-z]+", text.lower())
    if not words:
        return 0.0
    return sum(1 for word in words if word in terms) / len(words)


def main() -> int:
    terms = lexicon()
    rows: list[tuple[int, str, float]] = []
    for group in ROW_GROUPS:
        source = ParquetRowSource(row_group=group)
        window = source.rows(range(source.total()))
        offset = group * len(window)
        rows.extend(
            (offset + index, row.doc_id, score(row.text, terms)) for index, row in enumerate(window)
        )
        print(f"row group {group}: {len(window)} documents", file=sys.stderr)

    uniform_indices = select_indices(total=len(rows), size=UNIFORM_SIZE, seed=SEED)
    uniform = {rows[i][0] for i in uniform_indices}
    ranked = sorted(rows, key=lambda row: (-row[2], row[0]))
    candidate = [row for row in ranked if row[0] not in uniform][:CANDIDATE_SIZE]

    _write("uniform", [rows[i] for i in uniform_indices])
    _write("candidate", candidate)
    print(f"candidate score range: {candidate[-1][2]:.4f} – {candidate[0][2]:.4f}", file=sys.stderr)
    return 0


def _write(stratum: str, selected: list[tuple[int, str, float]]) -> None:
    manifest = Manifest(
        dataset="HuggingFaceFW/finepdfs",
        config="eng_Latn",
        split="train",
        seed=SEED,
        size=len(selected),
        indices=tuple(index % 1000 for index, _, _ in selected),
        doc_ids=tuple(doc_id for _, doc_id, _ in selected),
    )
    path = Path(f"data/label_manifest_{stratum}.json")
    path.write_text(f"{manifest.to_json()}\n", encoding="utf-8")
    scores = {doc_id: round(value, 5) for _, doc_id, value in selected}
    groups = {doc_id: index // 1000 for index, doc_id, _ in selected}
    Path(f"data/label_strata_{stratum}.json").write_text(
        json.dumps({"stratum": stratum, "scores": scores, "row_groups": groups}, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"wrote {path} with {len(selected)} documents", file=sys.stderr)


if __name__ == "__main__":
    raise SystemExit(main())
