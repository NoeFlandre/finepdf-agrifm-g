"""Command-line orchestration for the Grid’5000-only scaled FinePDF build."""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections.abc import Sequence
from contextlib import suppress
from pathlib import Path
from typing import Any

from scripts.grid5000 import remote
from scripts.grid5000.commands import memory_property, render_submission_command, resource_spec
from scripts.grid5000.config import (
    DEFAULT_CORES,
    DEFAULT_MEMORY_GB,
    DEFAULT_REPO,
    DEFAULT_ROW_GROUPS,
    DEFAULT_SEED,
    DEFAULT_SHARDS,
    DEFAULT_SITES,
    DEFAULT_WALLTIME,
    DEFAULT_WORKERS,
    RunConfig,
)
from scripts.grid5000.receipt import verify_receipt

_RUN_ID = re.compile(r"^finepdf-[0-9a-f]{12}-[0-9a-f]{12}$")
_TERMINAL_JOB_STATES = frozenset({"c", "cancelled", "e", "error", "t", "terminated"})


def current_commit(source_dir: Path) -> str:
    """Return the exact commit that will be archived."""
    result = remote.run_command(["git", "-C", str(source_dir), "rev-parse", "HEAD"])
    commit = result.stdout.strip()
    if result.returncode or not re.fullmatch(r"[0-9a-f]{40}", commit):
        raise remote.SubmissionError(f"could not resolve a commit: {result.stderr.strip()}")
    return commit


def ensure_clean_checkout(source_dir: Path) -> None:
    """Refuse to archive a checkout whose tracked state is not committed."""
    result = remote.run_command(["git", "-C", str(source_dir), "status", "--porcelain=v1"])
    if result.returncode:
        raise remote.SubmissionError(f"could not inspect checkout: {result.stderr.strip()}")
    if result.stdout.strip():
        raise remote.SubmissionError("refusing to submit a dirty checkout")


def _add_run_options(parser: argparse.ArgumentParser, *, include_source: bool = False) -> None:
    if include_source:
        parser.add_argument("--source-dir", type=Path, default=Path())
    parser.add_argument("--state-root", type=Path, default=Path("out/grid5000"))
    parser.add_argument("--site", dest="sites", action="append", help="site alias; repeatable")


def _add_build_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--repo", default=DEFAULT_REPO)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--threshold", type=float, default=0.005)
    parser.add_argument("--workers", type=int, default=DEFAULT_WORKERS)
    parser.add_argument("--cores", type=int, default=DEFAULT_CORES)
    parser.add_argument("--memory-gb", type=int, default=DEFAULT_MEMORY_GB)
    parser.add_argument("--walltime", default=DEFAULT_WALLTIME)
    parser.add_argument("--shards", type=int, nargs="+", default=DEFAULT_SHARDS)
    parser.add_argument("--row-groups", type=int, nargs="+", default=DEFAULT_ROW_GROUPS)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)

    preflight = commands.add_parser("preflight", help="check every configured Grid5000 site")
    _add_run_options(preflight)
    preflight.set_defaults(run=_run_preflight)

    submit = commands.add_parser("submit", help="submit exactly one scaled build job")
    _add_run_options(submit, include_source=True)
    _add_build_options(submit)
    submit.add_argument("--remote-root", default="~/agrifm-g-runs")
    submit.add_argument("--dry-run", action="store_true")
    submit.add_argument("--resume", action="store_true")
    submit.set_defaults(run=_run_submit)

    for name, help_text, handler in (
        ("status", "show OAR status for a submitted run", _run_status),
        ("fetch", "fetch and verify a completed publish artifact", _run_fetch),
        ("cancel", "cancel one submitted OAR job", _run_cancel),
        ("cleanup", "remove one verified remote run root", _run_cleanup),
    ):
        command = commands.add_parser(name, help=help_text)
        command.add_argument("--run-id", required=True)
        command.add_argument("--state-root", type=Path, default=Path("out/grid5000"))
        if name == "cleanup":
            command.add_argument("--confirm-run-id")
        command.set_defaults(run=handler)
    return parser


def _sites(args: argparse.Namespace) -> tuple[str, ...]:
    return tuple(args.sites) if args.sites else DEFAULT_SITES


def _config(args: argparse.Namespace, commit: str) -> RunConfig:
    return RunConfig(
        commit=commit,
        repo=args.repo,
        seed=args.seed,
        shards=tuple(args.shards),
        row_groups=tuple(args.row_groups),
        threshold=args.threshold,
        workers=args.workers,
        cores=args.cores,
        memory_gb=args.memory_gb,
        walltime=args.walltime,
        sites=_sites(args),
        remote_root=args.remote_root,
    )


def _state_dir(state_root: Path, run_id: str) -> Path:
    if not _RUN_ID.fullmatch(run_id):
        raise remote.SubmissionError("invalid run ID")
    return state_root / run_id


