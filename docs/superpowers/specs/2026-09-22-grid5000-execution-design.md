# Grid’5000-only FinePDF execution design

## Goal

Move the bounded FinePDF extraction and packaging workload off the Mac and make the
Grid’5000 execution path reproducible, resumable, policy-aware, and site-agnostic.
Local work remains limited to code packaging, job submission, monitoring, artifact
retrieval, and verification.

## Scope

The Grid’5000 path covers the scaled `scripts/build_scaled_sample.py` workload. The
existing small local CLI build and offline unit tests remain available for development,
but the scaled build refuses to run unless it is inside an OAR allocation. No GPU is
requested: PDF fetching, parsing, image conversion, and packaging are CPU workloads.

## Architecture

1. `scripts/grid5000/config.py` contains pure, serialisable run configuration and the
   immutable run identity. The identity includes the source commit, FinePDF selection,
   seed, thresholds, worker count, and scheduler resources.
2. `scripts/grid5000/commands.py` renders shell-safe SSH/OAR/worker commands without
   performing I/O. This is the unit-test seam for the scheduler contract.
3. `scripts/grid5000/remote.py` is the small side-effect boundary for SSH, source archive
   transfer, OAR submission/status/cancellation, and artifact retrieval. It never runs the
   extraction pipeline locally.
4. `scripts/grid5000/worker.py` runs only on a reserved node. It checks the OAR environment,
   bootstraps the pinned `uv` version when a site does not provide it, executes the locked
   environment, and writes a receipt containing the commit, configuration, job identity,
   output hashes, and completion state.
5. `scripts/build_scaled_sample.py` uses atomic per-row-group staging. A killed job leaves
   only a `.part` directory that the exact same run can safely discard and rebuild on resume.

The default site pool is `grenoble,lille,lyon,nancy,nantes,rennes,sophia,toulouse,luxembourg`.
The submitter probes sites in order, preferring sites with `uv`, and submits exactly one job.
It never retries an ambiguous submission. A site can be selected explicitly for a subsequent
resume.

## Policy and resource controls

- The submitter runs `usagepolicycheck -t` immediately before and immediately after
  `oarsub`; both outputs are saved in the local run state.
- Submission fails unless the policy command exits successfully and reports `No jobs flagged`.
  Non-fatal Grid-wide DNS warnings remain visible in the receipt.
- The default request is one host, 16 CPU cores, 32 GB RAM, and a four-hour walltime. All
  values are configurable and validated as positive bounded values; no GPU is requested.
- A run ID is derived from the immutable configuration. Existing local state or a live remote
  job with that ID prevents duplicate submission.
- The worker requires `OAR_JOB_ID`, `OAR_NODEFILE`, and `AGRIFM_G_GRID5000_JOB=1`, so the
  scaled computation cannot accidentally run on the Mac or on a frontend.
- Secrets are not included in source archives, command lines, logs, or receipts. Hugging Face
  publication remains a separate explicitly requested step after the pulled artifact passes
  local verification.

## Checkpoint and artifact flow

The remote run root is `~/agrifm-g-runs/<run-id>`, with source, logs, cache, staged groups,
dataset, publish output, and receipt below that exact project-owned directory. The worker
resumes only when the stored run specification is byte-identical. After completion, the local
`fetch` command pulls only the publish directory, receipt, and logs, verifies the receipt and
file hashes, and leaves the remote cache untouched until an explicit cleanup command.

## Failure handling

- A failed policy check blocks submission.
- A failed preflight blocks submission.
- A non-zero `oarsub` result blocks without trying another site.
- A submission response without a parseable job ID is treated as ambiguous and is never retried.
- A running job can be inspected with `status` and cancelled with `cancel <job-id>`.
- A completed job is not called successful until the receipt reports `complete`, the package
  verifies, and the pulled local files match the recorded hashes.

## Testing

TDD covers pure run identity, resource validation, command rendering, policy-output parsing,
duplicate-submission guards, atomic staging/resume behavior, and the worker's local-execution
refusal. Remote calls use injected command runners in unit tests. A dry-run prints the exact
submission without contacting OAR; a later real run is the only integration test that allocates
Grid’5000 resources.
