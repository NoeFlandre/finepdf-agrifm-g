import json
import shlex

import pytest
from scripts.grid5000.commands import render_submission_command, render_worker_command
from scripts.grid5000.config import RunConfig


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


def test_submission_command_requests_cpu_only_bounded_resources():
    config = RunConfig(commit="a" * 40, cores=16, memory_gb=32, walltime="04:00:00")

    command = render_submission_command(config, "/home/u/run/source", "/home/u/run")

    assert "host=1/core=16,mem=32G,walltime=04:00:00" in command
    assert "gpu" not in command.lower()
    assert "usagepolicycheck" not in command


def test_worker_command_is_shell_quoted():
    command = render_worker_command("/home/u/run source", "/home/u/run/spec.json")

    assert shlex.quote("/home/u/run source/scripts/grid5000/worker.sh") in command
    assert "AGRIFM_G_GRID5000_JOB=1" in command
