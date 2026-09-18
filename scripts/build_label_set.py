"""Materialise the stratified label manifests into build directories (issue #24).

`Manifest` addresses one row group, while the label sample deliberately spans three, so this
drives the pipeline per row group and writes one build directory per (stratum, row group).
"""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

from agrifm_g.adapters.finepdf import ParquetRowSource
from agrifm_g.adapters.pdfsource import CachingPdfFetcher
from agrifm_g.pipeline import Manifest, build_dataset

CACHE = Path(".cache/pdfs")
OUT = Path("out/label")


def main(stratum: str) -> int:
    manifest = Manifest.from_json(
        json.loads(Path(f"data/label_manifest_{stratum}.json").read_text())
    )
    strata = json.loads(Path(f"data/label_strata_{stratum}.json").read_text())
    by_group: dict[int, list[tuple[int, str]]] = defaultdict(list)
    for index, doc_id in zip(manifest.indices, manifest.doc_ids, strict=True):
        by_group[strata["row_groups"][doc_id]].append((index, doc_id))

    fetcher = CachingPdfFetcher(cache_dir=CACHE)
    for group, entries in sorted(by_group.items()):
        out = OUT / stratum / f"g{group}"
        out.mkdir(parents=True, exist_ok=True)
        subset = Manifest(
            dataset=manifest.dataset,
            config=manifest.config,
            split=manifest.split,
            seed=manifest.seed,
            size=len(entries),
            indices=tuple(index for index, _ in entries),
            doc_ids=tuple(doc_id for _, doc_id in entries),
        )
        source = ParquetRowSource(row_group=group)
        records = build_dataset(subset, source, fetcher, out)
        images = sum(record.n_images for record in records)
        print(
            f"{stratum} g{group}: {len(records)}/{len(entries)} documents, {images} images",
            file=sys.stderr,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1]))
