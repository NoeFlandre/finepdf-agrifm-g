"""Small, injectable side-effect boundary for SSH and OAR."""

from __future__ import annotations

import json
import re
import shlex
import subprocess
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class SubmissionError(RuntimeError):
    """A remote operation was unsafe or did not produce a trustworthy result."""


@dataclass(frozen=True, slots=True)
class CommandResult:
    """The captured result of one external command."""

    returncode: int
    stdout: str
    stderr: str


@dataclass(frozen=True, slots=True)
class PolicyResult:
    """The Grid’5000 usage-policy verdict and raw output."""

    returncode: int
    output: str

    @property
    def ok(self) -> bool:
        return self.returncode == 0 and "No jobs flagged" in self.output

    @property
    def warnings(self) -> tuple[str, ...]:
        return tuple(line for line in self.output.splitlines() if line.startswith("Error:"))


_JOB_ID = re.compile(r"(?:OAR_JOB_ID|job\s+id)\s*[:=]?\s*([0-9]+)", re.IGNORECASE)


def parse_policy_result(returncode: int, output: str) -> PolicyResult:
    """Accept only a successful command that explicitly reports no flagged jobs."""
    return PolicyResult(returncode=returncode, output=output)


def parse_job_id(output: str) -> str:
    """Extract exactly one OAR job ID; ambiguity is never retried automatically."""
    matches = tuple(dict.fromkeys(_JOB_ID.findall(output)))
    if len(matches) != 1:
        raise SubmissionError("oarsub returned no unambiguous job ID")
    return matches[0]


def refuse_duplicate_submission(state_path: Path) -> None:
    """Refuse to submit again once a local state file contains a job ID."""
    if not state_path.exists():
        return
    try:
        payload = json.loads(state_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise SubmissionError(f"existing submission state is unreadable: {state_path}") from error
    if payload.get("job_id"):
        raise SubmissionError(f"run already submitted: {state_path}")
    raise SubmissionError(f"submission state exists without a job ID: {state_path}")


def write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    """Write a small state file without exposing a partial JSON document."""
    path.parent.mkdir(parents=True, exist_ok=True)
    pending = path.with_suffix(f"{path.suffix}.part")
    pending.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    pending.replace(path)


def run_command(argv: Sequence[str], *, input_bytes: bytes | None = None) -> CommandResult:
    """Run one command with captured output and no implicit shell."""
    result = subprocess.run(
        list(argv),
        input=input_bytes,
        capture_output=True,
        check=False,
    )
    return CommandResult(
        returncode=result.returncode,
        stdout=result.stdout.decode("utf-8", errors="replace"),
        stderr=result.stderr.decode("utf-8", errors="replace"),
    )


def ssh_command(site: str, command: str) -> CommandResult:
    """Run one command on a site frontend through the configured SSH alias."""
    return run_command(["ssh", "-o", "BatchMode=yes", site, command])


def check_policy(site: str) -> PolicyResult:
    """Run the required policy check on a site frontend."""
    result = ssh_command(site, "usagepolicycheck -t")
    return parse_policy_result(result.returncode, result.stdout + result.stderr)


def remote_prepare(site: str, run_root: str) -> None:
    """Create only the project-owned remote directories needed by a run."""
    command = "mkdir -p -- " + shlex.quote(f"{run_root}/logs")
    result = ssh_command(site, command)
    if result.returncode:
        raise SubmissionError(f"could not prepare remote run root: {result.stderr.strip()}")
