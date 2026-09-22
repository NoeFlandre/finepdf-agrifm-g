# Grid’5000-only FinePDF execution Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a policy-aware, resumable, site-agnostic Grid’5000 runner and make the scaled FinePDF build refuse local execution.

**Architecture:** Pure run configuration and shell-command rendering live under `scripts/grid5000`; a thin subprocess/SSH boundary performs policy checks, source transfer, OAR submission, monitoring, retrieval, and cleanup. A reserved-node worker bootstraps the locked environment, runs the existing scaled pipeline, and writes a verifiable receipt. Per-row-group staging becomes atomic so a killed allocation can resume without reusing partial output.

**Tech Stack:** Python 3.12, `dataclasses`, `subprocess`, `ssh`, `scp`, OAR, `usagepolicycheck`, `uv.lock`, pytest, Ruff, ty.

---

### Task 1: Pure Grid’5000 run identity and scheduler commands

**Files:**
- Create: `scripts/grid5000/__init__.py`
- Create: `scripts/grid5000/config.py`
- Create: `scripts/grid5000/commands.py`
- Test: `tests/unit/test_grid5000.py`

- [ ] **Step 1: Write failing tests for run identity and validation**

```python
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
    assert '"shards": [0, 2]' in config.to_json()
```

- [ ] **Step 2: Run the focused tests and verify the expected import/attribute failures**

Run:

```bash
/Volumes/Seagate\ M3/projects/finepdf-agrifm-g/.venv/bin/pytest tests/unit/test_grid5000.py -q
```

Expected: FAIL because `scripts.grid5000.config` does not yet define `RunConfig`.

- [ ] **Step 3: Implement the minimal immutable configuration**

Implement `RunConfig` with validated positive `workers`, `cores`, `memory_gb`, `threshold`,
and `HH:MM:SS` walltime; sorted unique shard and row-group tuples; the nine configured site
aliases; canonical sorted JSON; and a SHA-256 run suffix derived from the configuration without
the derived `run_id`.

- [ ] **Step 4: Write failing tests for resource and worker command rendering**

```python
def test_submission_command_requests_cpu_only_bounded_resources():
    config = RunConfig(commit="a" * 40, cores=16, memory_gb=32, walltime="04:00:00")
    command = render_submission_command(config, "/home/u/run/source", "/home/u/run")
    assert "host=1/core=16,mem=32G,walltime=04:00:00" in command
    assert "gpu" not in command.lower()
    assert "usagepolicycheck" not in command


def test_worker_command_is_shell_quoted():
    command = render_worker_command("/home/u/run/source dir", "/home/u/run/spec.json")
    assert "'source dir'" in command
    assert "AGRIFM_G_GRID5000_JOB=1" in command
```

- [ ] **Step 5: Run the focused tests to verify the command failures**

Run the same focused pytest command; expected failures should identify the missing rendering
functions rather than an environment error.

- [ ] **Step 6: Implement pure command rendering and run GREEN**

Use `shlex.join`, never string interpolation of untrusted paths, and render one `oarsub`
command plus a worker command. Run the focused tests and Ruff on the two new modules.

- [ ] **Step 7: Commit the pure runner layer**

```bash
git add scripts/grid5000 tests/unit/test_grid5000.py
git commit -m "feat: add Grid5000 run configuration"
```

### Task 2: Policy-aware SSH/OAR boundary and local state

**Files:**
- Create: `scripts/grid5000/remote.py`
- Modify: `scripts/grid5000/config.py`
- Test: `tests/unit/test_grid5000.py`

- [ ] **Step 1: Write failing tests for policy parsing and job ID parsing**

```python
def test_policy_is_accepted_only_when_no_jobs_are_flagged():
    assert parse_policy_result(0, "No jobs flagged\n").ok
    assert not parse_policy_result(0, "Error: database unavailable\n").ok
    assert not parse_policy_result(1, "No jobs flagged\n").ok


def test_oarsub_job_id_is_required_and_unambiguous():
    assert parse_job_id("OAR_JOB_ID=12345\n") == "12345"
    with pytest.raises(SubmissionError):
        parse_job_id("submitted but no id\n")
```

- [ ] **Step 2: Run the tests and confirm the missing parser failures**

Run the focused pytest command and verify it fails on undefined policy/job parser functions.

- [ ] **Step 3: Implement the injected subprocess boundary**

Add `CommandResult`, `PolicyResult`, `SubmissionError`, `run_ssh`, `check_policy`,
`parse_policy_result`, `parse_job_id`, `remote_prepare`, `remote_upload_archive`,
`submit_job`, `job_status`, `cancel_job`, and `fetch_artifacts`. Every command must use argv
arrays or a shell-quoted command string, capture stdout/stderr, and expose return codes to the
caller. `fetch_artifacts` must use `scp`/`rsync` only after the remote receipt says `complete`.

