from pathlib import Path

import pytest
from scripts.grid5000.config import RunConfig
from scripts.grid5000.receipt import make_receipt
from scripts.grid5000.worker import (
    build_output_root,
    build_scaled_arguments,
    require_oar_environment,
)


def test_worker_refuses_frontend_execution(monkeypatch):
    for name in ("AGRIFM_G_GRID5000_JOB", "OAR_JOB_ID", "OAR_NODEFILE"):
        monkeypatch.delenv(name, raising=False)

    with pytest.raises(RuntimeError, match="OAR"):
        require_oar_environment()


def test_worker_requires_all_oar_markers():
    with pytest.raises(RuntimeError, match="OAR_NODEFILE"):
        require_oar_environment(
            {
                "AGRIFM_G_GRID5000_JOB": "1",
                "OAR_JOB_ID": "123",
            }
        )


def test_worker_uses_the_agriculture_output_profile(tmp_path: Path):
    config = RunConfig(commit="a" * 40, shards=(0,), row_groups=(0,))

    output_root = build_output_root(tmp_path)
    arguments = build_scaled_arguments(config, tmp_path)

    assert output_root == tmp_path / "out" / "agriculture-30000"
    assert str(output_root) in arguments
    assert "phenotype" not in " ".join(arguments)


def test_worker_publish_path_is_inside_the_agriculture_profile(tmp_path: Path):
    assert build_output_root(tmp_path) / "publish" == (
        tmp_path / "out" / "agriculture-30000" / "publish"
    )


def test_receipt_hashes_publish_files(tmp_path: Path):
    publish = tmp_path / "publish"
    publish.mkdir()
    (publish / "stats.json").write_text("{}", encoding="utf-8")
    nested = publish / "data"
    nested.mkdir()
    (nested / "part.parquet").write_bytes(b"payload")

    receipt = make_receipt("run-1", "123", publish)

    assert receipt["status"] == "complete"
    assert receipt["files"]["stats.json"]["sha256"]
    assert receipt["files"]["data/part.parquet"]["size"] == len(b"payload")
