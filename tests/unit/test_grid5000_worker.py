import os
import subprocess
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


def test_worker_uv_fallback_stays_inside_job_scratch(tmp_path: Path):
    repo = Path(__file__).resolve().parents[2]
    worker = repo / "scripts" / "grid5000" / "worker.sh"
    temp_root = tmp_path / "node-tmp"
    temp_root.mkdir()
    mock_bin = tmp_path / "mock-bin"
    mock_bin.mkdir()
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    spec = run_dir / "spec.json"
    spec.write_text("{}", encoding="utf-8")
    nodefile = tmp_path / "nodefile"
    nodefile.write_text("node-1\n", encoding="utf-8")
    log = tmp_path / "uv-calls.log"
    environment_log = tmp_path / "uv-environment.log"
    prefix_log = tmp_path / "uv-prefix.log"
    fake_python = mock_bin / "python3"
    fake_python.write_text(
        """#!/bin/sh
prefix=
while [ "$#" -gt 0 ]; do
    if [ "$1" = "--prefix" ]; then shift; prefix="$1"; fi
    shift
done
    if [ -z "$prefix" ]; then exit 91; fi
printf '%s\\n' "$prefix" > "$AGRIFM_G_TEST_PREFIX_LOG"
mkdir -p "$prefix/bin"
cat > "$prefix/bin/uv" <<'UV'
#!/bin/sh
printf '%s\\n' "$*" >> "$AGRIFM_G_TEST_LOG"
printf '%s|%s|%s|%s|%s\\n' \\
    "$TMPDIR" "$HF_HOME" "$PIP_CACHE_DIR" "$UV_CACHE_DIR" "$UV_PROJECT_ENVIRONMENT" \\
    >> "$AGRIFM_G_TEST_ENV_LOG"
UV
chmod +x "$prefix/bin/uv"
""",
        encoding="utf-8",
    )
    fake_python.chmod(0o755)
    environment = {
        **os.environ,
        "AGRIFM_G_GRID5000_JOB": "1",
        "AGRIFM_G_TEST_ENV_LOG": str(environment_log),
        "AGRIFM_G_TEST_LOG": str(log),
        "AGRIFM_G_TEST_PREFIX_LOG": str(prefix_log),
        "OAR_JOB_ID": "12345",
        "OAR_NODEFILE": str(nodefile),
        "PATH": f"{mock_bin}:/usr/bin:/bin",
        "TMPDIR": str(temp_root),
    }

    result = subprocess.run(
        ["bash", str(worker), "--spec", str(spec)],
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )

    scratch = temp_root / "agrifm-g-12345"
    assert result.returncode == 0, result.stderr
    assert not scratch.exists()
    calls = log.read_text(encoding="utf-8").splitlines()
    assert len(calls) == 2
    assert "sync" in calls[0]
    assert "run" in calls[1]
    assert prefix_log.read_text(encoding="utf-8").strip() == str(scratch / "uv-prefix")
    expected_paths = [
        str(scratch / "tmp"),
        str(scratch / "hf-cache"),
        str(scratch / "pip-cache"),
        str(scratch / "uv-cache"),
        str(scratch / "venv"),
    ]
    assert environment_log.read_text(encoding="utf-8").splitlines() == [
        "|".join(expected_paths),
        "|".join(expected_paths),
    ]
