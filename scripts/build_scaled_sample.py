"""Build and package a bounded multi-row-group FinePDF sample."""

from __future__ import annotations

import argparse
import os
import shutil
import sys
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from agrifm_g.adapters.clip_relevance import (
    DEFAULT_MODEL_ID,
    DEFAULT_MODEL_REVISION,
    ClipImageRelevanceFilter,
)
from agrifm_g.adapters.finepdf import FinePdfRow, ParquetRowSource
from agrifm_g.adapters.lexicon import AgricultureLexicons, load_agriculture_lexicons
from agrifm_g.adapters.packaging import package_dataset
from agrifm_g.adapters.pdfsource import CachingPdfFetcher
from agrifm_g.adapters.storage import existing_files, read_records, record_to_json
from agrifm_g.domain.agriculture import AgricultureSplit, classify_document
from agrifm_g.domain.normalisation import safe_doc_id
from agrifm_g.domain.records import DocumentRecord
from agrifm_g.domain.textgate import DEFAULT_THRESHOLD, agronomy_score, passes_gate
from agrifm_g.pipeline import DEFAULT_WORKERS, Manifest, build_with_outcome

DEFAULT_REPO = "NoeFlandre/finepdf-agrifm-g"
DEFAULT_SHARDS = tuple(range(30))
DEFAULT_ROW_GROUPS = (0,)
DEFAULT_SEED = 20260918
OUTPUT_PROFILE = "agriculture-30000"


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


def _build_lexicon_terms(
    *, threshold: float
) -> tuple[frozenset[str], frozenset[str], frozenset[str]]:
    """Load the broad and both category lexicons used by every staged group."""
    lexicons: AgricultureLexicons = load_agriculture_lexicons()
    terms = lexicons.prefetch_terms if threshold > 0 else frozenset()
    return terms, lexicons.conventional, lexicons.sustainable


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
    conventional_terms: frozenset[str],
    sustainable_terms: frozenset[str],
    threshold: float,
    seed: int,
    workers: int,
) -> tuple[int, int, int, int, int]:
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
        conventional_terms=conventional_terms,
        sustainable_terms=sustainable_terms,
        workers=workers,
    )
    images = sum(record.n_images for record in outcome.records)
    return (
        outcome.sampled,
        outcome.gated_out,
        outcome.ambiguous_out,
        len(outcome.records),
        images,
    )


def _reuse_group(
    *,
    group: GroupRef,
    out_dir: Path,
    terms: frozenset[str],
    conventional_terms: frozenset[str],
    sustainable_terms: frozenset[str],
    threshold: float,
) -> tuple[int, int, int, int, int]:
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
    gated_out, ambiguous_out, expected_splits = _decision_counts(
        rows,
        terms=terms,
        conventional_terms=conventional_terms,
        sustainable_terms=sustainable_terms,
        threshold=threshold,
    )
    _validate_reused_records(records, expected_splits, group.slug)
    return (
        len(rows),
        gated_out,
        ambiguous_out,
        len(records),
        sum(record.n_images for record in records),
    )


def _decision_counts(
    rows: Sequence[FinePdfRow],
    *,
    terms: frozenset[str],
    conventional_terms: frozenset[str],
    sustainable_terms: frozenset[str],
    threshold: float,
) -> tuple[int, int, dict[str, AgricultureSplit]]:
    gated_out = 0
    ambiguous_out = 0
    expected_splits: dict[str, AgricultureSplit] = {}
    for row in rows:
        if terms and not passes_gate(agronomy_score(row.text, terms), threshold=threshold):
            gated_out += 1
            continue
        split = classify_document(row.text, conventional_terms, sustainable_terms)
        if split is None:
            ambiguous_out += 1
            continue
        expected_splits[safe_doc_id(row.doc_id)] = split
    return gated_out, ambiguous_out, expected_splits


def _validate_reused_records(
    records: Sequence[DocumentRecord],
    expected_splits: dict[str, AgricultureSplit],
    group_slug: str,
) -> None:
    valid_splits = {split.value for split in AgricultureSplit}
    for record in records:
        if record.agriculture_split not in valid_splits:
            raise ValueError(
                f"staged group {group_slug} has an invalid agriculture split: "
                f"{record.agriculture_split!r}"
            )
        expected = expected_splits.get(record.doc_id)
        if expected is None or expected.value != record.agriculture_split:
            raise ValueError(
                f"staged group {group_slug} has a record outside the current category decisions: "
                f"{record.doc_id}"
            )


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-root", type=Path, default=Path(f"out/{OUTPUT_PROFILE}"))
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
    parser.add_argument("--image-filter-model", default=DEFAULT_MODEL_ID)
    parser.add_argument("--image-filter-revision", default=DEFAULT_MODEL_REVISION)
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


