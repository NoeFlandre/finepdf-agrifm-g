"""Build and package a bounded multi-row-group FinePDF sample."""

from __future__ import annotations

import argparse
import shutil
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from agrifm_g.adapters.finepdf import ParquetRowSource
from agrifm_g.adapters.lexicon import load_lexicon, load_phenotype_lexicon
from agrifm_g.adapters.packaging import package_dataset
from agrifm_g.adapters.pdfsource import CachingPdfFetcher
from agrifm_g.adapters.storage import existing_files, read_records, record_to_json
from agrifm_g.domain.records import DocumentRecord
from agrifm_g.domain.textgate import DEFAULT_THRESHOLD, agronomy_score, passes_gate
from agrifm_g.pipeline import DEFAULT_WORKERS, Manifest, build_with_outcome

DEFAULT_REPO = "NoeFlandre/finepdf-agrifm-g"
DEFAULT_SHARDS = tuple(range(30))
DEFAULT_ROW_GROUPS = (0,)
DEFAULT_SEED = 20260918


@dataclass(frozen=True, slots=True)
class GroupRef:
    """One sampling window: a row group inside a shard.

    Spreading a build across shards rather than across row groups of a single shard is what
    makes the sample less of an accident of one crawl segment.
    """

    shard: int
    row_group: int

    @property
    def shard_name(self) -> str:
        return f"000_{self.shard:05d}.parquet"

    @property
    def slug(self) -> str:
        return f"s{self.shard:05d}g{self.row_group}"

    def source(self) -> ParquetRowSource:
        return ParquetRowSource(shard=self.shard_name, row_group=self.row_group)


def group_refs(shards: Sequence[int], row_groups: Sequence[int]) -> tuple[GroupRef, ...]:
    """Every row group of every shard, in a stable order."""
    return tuple(
        GroupRef(shard=shard, row_group=row_group) for shard in shards for row_group in row_groups
    )


def merge_builds(group_dirs: Sequence[Path], out_dir: Path) -> list[DocumentRecord]:
    """Move independently built row-group directories into one dataset directory."""
    if out_dir.exists() and any(out_dir.iterdir()):
        raise ValueError(f"refusing to merge into a non-empty directory: {out_dir}")
    out_dir.mkdir(parents=True, exist_ok=True)

    records: list[DocumentRecord] = []
    seen: set[str] = set()
    for group_dir in group_dirs:
        for record in read_records(group_dir):
            if record.doc_id in seen:
                raise ValueError(f"duplicate document across row groups: {record.doc_id}")
            seen.add(record.doc_id)
            paths = (record.pdf_path, *(image.path for image in record.images))
            for relative in paths:
                source = group_dir / relative
                target = out_dir / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(source), str(target))
            records.append(record)
        shutil.rmtree(group_dir)

    ordered = sorted(records, key=lambda record: record.doc_id)
    (out_dir / "metadata.jsonl").write_text(
        "".join(f"{record_to_json(record)}\n" for record in ordered), encoding="utf-8"
    )
    return ordered


def _build_group(
    *,
    group: GroupRef,
    out_dir: Path,
    cache_dir: Path,
    terms: frozenset[str],
    caption_terms: frozenset[str],
    threshold: float,
    seed: int,
    workers: int,
) -> tuple[int, int, int, int]:
    source = group.source()
    indices = tuple(range(source.total()))
    rows = source.rows(indices)
    manifest = Manifest(
        dataset=source.dataset,
        config=source.config,
        split=source.split,
        seed=seed,
        size=len(indices),
        indices=indices,
        doc_ids=tuple(row.doc_id for row in rows),
    )
    outcome = build_with_outcome(
        manifest,
        source,
        CachingPdfFetcher(cache_dir=cache_dir),
        out_dir,
        terms=terms,
        threshold=threshold,
        caption_terms=caption_terms,
        workers=workers,
    )
    images = sum(record.n_images for record in outcome.records)
    return outcome.sampled, outcome.gated_out, len(outcome.records), images