- [ ] **Step 4: Add duplicate-submission state tests**

```python
def test_existing_submission_state_blocks_duplicate_submission(tmp_path):
    state = tmp_path / "submission.json"
    state.write_text('{"job_id": "123", "status": "queued"}\n')
    with pytest.raises(SubmissionError, match="already submitted"):
        refuse_duplicate_submission(state)
```

- [ ] **Step 5: Implement exact local state and atomic JSON writes**

Persist `spec.json`, `submission.json`, and policy stdout/stderr under
`out/grid5000/<run-id>/`. Refuse any existing state containing a job ID; do not retry an
ambiguous `oarsub` response. Keep the remote root restricted to
`~/agrifm-g-runs/<run-id>` and reject path traversal in run IDs.

- [ ] **Step 6: Run focused tests and commit**

```bash
/Volumes/Seagate\ M3/projects/finepdf-agrifm-g/.venv/bin/pytest tests/unit/test_grid5000.py -q
git add scripts/grid5000 tests/unit/test_grid5000.py
git commit -m "feat: add policy-aware Grid5000 submission boundary"
```

### Task 3: Grid-only scaled execution and atomic checkpoints

**Files:**
- Modify: `scripts/build_scaled_sample.py`
- Modify: `tests/unit/test_scaled_build.py`

- [ ] **Step 1: Write the failing execution-boundary test**

```python
def test_scaled_build_requires_an_oar_job(monkeypatch):
    monkeypatch.delenv("AGRIFM_G_GRID5000_JOB", raising=False)
    monkeypatch.delenv("OAR_JOB_ID", raising=False)
    with pytest.raises(SystemExit, match="Grid5000"):
        require_grid5000_execution()
```

- [ ] **Step 2: Run the test and verify it fails because the guard is absent**

Run `pytest tests/unit/test_scaled_build.py::test_scaled_build_requires_an_oar_job -q`; the
expected failure is an undefined guard.

- [ ] **Step 3: Implement the guard and atomic group staging**

Require `AGRIFM_G_GRID5000_JOB=1`, `OAR_JOB_ID`, and `OAR_NODEFILE` at the start of
`main`. Build each group into `groups/.<slug>.part`, atomically rename it to `<slug>` only
after metadata and files are complete, and on `--resume` remove only that exact stale `.part`
directory before rebuilding. Preserve completed group reuse and manifest order.

- [ ] **Step 4: Add tests for incomplete staging cleanup and completed reuse**

Use `tmp_path` to create `.s00000g0.part/partial`, run the group-selection helper with
`resume=True`, and assert the partial directory is gone while a completed `s00000g1/metadata.jsonl`
directory remains untouched. Also assert the existing merge tests continue to pass.

- [ ] **Step 5: Run focused scaled-build tests and commit**

```bash
/Volumes/Seagate\ M3/projects/finepdf-agrifm-g/.venv/bin/pytest tests/unit/test_scaled_build.py -q
git add scripts/build_scaled_sample.py tests/unit/test_scaled_build.py
git commit -m "feat: enforce Grid5000 scaled builds and atomic checkpoints"
```

### Task 4: Reserved-node worker and verifiable receipt

**Files:**
- Create: `scripts/grid5000/worker.py`
- Create: `scripts/grid5000/worker.sh`
- Create: `scripts/grid5000/receipt.py`
- Test: `tests/unit/test_grid5000_worker.py`

- [ ] **Step 1: Write failing worker tests**

```python
def test_worker_refuses_frontend_execution(monkeypatch, tmp_path):
    for name in ("AGRIFM_G_GRID5000_JOB", "OAR_JOB_ID", "OAR_NODEFILE"):
        monkeypatch.delenv(name, raising=False)
    with pytest.raises(RuntimeError, match="OAR"):
        require_oar_environment()


def test_receipt_hashes_publish_files(tmp_path):
    publish = tmp_path / "publish"
    publish.mkdir()
    (publish / "stats.json").write_text("{}")
    receipt = make_receipt("run-1", "123", publish)
    assert receipt["status"] == "complete"
    assert receipt["files"]["stats.json"]["sha256"]
```

- [ ] **Step 2: Run tests and verify the expected missing-worker failures**

Run `pytest tests/unit/test_grid5000_worker.py -q`; expected failures must be due to missing
worker functions.

- [ ] **Step 3: Implement worker environment checks and receipt generation**

`worker.py` must verify the stored spec matches the requested run, locate or install exactly
`uv==0.11.16` without printing credentials, execute `uv sync --locked --no-dev`, set
`AGRIFM_G_GRID5000_JOB=1`, call the scaled build with `--resume`, and atomically write a
receipt containing job ID, hostname, commit, spec JSON, completion status, package stats, and
SHA-256 hashes for every pulled artifact. Failures write `status: failed` and preserve the
remote run root.

