# Grid’5000-only FinePDF execution Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a runner for Grid’5000 that follows the usage policy, can resume, and works on any site. Make the scaled FinePDF build refuse local execution.

**Architecture:** The pure run configuration and the shell-command rendering are in `scripts/grid5000`. A thin subprocess/SSH boundary does the policy checks, the source transfer, the OAR submission, the monitoring, the retrieval, and the cleanup. A worker on a reserved node bootstraps the locked environment. It runs the existing scaled pipeline and writes a receipt that you can verify. The staging for each row group is atomic. Thus a killed allocation can resume and does not reuse partial output.

**Tech Stack:** Python 3.12, `dataclasses`, `subprocess`, `ssh`, `scp`, OAR, `usagepolicycheck`, `uv.lock`, pytest, Ruff, ty.

---

### Task 1: Pure Grid’5000 run identity and scheduler commands

**Files:**
- Create: `scripts/grid5000/__init__.py`
- Create: `scripts/grid5000/config.py`
- Create: `scripts/grid5000/commands.py`
- Test: `tests/unit/test_grid5000.py`

- [ ] **Step 1: Write failing tests for the run identity and the validation**

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

- [ ] **Step 2: Run the focused tests. Make sure they fail with the expected import or attribute errors**

Run:

```bash
/Volumes/Seagate\ M3/projects/finepdf-agrifm-g/.venv/bin/pytest tests/unit/test_grid5000.py -q
```

Expected: FAIL. `scripts.grid5000.config` does not yet define `RunConfig`.

- [ ] **Step 3: Implement the minimal immutable configuration**

Implement `RunConfig` with these parts:

- Validated positive values for `workers`, `cores`, `memory_gb`, `threshold`, and a walltime in `HH:MM:SS` format.
- Sorted tuples of unique shards and row groups.
- The nine configured site aliases.
- Canonical sorted JSON.
- A SHA-256 run suffix. Derive it from the configuration without the derived `run_id`.

- [ ] **Step 4: Write failing tests for the rendering of the resource and worker commands**

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

- [ ] **Step 5: Run the focused tests. Make sure the command tests fail**

Run the same focused pytest command. The failures must name the missing rendering functions. They must not show an environment error.

- [ ] **Step 6: Implement the pure command rendering and run GREEN**

Use `shlex.join`. Never use string interpolation for untrusted paths. Render one `oarsub` command and one worker command. Run the focused tests. Run Ruff on the two new modules.

- [ ] **Step 7: Commit the pure runner layer**

```bash
git add scripts/grid5000 tests/unit/test_grid5000.py
git commit -m "feat: add Grid5000 run configuration"
```

### Task 2: SSH/OAR boundary that follows the policy, and local state

**Files:**
- Create: `scripts/grid5000/remote.py`
- Modify: `scripts/grid5000/config.py`
- Test: `tests/unit/test_grid5000.py`

- [ ] **Step 1: Write failing tests for the parsing of the policy and the job ID**

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

- [ ] **Step 2: Run the tests. Make sure the parser functions are missing**

Run the focused pytest command. Make sure it fails on the undefined policy and job parser functions.

- [ ] **Step 3: Implement the injected subprocess boundary**

Add `CommandResult`, `PolicyResult`, `SubmissionError`, `run_ssh`, `check_policy`, `parse_policy_result`, `parse_job_id`, `remote_prepare`, `remote_upload_archive`, `submit_job`, `job_status`, `cancel_job`, and `fetch_artifacts`. Each command must use argv arrays or a shell-quoted command string. Each command must capture stdout and stderr and give the return codes to the caller. `fetch_artifacts` must use `scp` or `rsync` only after the remote receipt says `complete`.

- [ ] **Step 4: Add tests for the state of duplicate submissions**

```python
def test_existing_submission_state_blocks_duplicate_submission(tmp_path):
    state = tmp_path / "submission.json"
    state.write_text('{"job_id": "123", "status": "queued"}\n')
    with pytest.raises(SubmissionError, match="already submitted"):
        refuse_duplicate_submission(state)
```