def _load_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise remote.SubmissionError(f"could not read state: {path}") from error
    if not isinstance(payload, dict):
        raise remote.SubmissionError(f"state is not a JSON object: {path}")
    return payload


def _submission(args: argparse.Namespace) -> tuple[Path, dict[str, Any]]:
    state_dir = _state_dir(args.state_root, args.run_id)
    return state_dir, _load_json(state_dir / "submission.json")


def _save_policy(state_dir: Path, name: str, policy: remote.PolicyResult) -> None:
    remote.write_json_atomic(
        state_dir / f"{name}.json",
        {
            "returncode": policy.returncode,
            "ok": policy.ok,
            "warnings": list(policy.warnings),
            "output": policy.output,
        },
    )


def _remote_root(home: str, config: RunConfig) -> str:
    relative = config.remote_root[2:].strip("/")
    return f"{home.rstrip('/')}/{relative}/{config.run_id}"


def _select_site(sites: Sequence[str]) -> str:
    failures: list[str] = []
    for site in sites:
        result = remote.probe_site(site)
        if result.returncode == 0:
            return site
        failures.append(f"{site}: {result.stderr.strip() or 'required command unavailable'}")
    raise remote.SubmissionError("no Grid5000 site passed preflight: " + "; ".join(failures))


def _job_is_active(status: remote.CommandResult) -> bool:
    """Treat unreadable or unknown scheduler state as active for safety.

    ``oarstat -j`` uses a compact table by default (the state is the
    penultimate field, e.g. ``... 18:30:32 T p3``), while some sites expose a
    verbose ``state = Terminated`` form.  Cleanup must understand both forms.
    """
    if status.returncode != 0:
        return True

    verbose = re.search(r"\bstate\s*[:=]\s*([A-Za-z]+)", status.stdout, re.IGNORECASE)
    if verbose:
        return verbose.group(1).lower() not in _TERMINAL_JOB_STATES

    for line in status.stdout.splitlines():
        fields = line.split()
        if fields and fields[0].isdigit() and len(fields) >= 3:
            state = fields[-2].lower()
            return state not in _TERMINAL_JOB_STATES

    return True


def _run_preflight(args: argparse.Namespace) -> int:
    failures = 0
    for site in _sites(args):
        tools = remote.probe_site(site)
        policy = remote.check_policy(site)
        tool_state = "ok" if tools.returncode == 0 else "failed"
        policy_state = "ok" if policy.ok else "failed"
        print(f"{site}: tools={tool_state} policy={policy_state}")
        if policy.warnings:
            for warning in policy.warnings:
                print(f"{site}: policy warning: {warning}", file=sys.stderr)
        if tools.returncode or not policy.ok:
            failures += 1
    return 0 if failures == 0 else 1


def _prepare_submission_state(
    args: argparse.Namespace, config: RunConfig
) -> tuple[Path, dict[str, Any] | None]:
    state_dir = _state_dir(args.state_root, config.run_id)
    if not args.resume:
        remote.refuse_duplicate_submission(state_dir / "submission.json")
        previous = None
    else:
        previous = _load_json(state_dir / "submission.json")
        if previous.get("status") in {"fetched", "complete"}:
            raise remote.SubmissionError("the run already has a fetched complete artifact")
        if previous.get("commit") != config.commit:
            raise remote.SubmissionError("resume commit does not match the original run")
        previous_status = remote.job_status(str(previous["site"]), str(previous["job_id"]))
        if previous_status.returncode:
            raise remote.SubmissionError(
                "could not verify the previous job reached a terminal state; refusing duplicate"
            )
        if _job_is_active(previous_status):
            raise remote.SubmissionError("the previous OAR job is still active")
    state_dir.mkdir(parents=True, exist_ok=True)
    remote.write_json_atomic(state_dir / "spec.json", config.to_dict())
    return state_dir, previous


def _run_target(config: RunConfig, previous: dict[str, Any] | None) -> tuple[str, str]:
    if previous:
        return str(previous["site"]), str(previous["remote_root"])
    site = _select_site(config.sites)
    return site, _remote_root(remote.remote_home(site), config)


def _prepare_remote_run(
    source_dir: Path, state_dir: Path, site: str, run_root: str, commit: str
) -> None:
    remote.remote_prepare(site, run_root)
    remote.remote_upload_archive(source_dir, commit, site, f"{run_root}/source")
    remote.copy_file_to_remote(state_dir / "spec.json", site, f"{run_root}/spec.json")


def _record_submission(
    state_dir: Path,
    config: RunConfig,
    site: str,
    run_root: str,
    job_id: str,
    result: remote.CommandResult,
    previous: dict[str, Any] | None,
) -> dict[str, Any]:
    attempts = list(previous.get("attempts", [])) if previous else []
    attempts.append({"job_id": job_id, "site": site})
    submission = {
        "run_id": config.run_id,
        "status": "submitted",
        "site": site,
        "job_id": job_id,
        "commit": config.commit,
        "config": config.to_dict(),
        "remote_root": run_root,
        "resource": resource_spec(config),
        "property": memory_property(config),
        "submission_stdout": result.stdout,
        "submission_stderr": result.stderr,
        "attempts": attempts,
    }
    remote.write_json_atomic(state_dir / "submission.json", submission)
    return submission