- [ ] **Step 4: Implement the shell bootstrap contract**

`worker.sh` must use `set -euo pipefail`, reject missing OAR variables, use a run-local pip
cache, bootstrap `uv` only when absent, and `exec` the Python worker. It must not contain
tokens, passwords, or `rm -rf` of any path other than the exact run root in the explicit cleanup
command.

- [ ] **Step 5: Run worker tests, shell syntax, and commit**

```bash
/Volumes/Seagate\ M3/projects/finepdf-agrifm-g/.venv/bin/pytest tests/unit/test_grid5000_worker.py -q
bash -n scripts/grid5000/worker.sh
git add scripts/grid5000 tests/unit/test_grid5000_worker.py
git commit -m "feat: add resumable Grid5000 worker"
```

### Task 5: User-facing CLI, documentation, and contracts

**Files:**
- Create: `scripts/grid5000/__main__.py`
- Create: `scripts/grid5000/cli.py`
- Modify: `README.md`
- Modify: `docs/quickstart.md`
- Modify: `Makefile`
- Modify: `tests/unit/test_cli.py`
- Create: `tests/unit/test_grid5000_cli.py`

- [ ] **Step 1: Write failing CLI contract tests**

Test that `python -m scripts.grid5000 --help` lists `preflight`, `submit`, `status`, `fetch`,
`cancel`, and `cleanup`; `--dry-run` renders the chosen site/resource request without calling
OAR; and `cleanup` refuses unless the exact run ID is supplied with `--confirm-run-id`.

- [ ] **Step 2: Implement the CLI subcommands**

`preflight` checks every configured site. `submit` rejects a dirty checkout, archives the exact
commit, uploads source/spec, runs policy checks immediately before and after one OAR submission,
and saves local state. `status` and `cancel` operate on the stored job ID. `fetch` verifies the
remote receipt then pulls and hashes publish artifacts. `cleanup` deletes only the exact remote
run root after explicit confirmation.

- [ ] **Step 3: Update docs and Make targets**

Replace the local scaled-build command with the Grid’5000 submit/fetch flow, document that the
Mac does not run the scaled extractor, show the site pool/resource defaults, explain resume and
policy gates, and add `grid5000-preflight` and `grid5000-submit` targets without changing the
local unit-test QA targets.

- [ ] **Step 4: Run CLI-focused tests and commit**

```bash
/Volumes/Seagate\ M3/projects/finepdf-agrifm-g/.venv/bin/pytest tests/unit/test_grid5000_cli.py tests/unit/test_cli.py -q
git add scripts/grid5000 README.md docs/quickstart.md Makefile tests/unit
git commit -m "feat: expose Grid5000 execution workflow"
```

### Task 6: Full verification and real Grid’5000 execution

**Files:**
- No source changes unless a verification failure identifies a tested defect.

- [ ] **Step 1: Run the local quality gates with isolated caches**

Run focused tests, the full suite, Ruff, ty, import architecture, `git diff --check`, and the
offline smoke test with `UV_CACHE_DIR=/private/tmp/finepdf-agrifm-g-uv-cache` and isolated HF
caches. Do not run the scaled build locally.

- [ ] **Step 2: Run the runner dry-run and all-site preflight**

```bash
UV_CACHE_DIR=/private/tmp/finepdf-agrifm-g-uv-cache \
  /Volumes/Seagate\ M3/projects/finepdf-agrifm-g/.venv/bin/python -m scripts.grid5000 submit --dry-run
UV_CACHE_DIR=/private/tmp/finepdf-agrifm-g-uv-cache \
  /Volumes/Seagate\ M3/projects/finepdf-agrifm-g/.venv/bin/python -m scripts.grid5000 preflight
```

Confirm the dry-run contains one CPU-only bounded request and the preflight records every site.

- [ ] **Step 3: Submit exactly one real job**

Run the real `submit` command from the clean committed branch. Record the selected site, job
ID, source commit, run ID, pre/post policy outputs, and scheduler request. Never retry if the
submission response is ambiguous.

- [ ] **Step 4: Monitor and retrieve**

Use `status` until OAR reports completion, then `fetch`. Verify the receipt status, package
hashes, schema, stats, row count, and image decoding locally. If the job fails, inspect logs and
resume the exact run only after confirming no active job exists.

- [ ] **Step 5: Cancel leftovers, preserve verified artifacts, and report exact evidence**

Cancel only any remaining job for this run, rerun `usagepolicycheck -t` on the submitting site,
retain the fetched publish artifact and receipt locally, and use `cleanup --confirm-run-id` only
after those checks. Report job ID, site, commit, run ID, policy results, artifact hashes, and
any Grid-wide policy-tool warning separately from pipeline results.
