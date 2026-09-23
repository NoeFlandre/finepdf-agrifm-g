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


def run_command(
    argv: Sequence[str], *, input_bytes: bytes | None = None, timeout: float | None = None
) -> CommandResult:
    """Run one command with captured output and no implicit shell."""
    result = subprocess.run(
        list(argv),
        input=input_bytes,
        capture_output=True,
        check=False,
        timeout=timeout,
    )
    return CommandResult(
        returncode=result.returncode,
        stdout=result.stdout.decode("utf-8", errors="replace"),
        stderr=result.stderr.decode("utf-8", errors="replace"),
    )


def ssh_command(site: str, command: str) -> CommandResult:
    """Run one command on a site frontend through the configured SSH alias."""
    try:
        return run_command(
            ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=8", site, command],
            timeout=30,
        )
    except subprocess.TimeoutExpired:
        return CommandResult(124, "", "SSH command exceeded the 30-second timeout")


def check_policy(site: str) -> PolicyResult:
    """Run the required policy check on a site frontend."""
    result = ssh_command(site, "usagepolicycheck -t")
    return parse_policy_result(result.returncode, result.stdout + result.stderr)


def remote_prepare(site: str, run_root: str) -> None:
    """Create only the project-owned remote directories needed by a run."""
    command = "mkdir -p -- " + " ".join(
        shlex.quote(f"{run_root}/{directory}") for directory in ("logs", "source")
    )
    result = ssh_command(site, command)
    if result.returncode:
        raise SubmissionError(f"could not prepare remote run root: {result.stderr.strip()}")


def probe_site(site: str) -> CommandResult:
    """Check that a frontend exposes the commands needed by the runner."""
    command = (
        "for name in usagepolicycheck oarsub oarstat oardel python3; do "
        'command -v "$name" >/dev/null || exit 127; '
        "done; "
        "if command -v uv >/dev/null; then printf 'uv=present\\n'; "
        "else printf 'uv=bootstrap\\n'; fi"
    )
    return ssh_command(site, command)


def remote_home(site: str) -> str:
    """Resolve the site-local home directory without assuming its path."""
    result = ssh_command(site, 'printf "%s" "$HOME"')
    home = result.stdout.strip()
    if result.returncode or not home.startswith("/") or "\n" in home:
        raise SubmissionError(f"could not resolve remote home on {site}")
    return home


def remote_upload_archive(source_dir: Path, commit: str, site: str, remote_source_dir: str) -> None:
    """Stream one committed source archive to an exact remote directory."""
    archive = subprocess.Popen(
        ["git", "-C", str(source_dir), "archive", "--format=tar", commit],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if archive.stdout is None or archive.stderr is None:
        raise SubmissionError("could not open git archive stream")
    remote_command = "mkdir -p -- {0} && tar -xf - -C {0}".format(shlex.quote(remote_source_dir))
    upload = subprocess.Popen(
        ["ssh", "-o", "BatchMode=yes", site, remote_command],
        stdin=archive.stdout,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    archive.stdout.close()
    upload_stdout, upload_stderr = upload.communicate()
    archive_returncode = archive.wait()
    archive_stderr = archive.stderr.read().decode("utf-8", errors="replace")
    if archive_returncode:
        raise SubmissionError(f"could not archive commit: {archive_stderr.strip()}")
    if upload.returncode:
        detail = upload_stderr.decode("utf-8", errors="replace").strip()
        raise SubmissionError(f"could not upload source archive: {detail}")
    del upload_stdout


def copy_file_to_remote(local_path: Path, site: str, remote_path: str) -> None:
    """Copy one local file to an already prepared remote directory."""
    result = run_command(["scp", "-q", str(local_path), f"{site}:{remote_path}"])
    if result.returncode:
        raise SubmissionError(f"could not upload {local_path.name}: {result.stderr.strip()}")


def copy_file_from_remote(site: str, remote_path: str, local_path: Path) -> None:
    """Copy one exact remote file to a local path."""
    local_path.parent.mkdir(parents=True, exist_ok=True)
    result = run_command(["scp", "-q", f"{site}:{remote_path}", str(local_path)])
    if result.returncode:
        raise SubmissionError(f"could not fetch {remote_path}: {result.stderr.strip()}")


def submit_job(site: str, submission_command: str) -> tuple[str, CommandResult]:
    """Submit once and require an unambiguous OAR job ID."""
    result = ssh_command(site, submission_command)
    if result.returncode:
        raise SubmissionError(f"oarsub failed: {result.stderr.strip()}")
    job_id = parse_job_id(result.stdout + result.stderr)
    return job_id, result


def job_status(site: str, job_id: str) -> CommandResult:
    """Read scheduler status for a numeric job ID."""
    if not job_id.isdigit():
        raise SubmissionError("job ID must be numeric")
    return ssh_command(site, f"oarstat -j {job_id}")


def cancel_job(site: str, job_id: str) -> CommandResult:
    """Cancel one numeric OAR job, never a broad scheduler selection."""
    if not job_id.isdigit():
        raise SubmissionError("job ID must be numeric")
    result = ssh_command(site, f"oardel {job_id}")
    if result.returncode:
        raise SubmissionError(f"oardel failed: {result.stderr.strip()}")
    return result


def read_remote_json(site: str, remote_path: str) -> dict[str, Any]:
    """Read and validate one remote JSON object."""
    result = ssh_command(site, "cat -- " + shlex.quote(remote_path))
    if result.returncode:
        raise SubmissionError(f"could not read {remote_path}: {result.stderr.strip()}")
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError as error:
        raise SubmissionError(f"invalid JSON at {remote_path}") from error
    if not isinstance(payload, dict):
        raise SubmissionError(f"JSON at {remote_path} is not an object")
    return payload


def publish_remote_path(remote_root: str) -> str:
    """Return the exact publish directory for the agriculture-splits worker."""
    return f"{remote_root}/out/agriculture-30000/publish/."


def fetch_publish(site: str, remote_root: str, local_publish_dir: Path) -> dict[str, Any]:
    """Verify the remote receipt, then fetch and locally verify publish files."""
    from scripts.grid5000.receipt import verify_receipt

    receipt = read_remote_json(site, f"{remote_root}/receipt.json")
    if receipt.get("status") != "complete":
        raise SubmissionError("remote receipt is not complete")
    if local_publish_dir.exists():
        raise SubmissionError(f"local publish directory already exists: {local_publish_dir}")
    pending = local_publish_dir.with_name(f".{local_publish_dir.name}.part")
    if pending.exists():
        raise SubmissionError(f"local fetch is already incomplete: {pending}")
    pending.mkdir(parents=True, exist_ok=False)
    remote_publish = publish_remote_path(remote_root)
    result = run_command(["scp", "-q", "-r", f"{site}:{remote_publish}", str(pending)])
    if result.returncode:
        raise SubmissionError(f"could not fetch publish files: {result.stderr.strip()}")
    try:
        verify_receipt(pending, receipt)
    except ValueError as error:
        raise SubmissionError(str(error)) from error
    pending.replace(local_publish_dir)
    return receipt


def cleanup_remote(site: str, remote_root: str, run_id: str) -> None:
    """Remove only the exact run directory after caller-side confirmation."""
    if not run_id.startswith("finepdf-") or remote_root.rstrip("/").split("/")[-1] != run_id:
        raise SubmissionError("remote cleanup target does not match the confirmed run ID")
    result = ssh_command(site, "rm -rf -- " + shlex.quote(remote_root))
    if result.returncode:
        raise SubmissionError(f"remote cleanup failed: {result.stderr.strip()}")
