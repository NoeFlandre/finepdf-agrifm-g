"""Reserved-node entry point for one immutable Grid’5000 FinePDF run."""

from __future__ import annotations

import argparse
import os
from collections.abc import Mapping, Sequence
from pathlib import Path

from scripts.grid5000.config import RunConfig
from scripts.grid5000.receipt import make_receipt, write_receipt_atomic

OUTPUT_PROFILE = "agriculture-30000"


def build_output_root(run_root: Path) -> Path:
    """Return the immutable output root for the agriculture-splits pipeline."""
    return run_root / "out" / OUTPUT_PROFILE


def require_oar_environment(env: Mapping[str, str] | None = None) -> None:
    """Reject execution on a frontend or outside the reserved allocation."""
    values = os.environ if env is None else env
    required = ("AGRIFM_G_GRID5000_JOB", "OAR_JOB_ID", "OAR_NODEFILE")
    missing = tuple(name for name in required if not values.get(name))
    if values.get("AGRIFM_G_GRID5000_JOB") != "1":
        missing = (*missing, "AGRIFM_G_GRID5000_JOB=1")
    if missing:
        raise RuntimeError("worker requires a reserved OAR environment: " + ", ".join(missing))


def load_config(spec_path: Path) -> RunConfig:
    """Load the spec and verify it is located below its own run ID."""
    config = RunConfig.from_json(spec_path.read_text(encoding="utf-8"))
    if spec_path.parent.name != config.run_id:
        raise RuntimeError("spec path does not match its immutable run ID")
    return config


def build_scaled_arguments(config: RunConfig, run_root: Path) -> list[str]:
    """Render arguments for the existing scaled build without duplicating its logic."""
    output_root = build_output_root(run_root)
    arguments = [
        "--out-root",
        str(output_root),
        "--cache",
        str(run_root / "cache" / "pdfs"),
        "--repo",
        config.repo,
        "--threshold",
        format(config.threshold, ".17g"),
        "--seed",
        str(config.seed),
        "--shards",
        *(str(shard) for shard in config.shards),
        "--row-groups",
        *(str(row_group) for row_group in config.row_groups),
        "--workers",
        str(config.workers),
    ]
    if (output_root / "groups").is_dir():
        arguments.append("--resume")
    return arguments


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--spec", type=Path, required=True)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    require_oar_environment()
    args = _parse_args(argv)
    spec_path = args.spec.expanduser().resolve()
    config = load_config(spec_path)
    run_root = spec_path.parent
    publish_dir = build_output_root(run_root) / "publish"
    receipt_path = run_root / "receipt.json"
    job_id = os.environ["OAR_JOB_ID"]
    try:
        from scripts.build_scaled_sample import main as build_main

        result = build_main(build_scaled_arguments(config, run_root))
    except BaseException as error:
        receipt = make_receipt(
            config.run_id,
            job_id,
            publish_dir,
            status="failed",
            spec=config,
            commit=config.commit,
            error=f"{type(error).__name__}: {error}",
        )
        write_receipt_atomic(receipt_path, receipt)
        raise
    receipt = make_receipt(
        config.run_id,
        job_id,
        publish_dir,
        spec=config,
        commit=config.commit,
    )
    write_receipt_atomic(receipt_path, receipt)
    return result


if __name__ == "__main__":
    raise SystemExit(main())