- [ ] **Step 5: Implement the exact local state and the atomic JSON writes**

Save `spec.json`, `submission.json`, and the policy stdout and stderr in `out/grid5000/<run-id>/`. Refuse any existing state that contains a job ID. Do not retry an ambiguous `oarsub` response. Keep the remote root restricted to `~/agrifm-g-runs/<run-id>`. Reject path traversal in run IDs.

- [ ] **Step 6: Run the focused tests and commit**

```bash
/Volumes/Seagate\ M3/projects/finepdf-agrifm-g/.venv/bin/pytest tests/unit/test_grid5000.py -q
git add scripts/grid5000 tests/unit/test_grid5000.py
git commit -m "feat: add policy-aware Grid5000 submission boundary"
```

### Task 3: Scaled execution on Grid’5000 only, and atomic checkpoints

**Files:**
- Modify: `scripts/build_scaled_sample.py`
- Modify: `tests/unit/test_scaled_build.py`

- [ ] **Step 1: Write the failing test for the execution boundary**

```python
def test_scaled_build_requires_an_oar_job(monkeypatch):
    monkeypatch.delenv("AGRIFM_G_GRID5000_JOB", raising=False)
    monkeypatch.delenv("OAR_JOB_ID", raising=False)
    with pytest.raises(SystemExit, match="Grid5000"):
        require_grid5000_execution()
```

- [ ] **Step 2: Run the test. Make sure it fails because the guard does not exist**

Run `pytest tests/unit/test_scaled_build.py::test_scaled_build_requires_an_oar_job -q`. The expected failure is an undefined guard.

- [ ] **Step 3: Implement the guard and the atomic group staging**

At the start of `main`, require `AGRIFM_G_GRID5000_JOB=1`, `OAR_JOB_ID`, and `OAR_NODEFILE`. Build each group in `groups/.<slug>.part`. Rename it atomically to `<slug>` only after the metadata and files are complete. On `--resume`, remove only that exact stale `.part` directory, then rebuild. Keep the reuse of completed groups and the manifest order.

- [ ] **Step 4: Add tests for the cleanup of incomplete staging and the reuse of completed groups**

Use `tmp_path` to create `.s00000g0.part/partial`. Run the group-selection helper with `resume=True`. Assert that the partial directory is gone. Assert that the completed `s00000g1/metadata.jsonl` directory stays untouched. Also assert that the existing merge tests still pass.

- [ ] **Step 5: Run the focused scaled-build tests and commit**

```bash
/Volumes/Seagate\ M3/projects/finepdf-agrifm-g/.venv/bin/pytest tests/unit/test_scaled_build.py -q
git add scripts/build_scaled_sample.py tests/unit/test_scaled_build.py
git commit -m "feat: enforce Grid5000 scaled builds and atomic checkpoints"
```

### Task 4: Worker for the reserved node, and receipt that you can verify

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

- [ ] **Step 2: Run the tests. Make sure the worker functions are missing**

Run `pytest tests/unit/test_grid5000_worker.py -q`. The expected failures must come from the missing worker functions.

- [ ] **Step 3: Implement the worker environment checks and the receipt generation**

`worker.py` must do these steps:

- Verify that the stored spec matches the requested run.
- Find exactly `uv==0.11.16`, or install it. Do not print credentials.
- Run `uv sync --locked --no-dev`.
- Set `AGRIFM_G_GRID5000_JOB=1`.
- Call the scaled build with `--resume`.
- Write a receipt atomically. The receipt contains the job ID, the hostname, the commit, the spec JSON, the completion status, the package stats, and the SHA-256 hashes of each pulled artifact.

When a failure occurs, write `status: failed` and keep the remote run root.

- [ ] **Step 4: Implement the shell bootstrap contract**