def require_grid5000_execution(env: Mapping[str, str] | None = None) -> None:
    """Refuse the scaled build unless it is inside an OAR allocation."""
    values = os.environ if env is None else env
    required = ("AGRIFM_G_GRID5000_JOB", "OAR_JOB_ID", "OAR_NODEFILE")
    if values.get(required[0]) != "1" or any(not values.get(name) for name in required[1:]):
        raise SystemExit("the scaled FinePDF build must run inside a Grid5000 OAR job")


def _prepare_group_dir(group_dir: Path, *, resume: bool) -> Path:
    """Return a clean private staging directory for one group.

    A completed group is immutable.  An incomplete ``.part`` directory can be
    discarded on resume, and the final rename makes completion atomic.
    """
    partial_dir = group_dir.with_name(f".{group_dir.name}.part")
    if partial_dir.exists():
        if not resume:
            raise SystemExit(f"refusing to reuse incomplete staged group: {partial_dir}")
        shutil.rmtree(partial_dir)
    if group_dir.exists() and any(group_dir.iterdir()):
        if not resume or (group_dir / "metadata.jsonl").exists():
            raise SystemExit(f"refusing to reuse staged group: {group_dir}")
        shutil.rmtree(group_dir)
    partial_dir.parent.mkdir(parents=True, exist_ok=True)
    partial_dir.mkdir()
    return partial_dir


def _run_group(
    *,
    group: GroupRef,
    group_dir: Path,
    cache_dir: Path,
    terms: frozenset[str],
    conventional_terms: frozenset[str],
    sustainable_terms: frozenset[str],
    threshold: float,
    seed: int,
    workers: int,
    resume: bool,
) -> tuple[tuple[int, int, int, int, int], str]:
    if resume and (group_dir / "metadata.jsonl").exists():
        return (
            _reuse_group(
                group=group,
                out_dir=group_dir,
                terms=terms,
                conventional_terms=conventional_terms,
                sustainable_terms=sustainable_terms,
                threshold=threshold,
            ),
            "reused",
        )
    partial_dir = _prepare_group_dir(group_dir, resume=resume)
    result = _build_group(
        group=group,
        out_dir=partial_dir,
        cache_dir=cache_dir,
        terms=terms,
        conventional_terms=conventional_terms,
        sustainable_terms=sustainable_terms,
        threshold=threshold,
        seed=seed,
        workers=workers,
    )
    partial_dir.replace(group_dir)
    return result, "built"


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    require_grid5000_execution()
    _validate_output_root(args.out_root, resume=args.resume)

    staging = args.out_root / "groups"
    dataset = args.out_root / "dataset"
    publish = args.out_root / "publish"
    terms, conventional_terms, sustainable_terms = _build_lexicon_terms(threshold=args.threshold)
    visual_filter = ClipImageRelevanceFilter(
        model_id=args.image_filter_model,
        revision=args.image_filter_revision,
        num_threads=args.workers,
    )
    visual_check = visual_filter.audit_reference_examples(Path("docs/images"))
    print(
        "CLIP reference check: "
        f"kept {visual_check['reference_photos_kept']}/{visual_check['reference_photos']} photos; "
        f"rejected {visual_check['reference_noise_rejected']}/"
        f"{visual_check['reference_noise']} obvious negatives; synthetic documents "
        f"chart={visual_check['synthetic_chart_rejected']}, "
        f"table={visual_check['synthetic_table_rejected']}, "
        f"map={visual_check['synthetic_map_rejected']}",
        file=sys.stderr,
    )

    totals = [0, 0, 0, 0, 0]
    group_dirs = []
    for group in group_refs(args.shards, args.row_groups):
        group_dir = staging / group.slug
        group_dirs.append(group_dir)
        (sampled, gated_out, ambiguous_out, built, images), action = _run_group(
            group=group,
            group_dir=group_dir,
            cache_dir=args.cache,
            terms=terms,
            conventional_terms=conventional_terms,
            sustainable_terms=sustainable_terms,
            threshold=args.threshold,
            seed=args.seed,
            workers=args.workers,
            resume=args.resume,
        )
        totals = [
            totals[0] + sampled,
            totals[1] + gated_out,
            totals[2] + ambiguous_out,
            totals[3] + built,
            totals[4] + images,
        ]
        print(
            f"{group.slug}: skipped {gated_out} text-gated and {ambiguous_out} ambiguous "
            f"of {sampled}, "
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
        text_gated=totals[1],
        ambiguous=totals[2],
        visual_filter=visual_filter,
    )
    print(
        f"scaled build: sampled {totals[0]}, text-gated {totals[1]}, "
        f"ambiguous {totals[2]}, built {totals[3]}, "
        f"extracted {totals[4]}, published {package.n_rows} rows in {publish}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
