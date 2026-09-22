"""Pure shell-command rendering for Grid’5000 operations."""

from __future__ import annotations

import shlex

from scripts.grid5000.config import RunConfig


def resource_spec(config: RunConfig) -> str:
    """Return a bounded CPU-only OAR resource request."""
    return f"host=1/core={config.cores},walltime={config.walltime}"


def memory_property(config: RunConfig) -> str:
    """Return Grid’5000's node-memory property filter in MB."""
    return f"memnode >= {config.memory_gb * 1024}"


def render_worker_command(source_dir: str, spec_path: str) -> str:
    """Render the command executed inside the reserved allocation."""
    script = f"{source_dir.rstrip('/')}/scripts/grid5000/worker.sh"
    return "AGRIFM_G_GRID5000_JOB=1 " + shlex.join(["bash", script, "--spec", spec_path])


def render_submission_command(config: RunConfig, source_dir: str, run_root: str) -> str:
    """Render one OAR submission; policy checks are deliberately separate calls."""
    stdout = f"{run_root.rstrip('/')}/logs/stdout.log"
    stderr = f"{run_root.rstrip('/')}/logs/stderr.log"
    worker = render_worker_command(source_dir, f"{run_root.rstrip('/')}/spec.json")
    remote = f"cd {shlex.quote(source_dir)} && exec {worker}"
    args = [
        "oarsub",
        "-n",
        f"agrifm-{config.run_id[-12:]}",
        "-l",
        resource_spec(config),
        "-p",
        memory_property(config),
        "-O",
        stdout,
        "-E",
        stderr,
        remote,
    ]
    return shlex.join(args)