`worker.sh` must use `set -euo pipefail` and reject missing OAR variables. It must use a pip cache local to the run. It must bootstrap `uv` only when `uv` is absent. It must `exec` the Python worker. It must not contain tokens or passwords. It must not run `rm -rf` on any path except the exact run root in the explicit cleanup command.

- [ ] **Step 5: Run the worker tests and the shell syntax check, then commit**

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

Test these three items:

- `python -m scripts.grid5000 --help` lists `preflight`, `submit`, `status`, `fetch`, `cancel`, and `cleanup`.
- `--dry-run` renders the chosen site and resource request. It does not call OAR.
- `cleanup` refuses to run unless you supply the exact run ID with `--confirm-run-id`.

- [ ] **Step 2: Implement the CLI subcommands**

- `preflight` checks every configured site.
- `submit` rejects a dirty checkout. It archives the exact commit and uploads the source and the spec. It runs the policy checks immediately before and immediately after one OAR submission. It saves the local state.
- `status` and `cancel` operate on the stored job ID.
- `fetch` verifies the remote receipt. Then it pulls the publish artifacts and hashes them.
- `cleanup` deletes only the exact remote run root, after explicit confirmation.

- [ ] **Step 3: Update the documentation and the Make targets**

Replace the local scaled-build command with the Grid’5000 submit and fetch flow. State that the Mac does not run the scaled extractor. Show the site pool and the default resources. Explain the resume and the policy gates. Add the targets `grid5000-preflight` and `grid5000-submit`. Do not change the local unit-test QA targets.

- [ ] **Step 4: Run the CLI-focused tests and commit**

```bash
/Volumes/Seagate\ M3/projects/finepdf-agrifm-g/.venv/bin/pytest tests/unit/test_grid5000_cli.py tests/unit/test_cli.py -q
git add scripts/grid5000 README.md docs/quickstart.md Makefile tests/unit
git commit -m "feat: expose Grid5000 execution workflow"
```

### Task 6: Full verification and real Grid’5000 execution

**Files:**
- Do not change the source unless a verification failure shows a tested defect.

- [ ] **Step 1: Run the local quality gates with isolated caches**

Run the focused tests, the full suite, Ruff, ty, the import architecture check, `git diff --check`, and the offline smoke test. Set `UV_CACHE_DIR=/private/tmp/finepdf-agrifm-g-uv-cache` and use isolated HF caches. Do not run the scaled build locally.

- [ ] **Step 2: Run the runner dry-run and the preflight of all sites**

```bash
UV_CACHE_DIR=/private/tmp/finepdf-agrifm-g-uv-cache \
  /Volumes/Seagate\ M3/projects/finepdf-agrifm-g/.venv/bin/python -m scripts.grid5000 submit --dry-run
UV_CACHE_DIR=/private/tmp/finepdf-agrifm-g-uv-cache \
  /Volumes/Seagate\ M3/projects/finepdf-agrifm-g/.venv/bin/python -m scripts.grid5000 preflight
```

Make sure the dry-run contains one bounded CPU-only request. Make sure the preflight records every site.

- [ ] **Step 3: Submit exactly one real job**

Run the real `submit` command from the clean committed branch. Record the selected site, the job ID, the source commit, the run ID, the policy outputs from before and after, and the scheduler request. Never retry when the submission response is ambiguous.

- [ ] **Step 4: Monitor and retrieve**

Use `status` until OAR reports completion. Then use `fetch`. Verify locally the receipt status, the package hashes, the schema, the stats, the row count, and the image decoding. If the job fails, inspect the logs. Resume the exact run only after you confirm that no job is active.

- [ ] **Step 5: Cancel leftovers, keep the verified artifacts, and report the exact evidence**

Cancel only a remaining job for this run. Run `usagepolicycheck -t` again on the submitting site. Keep the fetched publish artifact and the receipt locally. Use `cleanup --confirm-run-id` only after these checks. Report the job ID, the site, the commit, the run ID, the policy results, the artifact hashes, and any warning from the Grid-wide policy tool. Report the warnings separately from the pipeline results.
