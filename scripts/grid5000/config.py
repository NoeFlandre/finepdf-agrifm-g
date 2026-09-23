"""Pure configuration for one immutable Grid’5000 FinePDF run."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass
from typing import Any

DEFAULT_REPO = "NoeFlandre/finepdf-agrifm-g"
DEFAULT_SITES = (
    "grenoble",
    "lille",
    "lyon",
    "nancy",
    "nantes",
    "rennes",
    "sophia",
    "toulouse",
    "luxembourg",
)
DEFAULT_SHARDS = tuple(range(30))
DEFAULT_ROW_GROUPS = (0,)
DEFAULT_SEED = 20260918
DEFAULT_WORKERS = 16
DEFAULT_CORES = 16
DEFAULT_MEMORY_GB = 32
DEFAULT_WALLTIME = "04:00:00"
DEFAULT_PIPELINE = "agriculture-splits-v2"
UV_VERSION = "0.11.16"

_COMMIT = re.compile(r"^[0-9a-f]{40}$")
_WALLTIME = re.compile(r"^(?:[0-9]{2}):[0-5][0-9]:[0-5][0-9]$")


@dataclass(frozen=True, slots=True)
class RunConfig:
    """The exact input and resource contract for one remote run."""

    commit: str
    repo: str = DEFAULT_REPO
    pipeline: str = DEFAULT_PIPELINE
    seed: int = DEFAULT_SEED
    shards: tuple[int, ...] = DEFAULT_SHARDS
    row_groups: tuple[int, ...] = DEFAULT_ROW_GROUPS
    threshold: float = 0.005
    workers: int = DEFAULT_WORKERS
    cores: int = DEFAULT_CORES
    memory_gb: int = DEFAULT_MEMORY_GB
    walltime: str = DEFAULT_WALLTIME
    sites: tuple[str, ...] = DEFAULT_SITES
    remote_root: str = "~/agrifm-g-runs"

    def __post_init__(self) -> None:
        _validate_identity(self.commit, self.repo, self.seed)
        if not self.pipeline or "/" in self.pipeline or ".." in self.pipeline:
            raise ValueError("pipeline must be a non-empty profile name")
        object.__setattr__(self, "shards", _positive_unique(self.shards, "shards"))
        object.__setattr__(self, "row_groups", _nonnegative_unique(self.row_groups, "row_groups"))
        _validate_resources(self.threshold, self.workers, self.cores, self.memory_gb, self.walltime)
        if not self.sites or any(not site or "/" in site for site in self.sites):
            raise ValueError("sites must contain non-empty site aliases")
        object.__setattr__(self, "sites", tuple(dict.fromkeys(self.sites)))
        _validate_remote_root(self.remote_root)

    @property
    def run_id(self) -> str:
        """A stable identifier derived from all run-defining values."""
        digest = hashlib.sha256(self.to_json().encode("utf-8")).hexdigest()[:12]
        return f"finepdf-{self.commit[:12]}-{digest}"

    @property
    def remote_run_root(self) -> str:
        return f"{self.remote_root.rstrip('/')}/{self.run_id}"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, sort_keys=True, indent=2) + "\n"

    @classmethod
    def from_json(cls, payload: str) -> RunConfig:
        values = json.loads(payload)
        if not isinstance(values, dict):
            raise ValueError("run configuration must be a JSON object")
        for field in ("shards", "row_groups", "sites"):
            if field in values:
                values[field] = tuple(values[field])
        return cls(**values)


def _bounded_positive(value: int, name: str, maximum: int) -> None:
    if not isinstance(value, int) or isinstance(value, bool) or not 0 < value <= maximum:
        raise ValueError(f"{name} must be between 1 and {maximum}")


def _validate_identity(commit: str, repo: str, seed: int) -> None:
    if not _COMMIT.fullmatch(commit):
        raise ValueError("commit must be a 40-character lowercase SHA-1")
    if not repo or "/" not in repo:
        raise ValueError("repo must be an owner/name identifier")
    if seed < 0:
        raise ValueError("seed must be non-negative")


def _validate_resources(
    threshold: float, workers: int, cores: int, memory_gb: int, walltime: str
) -> None:
    if threshold < 0:
        raise ValueError("threshold must be non-negative")
    _bounded_positive(workers, "workers", 128)
    _bounded_positive(cores, "cores", 128)
    _bounded_positive(memory_gb, "memory_gb", 512)
    if not _WALLTIME.fullmatch(walltime):
        raise ValueError("walltime must use HH:MM:SS")


def _validate_remote_root(remote_root: str) -> None:
    if not remote_root.startswith("~/") or ".." in remote_root.split("/"):
        raise ValueError("remote_root must be a home-relative path")


def _positive_unique(values: tuple[int, ...], name: str) -> tuple[int, ...]:
    result = tuple(sorted(set(values)))
    if not result or any(not isinstance(value, int) or value < 0 for value in result):
        raise ValueError(f"{name} must contain non-negative integers")
    return result


def _nonnegative_unique(values: tuple[int, ...], name: str) -> tuple[int, ...]:
    return _positive_unique(values, name)