def _reuse_group(
    *, group: GroupRef, out_dir: Path, terms: frozenset[str], threshold: float
) -> tuple[int, int, int, int]:
    """Recover counts for a completed staged group after an interrupted run."""
    records = read_records(out_dir)
    expected = {
        relative
        for record in records
        for relative in (record.pdf_path, *(image.path for image in record.images))
    }
    missing = expected - existing_files(out_dir)
    if missing:
        raise ValueError(f"staged group {group.slug} is missing files: {sorted(missing)[:3]}")
    source = group.source()
    rows = source.rows(tuple(range(source.total())))
    gated_out = sum(
        1
        for row in rows
        if terms and not passes_gate(agronomy_score(row.text, terms), threshold=threshold)
    )
    return len(rows), gated_out, len(records), sum(record.n_images for record in records)


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-root", type=Path, default=Path("out/phenotype-30000"))
    parser.add_argument("--cache", type=Path, default=Path(".cache/pdfs"))
    parser.add_argument("--repo", default=DEFAULT_REPO)
    parser.add_argument("--threshold", type=float, default=DEFAULT_THRESHOLD)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument(
        "--shards",
        type=int,
        nargs="+",
        default=DEFAULT_SHARDS,
        help="shard indices in the eng_Latn split; one sampling window each",
    )
    parser.add_argument("--row-groups", type=int, nargs="+", default=DEFAULT_ROW_GROUPS)
    parser.add_argument(
        "--workers",
        type=int,
        default=DEFAULT_WORKERS,
        help="documents retrieved at once; the build waits on dead URLs, not on work",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="reuse complete staged groups in an interrupted output root",
    )
    return parser.parse_args(argv)


def _validate_output_root(out_root: Path, *, resume: bool) -> None:
    if not out_root.exists() or not any(out_root.iterdir()):
        if resume:
            raise SystemExit(f"cannot resume missing output root: {out_root}")
        return
    if not resume:
        raise SystemExit(f"refusing to reuse non-empty output root: {out_root}")
    if not (out_root / "groups").is_dir():
        raise SystemExit(f"cannot resume without staged groups: {out_root / 'groups'}")


def _run_group(
    *,
    group: GroupRef,
    group_dir: Path,
    cache_dir: Path,
    terms: frozenset[str],
    caption_terms: frozenset[str],
    threshold: float,
    seed: int,
    workers: int,
    resume: bool,
) -> tuple[tuple[int, int, int, int], str]:
    if resume and (group_dir / "metadata.jsonl").exists():
        return (
            _reuse_group(group=group, out_dir=group_dir, terms=terms, threshold=threshold),
            "reused",
        )
    if group_dir.exists() and any(group_dir.iterdir()):
        raise SystemExit(f"refusing to reuse incomplete staged group: {group_dir}")
    return (
        _build_group(
            group=group,
            out_dir=group_dir,
            cache_dir=cache_dir,
            terms=terms,
            caption_terms=caption_terms,
            threshold=threshold,
            seed=seed,
            workers=workers,
        ),
        "built",
    )


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    _validate_output_root(args.out_root, resume=args.resume)

    staging = args.out_root / "groups"
    dataset = args.out_root / "dataset"
    publish = args.out_root / "publish"
    caption_terms = load_phenotype_lexicon()
    terms = load_lexicon() if args.threshold > 0 else frozenset()

    totals = [0, 0, 0, 0]
    group_dirs = []
    for group in group_refs(args.shards, args.row_groups):
        group_dir = staging / group.slug
        group_dirs.append(group_dir)
        (sampled, gated_out, built, images), action = _run_group(
            group=group,
            group_dir=group_dir,
            cache_dir=args.cache,
            terms=terms,
            caption_terms=caption_terms,
            threshold=args.threshold,
            seed=args.seed,
            workers=args.workers,
            resume=args.resume,
        )
        totals = [
            totals[0] + sampled,
            totals[1] + gated_out,
            totals[2] + built,
            totals[3] + images,
        ]
        print(
            f"{group.slug}: skipped {gated_out}/{sampled}, "
            f"{action} {built} documents and {images} images",
            file=sys.stderr,
        )

    records = merge_builds(group_dirs, dataset)
    package = package_dataset(
        dataset,
        publish,
        repo_id=args.repo,
        records=records,
        sampled=totals[0],
        seed=args.seed,
        source_shards=len(set(args.shards)),
    )
    print(
        f"scaled build: sampled {totals[0]}, skipped {totals[1]}, built {totals[2]}, "
        f"extracted {totals[3]}, published {package.n_rows} rows in {publish}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
