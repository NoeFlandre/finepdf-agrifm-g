import json
import shlex
from pathlib import Path

import pytest
from scripts.grid5000.commands import (
    memory_property,
    render_submission_command,
    render_worker_command,
)
from scripts.grid5000.config import RunConfig
from scripts.grid5000.remote import (
    SubmissionError,
    parse_job_id,
    parse_policy_result,
    publish_remote_path,
    refuse_duplicate_submission,
)


def test_run_id_is_stable_for_the_same_configuration():
    first = RunConfig(commit="a" * 40, shards=(0, 2), row_groups=(0,), seed=7)
    second = RunConfig(commit="a" * 40, shards=(0, 2), row_groups=(0,), seed=7)

    assert first.run_id == second.run_id
    assert len(first.run_id.split("-")[-1]) == 12


def test_invalid_resources_are_rejected():
    with pytest.raises(ValueError, match="cores"):
        RunConfig(commit="a" * 40, cores=0)


def test_config_round_trips_as_sorted_json():
    config = RunConfig(commit="a" * 40, shards=(2, 0), row_groups=(1, 0))

    assert RunConfig.from_json(config.to_json()) == config
    payload = json.loads(config.to_json())
    assert payload["shards"] == [0, 2]
    assert payload["row_groups"] == [0, 1]
    assert payload["pipeline"] == "agriculture-splits-v1"


def test_pipeline_profile_changes_the_run_identity():
    agriculture = RunConfig(commit="a" * 40, pipeline="agriculture-splits-v1")
    other = RunConfig(commit="a" * 40, pipeline="other-profile")

    assert agriculture.run_id != other.run_id


def test_submission_command_requests_cpu_only_bounded_resources():
    config = RunConfig(commit="a" * 40, cores=16, memory_gb=32, walltime="04:00:00")

    command = render_submission_command(config, "/home/u/run/source", "/home/u/run")

    assert "host=1/core=16,walltime=04:00:00" in command
    assert memory_property(config) == "memnode >= 32768"
    assert "memnode >= 32768" in command
    assert "gpu" not in command.lower()
    assert "usagepolicycheck" not in command


def test_worker_command_is_shell_quoted():
    command = render_worker_command("/home/u/run source", "/home/u/run/spec.json")

    assert shlex.quote("/home/u/run source/scripts/grid5000/worker.sh") in command
    assert "AGRIFM_G_GRID5000_JOB=1" in command
    assert "env" in command


def test_remote_fetch_uses_the_agriculture_publish_path():
    assert publish_remote_path("/home/test/run") == "/home/test/run/out/agriculture-30000/publish/."


def test_policy_is_accepted_only_when_no_jobs_are_flagged():
    assert parse_policy_result(0, "No jobs flagged\n").ok
    assert not parse_policy_result(0, "Error: database unavailable\n").ok
    assert not parse_policy_result(1, "No jobs flagged\n").ok


def test_oarsub_job_id_is_required_and_unambiguous():
    assert parse_job_id("OAR_JOB_ID=12345\n") == "12345"
    with pytest.raises(SubmissionError):
        parse_job_id("submitted but no id\n")


def test_existing_submission_state_blocks_duplicate_submission(tmp_path: Path):
    state = tmp_path / "submission.json"
    state.write_text('{"job_id": "123", "status": "queued"}\n')

    with pytest.raises(SubmissionError, match="already submitted"):
        refuse_duplicate_submission(state)
