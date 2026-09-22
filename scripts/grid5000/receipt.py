"""Build and verify immutable receipts for remote publish artifacts."""

from __future__ import annotations

import hashlib
import json
import socket
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from scripts.grid5000.config import RunConfig


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _file_manifest(publish_dir: Path) -> dict[str, dict[str, int | str]]:
    if not publish_dir.is_dir():
        raise ValueError(f"publish directory does not exist: {publish_dir}")
    return {
        path.relative_to(publish_dir).as_posix(): {
            "sha256": _sha256(path),
            "size": path.stat().st_size,
        }
        for path in sorted(publish_dir.rglob("*"))
        if path.is_file()
    }


def _stats(publish_dir: Path) -> dict[str, Any] | None:
    stats_path = publish_dir / "stats.json"
    if not stats_path.exists():
        return None
    payload = json.loads(stats_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("publish stats must be a JSON object")
    return payload


def _spec_payload(spec: RunConfig | Mapping[str, Any] | None) -> dict[str, Any] | None:
    if spec is None:
        return None
    return spec.to_dict() if isinstance(spec, RunConfig) else dict(spec)


def make_receipt(
    run_id: str,
    job_id: str,
    publish_dir: Path,
    *,
    status: str = "complete",
    spec: RunConfig | Mapping[str, Any] | None = None,
    commit: str | None = None,
    error: str | None = None,
) -> dict[str, Any]:
    """Return a JSON-safe receipt for a completed or failed worker run."""
    if status not in {"complete", "failed"}:
        raise ValueError("receipt status must be complete or failed")
    files = _file_manifest(publish_dir) if publish_dir.is_dir() else {}
    receipt: dict[str, Any] = {
        "schema_version": 1,
        "run_id": run_id,
        "job_id": job_id,
        "hostname": socket.gethostname(),
        "status": status,
        "commit": commit,
        "spec": _spec_payload(spec),
        "stats": _stats(publish_dir) if publish_dir.is_dir() else None,
        "files": files,
    }
    if error is not None:
        receipt["error"] = error
    return receipt


def write_receipt_atomic(path: Path, receipt: Mapping[str, Any]) -> None:
    """Write a receipt atomically so readers never see partial JSON."""
    path.parent.mkdir(parents=True, exist_ok=True)
    pending = path.with_name(f".{path.name}.part")
    pending.write_text(json.dumps(dict(receipt), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    pending.replace(path)


def verify_receipt(publish_dir: Path, receipt: Mapping[str, Any]) -> None:
    """Raise when local files do not exactly match a complete receipt."""
    if receipt.get("status") != "complete":
        raise ValueError("remote receipt is not complete")
    expected = receipt.get("files")
    if not isinstance(expected, dict):
        raise ValueError("receipt has no file manifest")
    actual = _file_manifest(publish_dir)
    if actual != expected:
        raise ValueError("fetched publish files do not match the remote receipt")
