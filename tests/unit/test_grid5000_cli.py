from pathlib import Path

import pytest
from scripts.grid5000 import cli
from scripts.grid5000.remote import CommandResult, PolicyResult


def test_help_lists_all_grid_commands(capsys):
    with pytest.raises(SystemExit) as error:
        cli.main(["--help"])

    assert error.value.code == 0
    output = capsys.readouterr().out
    for command in ("preflight", "submit", "status", "fetch", "cancel", "cleanup"):
        assert command in output


def test_submit_dry_run_does_not_call_remote(monkeypatch, tmp_path: Path, capsys):
    monkeypatch.setattr(cli, "current_commit", lambda _source: "a" * 40)
    monkeypatch.setattr(cli, "ensure_clean_checkout", lambda _source: None)

    code = cli.main(
        [
            "submit",
            "--source-dir",
            str(tmp_path),
            "--state-root",
            str(tmp_path / "state"),
            "--site",
            "grenoble",
            "--shards",
            "0",
            "--row-groups",
            "0",
            "--dry-run",
        ]
    )

    assert code == 0
    output = capsys.readouterr().out
    assert "grenoble" in output
    assert "host=1/core=16,walltime=04:00:00" in output
    assert "memnode >= 32768" in output
    assert not (tmp_path / "state").exists()


def test_cleanup_requires_the_exact_run_id_confirmation(tmp_path: Path):
    run_id = "finepdf-" + "a" * 12 + "-" + "b" * 12

    with pytest.raises(SystemExit, match="confirm-run-id"):
        cli.main(
            [
                "cleanup",
                "--run-id",
                run_id,
                "--state-root",
                str(tmp_path / "state"),
            ]
        )


def test_submit_records_one_job_and_both_policy_gates(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(cli, "current_commit", lambda _source: "a" * 40)
    monkeypatch.setattr(cli, "ensure_clean_checkout", lambda _source: None)
    monkeypatch.setattr(
        cli.remote,
        "probe_site",
        lambda _site: CommandResult(returncode=0, stdout="uv=present\n", stderr=""),
    )
    monkeypatch.setattr(cli.remote, "remote_home", lambda _site: "/home/test")
    monkeypatch.setattr(cli.remote, "remote_prepare", lambda *_args: None)
    monkeypatch.setattr(cli.remote, "remote_upload_archive", lambda *_args: None)
    monkeypatch.setattr(cli.remote, "copy_file_to_remote", lambda *_args: None)
    monkeypatch.setattr(
        cli.remote,
        "submit_job",
        lambda *_args: ("123", CommandResult(0, "OAR_JOB_ID=123\n", "")),
    )
    policy = PolicyResult(returncode=0, output="No jobs flagged\n")
    monkeypatch.setattr(cli.remote, "check_policy", lambda _site: policy)

    code = cli.main(
        [
            "submit",
            "--source-dir",
            str(tmp_path),
            "--state-root",
            str(tmp_path / "state"),
            "--site",
            "grenoble",
            "--shards",
            "0",
            "--row-groups",
            "0",
        ]
    )

    assert code == 0
    submissions = list((tmp_path / "state").glob("*/submission.json"))
    assert len(submissions) == 1
    payload = submissions[0].read_text(encoding="utf-8")
    assert '"job_id": "123"' in payload
    assert (submissions[0].parent / "policy-pre.json").exists()
    assert (submissions[0].parent / "policy-post.json").exists()
