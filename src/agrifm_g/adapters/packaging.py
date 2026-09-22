"""Turn a build directory into a publishable dataset: parquet shards, card, stats."""

from __future__ import annotations

import json
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from agrifm_g.domain.agriculture import AgricultureSplit
from agrifm_g.domain.card import render_card
from agrifm_g.domain.dedup import deduplicate
from agrifm_g.domain.records import DocumentRecord
from agrifm_g.domain.rows import image_rows
from agrifm_g.domain.stats import build_stats

if TYPE_CHECKING:
    from datasets import Features

SHARD_TARGET_BYTES = 300 * 1024 * 1024
DATA_DIR = "data"
STATS_FILE = "stats.json"
CARD_FILE = "README.md"


@dataclass(frozen=True, slots=True)
class Package:
    """What was produced, so the caller can report it without re-reading the disk."""

    directory: Path
    n_rows: int
    n_shards: int
    stats: dict


def features() -> Features:
    """The declared schema; `Image()` is what makes the Hub viewer render thumbnails."""
    from datasets import Features, Image, Value

    return Features(
        {
            "image": Image(),
            "doc_id": Value("string"),
            "agriculture_split": Value("string"),
            "page": Value("int32"),
            "image_index": Value("int32"),
            "width": Value("int32"),
            "height": Value("int32"),
            "image_sha256": Value("string"),
            "image_path": Value("string"),
            "n_colours": Value("int32"),
            "edge_density": Value("float32"),
            "caption": Value("string"),
            "source_url": Value("string"),
            "pdf_sha256": Value("string"),
            "text": Value("string"),
            "n_images_in_doc": Value("int32"),
            "extraction_version": Value("int32"),
        }
    )


def package_dataset(
    build_dir: Path,
    out_dir: Path,
    *,
    repo_id: str,
    records: Sequence[DocumentRecord],
    sampled: int,
    seed: int,
    source_shards: int = 1,
    text_gated: int = 0,
    ambiguous: int = 0,
) -> Package:
    """Deduplicate, flatten to rows, and write the two agriculture split families."""
    kept, dropped = deduplicate(records)
    rows = [_with_image_bytes(build_dir, row) for row in image_rows(kept)]
    rows_by_split = {split.value: [] for split in AgricultureSplit}
    for row in rows:
        split = row["agriculture_split"]
        if split not in rows_by_split:
            raise ValueError(f"record has no valid agriculture split: {split!r}")
        rows_by_split[split].append(row)
    stats = build_stats(
        kept,
        sampled=sampled,
        dropped=dropped,
        seed=seed,
        source_shards=source_shards,
        text_gated=text_gated,
        ambiguous=ambiguous,
    )
    n_shards = _write_parquet(out_dir, rows_by_split)
    (out_dir / STATS_FILE).write_text(f"{json.dumps(stats, indent=2, sort_keys=True)}\n")
    (out_dir / CARD_FILE).write_text(
        render_card(repo_id=repo_id, stats=stats, n_rows=len(rows), n_shards=n_shards),
        encoding="utf-8",
    )
    return Package(directory=out_dir, n_rows=len(rows), n_shards=n_shards, stats=stats)


def _with_image_bytes(build_dir: Path, row: dict) -> dict:
    payload = (build_dir / row["image_path"]).read_bytes()
    return {**row, "image": {"path": row["image_path"], "bytes": payload}}


def _write_parquet(out_dir: Path, rows_by_split: dict[str, list[dict]]) -> int:
    from datasets import Dataset

    data_dir = out_dir / DATA_DIR
    data_dir.mkdir(parents=True, exist_ok=True)
    for stale in data_dir.glob("*.parquet"):
        stale.unlink()
    total_shards = 0
    for split, rows in rows_by_split.items():
        schema = features()
        if rows:
            dataset = Dataset.from_list(rows, features=schema)
        else:
            _write_empty_parquet(data_dir / f"{split}-00000-of-00001.parquet", schema)
            total_shards += 1
            continue
        n_shards = max(1, -(-dataset.data.nbytes // SHARD_TARGET_BYTES))
        for index in range(n_shards):
            shard = dataset.shard(num_shards=n_shards, index=index, contiguous=True)
            shard.to_parquet(data_dir / f"{split}-{index:05d}-of-{n_shards:05d}.parquet")
        total_shards += n_shards
    return total_shards


def _write_empty_parquet(path: Path, schema: Features) -> None:
    """Write an empty split without triggering Datasets' zero-row Image estimator bug."""
    import pyarrow as pa
    import pyarrow.parquet as pq

    pq.write_table(pa.Table.from_pylist([], schema=schema.arrow_schema), path)