def _run_submit(args: argparse.Namespace) -> int:
    source_dir = args.source_dir.resolve()
    ensure_clean_checkout(source_dir)
    config = _config(args, current_commit(source_dir))
    if args.dry_run:
        site = _sites(args)[0]
        print(f"dry run: site={site}")
        print(f"dry run: run_id={config.run_id}")
        print(f"dry run: resources={resource_spec(config)}")
        print(f"dry run: property={memory_property(config)}")
        print("dry run: no SSH connection or OAR submission")
        return 0

    state_dir, previous = _prepare_submission_state(args, config)
    site, run_root = _run_target(config, previous)
    _prepare_remote_run(source_dir, state_dir, site, run_root, config.commit)
    source_root = f"{run_root}/source"

    policy_before = remote.check_policy(site)
    _save_policy(state_dir, "policy-pre", policy_before)
    if not policy_before.ok:
        raise remote.SubmissionError(f"pre-submission usage policy check failed on {site}")

    command = render_submission_command(config, source_root, run_root)
    job_id, submission_result = remote.submit_job(site, command)
    submission = _record_submission(
        state_dir, config, site, run_root, job_id, submission_result, previous
    )

    policy_after = remote.check_policy(site)
    _save_policy(state_dir, "policy-post", policy_after)
    if not policy_after.ok:
        remote.cancel_job(site, job_id)
        submission["status"] = "cancelled-policy"
        remote.write_json_atomic(state_dir / "submission.json", submission)
        raise remote.SubmissionError(f"post-submission usage policy check failed on {site}")

    print(f"submitted run {config.run_id} to {site} as OAR job {job_id}")
    return 0


def _run_status(args: argparse.Namespace) -> int:
    state_dir, submission = _submission(args)
    result = remote.job_status(str(submission["site"]), str(submission["job_id"]))
    print(result.stdout, end="")
    if result.stderr:
        print(result.stderr, end="", file=sys.stderr)
    print(f"state: {state_dir}")
    return result.returncode


def _run_fetch(args: argparse.Namespace) -> int:
    state_dir, submission = _submission(args)
    publish_dir = state_dir / "publish"
    receipt = remote.fetch_publish(
        str(submission["site"]), str(submission["remote_root"]), publish_dir
    )
    if receipt.get("run_id") != args.run_id or receipt.get("commit") != submission.get("commit"):
        raise remote.SubmissionError("remote receipt identity does not match local submission")
    remote.write_json_atomic(state_dir / "receipt.json", receipt)
    for name in ("stdout.log", "stderr.log"):
        with suppress(remote.SubmissionError):
            remote.copy_file_from_remote(
                str(submission["site"]),
                f"{submission['remote_root']}/logs/{name}",
                state_dir / "logs" / name,
            )
    submission["status"] = "fetched"
    remote.write_json_atomic(state_dir / "submission.json", submission)
    print(f"fetched and verified {len(receipt['files'])} files into {publish_dir}")
    return 0


def _run_cancel(args: argparse.Namespace) -> int:
    state_dir, submission = _submission(args)
    result = remote.cancel_job(str(submission["site"]), str(submission["job_id"]))
    submission["status"] = "cancelled"
    remote.write_json_atomic(state_dir / "submission.json", submission)
    print(result.stdout, end="")
    return 0


def _run_cleanup(args: argparse.Namespace) -> int:
    if args.confirm_run_id != args.run_id:
        raise SystemExit("cleanup requires --confirm-run-id to exactly match --run-id")
    state_dir, submission = _submission(args)
    receipt = _load_json(state_dir / "receipt.json")
    publish_dir = state_dir / "publish"
    try:
        verify_receipt(publish_dir, receipt)
    except ValueError as error:
        raise remote.SubmissionError(
            f"refusing cleanup before artifact verification: {error}"
        ) from error
    if submission.get("status") not in {"fetched", "complete"}:
        raise remote.SubmissionError("refusing cleanup before a fetched complete artifact")
    status = remote.job_status(str(submission["site"]), str(submission["job_id"]))
    if _job_is_active(status):
        raise remote.SubmissionError("refusing cleanup while the OAR job may still be active")
    remote.cleanup_remote(str(submission["site"]), str(submission["remote_root"]), args.run_id)
    policy = remote.check_policy(str(submission["site"]))
    _save_policy(state_dir, "policy-final", policy)
    if not policy.ok:
        raise remote.SubmissionError("final usage policy check failed")
    print(f"cleaned exact remote run root for {args.run_id}")
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        return args.run(args)
    except remote.SubmissionError as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
