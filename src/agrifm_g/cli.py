"""Scriptable entry points: sample, build, verify, publish."""

from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from pathlib import Path

from agrifm_g.adapters.finepdf import (
    DEFAULT_CONFIG,
    DEFAULT_DATASET,
    DEFAULT_SPLIT,
    ParquetRowSource,
    RowSource,
)
from agrifm_g.adapters.pdfsource import CachingPdfFetcher
from agrifm_g.adapters.publish import publish_dataset, write_dataset_card
from agrifm_g.adapters.storage import existing_files, read_records
from agrifm_g.domain.verification import verify_records
from agrifm_g.pipeline import Manifest, build_dataset, build_manifest

DEFAULT_MANIFEST = Path("data/sample_manifest.json")


def main(argv: Sequence[str] | None = None) -> int:
    """Run one command. Returns the process exit code."""
    args = _parser().parse_args(argv)
    return args.run(args)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="agrifm-g", description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)

    sample = commands.add_parser("sample", help="resolve a seeded FinePDF sample into a manifest")
    sample.add_argument("--size", type=int, default=10)
    sample.add_argument("--seed", type=int, default=20260918)
    sample.add_argument("--dataset", default=DEFAULT_DATASET)
    sample.add_argument("--config", default=DEFAULT_CONFIG)
    sample.add_argument("--split", default=DEFAULT_SPLIT)
    sample.add_argument("--out", type=Path, default=DEFAULT_MANIFEST)
    sample.set_defaults(run=_run_sample)

    build = commands.add_parser("build", help="materialise a manifest into a dataset directory")
    build.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    build.add_argument("--out", type=Path, default=Path("out/dataset"))
    build.add_argument("--cache", type=Path, default=Path(".cache/pdfs"))
    build.set_defaults(run=_run_build)

    verify = commands.add_parser("verify", help="check a dataset's schema and file references")
    verify.add_argument("--dataset", type=Path, required=True)
    verify.set_defaults(run=_run_verify)

    publish = commands.add_parser("publish", help="upload a dataset to Hugging Face")
    publish.add_argument("--dataset", type=Path, required=True)
    publish.add_argument("--repo", required=True)
    publish.add_argument("--dry-run", action="store_true")
    publish.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    publish.set_defaults(run=_run_publish)
    return parser


def _row_source(args: argparse.Namespace) -> RowSource:
    return ParquetRowSource(dataset=args.dataset, config=args.config, split=args.split)


def _run_sample(args: argparse.Namespace) -> int:
    manifest = build_manifest(
        _row_source(args),
        size=args.size,
        seed=args.seed,
        dataset=args.dataset,
        config=args.config,
        split=args.split,
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(f"{manifest.to_json()}\n", encoding="utf-8")
    print(f"wrote {args.out} with {len(manifest.doc_ids)} documents")
    return 0


def _run_build(args: argparse.Namespace) -> int:
    manifest = Manifest.from_json(json.loads(args.manifest.read_text(encoding="utf-8")))
    source = ParquetRowSource(
        dataset=manifest.dataset, config=manifest.config, split=manifest.split
    )
    args.out.mkdir(parents=True, exist_ok=True)
    records = build_dataset(manifest, source, CachingPdfFetcher(cache_dir=args.cache), args.out)
    images = sum(record.n_images for record in records)
    print(f"built {len(records)} documents and {images} images in {args.out}")
    return 0


def _run_verify(args: argparse.Namespace) -> int:
    problems = verify_records(read_records(args.dataset), existing_files(args.dataset))
    for problem in problems:
        print(problem)
    print("ok" if not problems else f"{len(problems)} problems")
    return 1 if problems else 0


def _run_publish(args: argparse.Namespace) -> int:
    seed = Manifest.from_json(json.loads(args.manifest.read_text(encoding="utf-8"))).seed
    write_dataset_card(args.dataset, args.repo, read_records(args.dataset), manifest_seed=seed)
    url = publish_dataset(args.dataset, args.repo, dry_run=args.dry_run)
    print(f"{'dry run: would publish to' if args.dry_run else 'published'} {url}")
    return 0
