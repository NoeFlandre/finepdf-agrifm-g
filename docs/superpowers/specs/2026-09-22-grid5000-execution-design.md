# Grid’5000-only FinePDF execution design

## Goal

Move the bounded FinePDF extraction and packaging workload off the Mac. Make the Grid’5000
execution path reproducible, resumable, aware of the usage policy, and independent of the site.
On the Mac, do only these tasks: package the code, submit the job, monitor the job, retrieve the
artifacts, and verify the artifacts.

## Scope

The Grid’5000 path covers the scaled `scripts/build_scaled_sample.py` workload. The small local
CLI build and the offline unit tests stay available for development. The scaled build refuses to
run outside an OAR allocation. The job does not request a GPU. PDF fetching, parsing, image
conversion, and packaging are CPU workloads.

## Architecture

1. `scripts/grid5000/config.py` contains the pure, serialisable run configuration and the
   immutable run identity. The identity includes the source commit, the FinePDF selection, the
   seed, the thresholds, the worker count, and the scheduler resources.
2. `scripts/grid5000/commands.py` renders shell-safe SSH, OAR, and worker commands. It does no
   I/O. It is the unit-test seam for the scheduler contract.
3. `scripts/grid5000/remote.py` is the small boundary for side effects. It does SSH, source
   archive transfer, OAR submission, status, cancellation, and artifact retrieval. It never runs
   the extraction pipeline locally.
4. `scripts/grid5000/worker.py` runs only on a reserved node. It checks the OAR environment. It
   bootstraps the pinned `uv` version when a site does not supply `uv`. It runs the locked
   environment. It writes a receipt that contains the commit, the configuration, the job
   identity, the output hashes, and the completion state.
5. `scripts/build_scaled_sample.py` uses atomic staging for each row group. When a job is killed,
   only a `.part` directory remains. The exact same run can safely discard and rebuild that
   directory on resume.

The default site pool is `grenoble,lille,lyon,nancy,nantes,rennes,sophia,toulouse,luxembourg`.
The submitter probes the sites in order and prefers sites that have `uv`. It submits exactly one
job. It never retries an ambiguous submission. To resume, the operator can select a site
explicitly.

## Policy and resource controls

- The submitter runs `usagepolicycheck -t` immediately before and immediately after `oarsub`.
  It saves both outputs in the local run state.
- The submission fails unless the policy command exits successfully and reports
  `No jobs flagged`. The receipt keeps the non-fatal Grid-wide DNS warnings visible.
- The default request is one host, 16 CPU cores, 32 GB RAM, and a four-hour walltime. The
  operator can configure all values. The code validates them as positive bounded values. The job
  does not request a GPU.
- The system derives a run ID from the immutable configuration. Existing local state, or a live
  remote job with that ID, prevents a duplicate submission.
- The worker needs `OAR_JOB_ID`, `OAR_NODEFILE`, and `AGRIFM_G_GRID5000_JOB=1`. Thus the scaled
  computation cannot run by accident on the Mac or on a frontend.
- Source archives, command lines, logs, and receipts do not contain secrets. The Hugging Face
  publication is a separate step. Do it only on explicit request, after the pulled artifact
  passes the local verification.

## Checkpoint and artifact flow

The remote run root is `~/agrifm-g-runs/<run-id>`. The source, logs, cache, staged groups,
dataset, publish output, and receipt are below this exact project-owned directory. The worker
resumes only when the stored run specification is byte-identical. After completion, the local
`fetch` command pulls only the publish directory, the receipt, and the logs. It verifies the
receipt and the file hashes. It does not touch the remote cache until the operator uses an
explicit cleanup command.

## Failure handling

- A failed policy check blocks the submission.
- A failed preflight blocks the submission.
- A non-zero `oarsub` result blocks the submission. The system does not try another site.
- A submission response without a job ID that the system can parse is ambiguous. The system never
  retries it.
- Use `status` to inspect a running job. Use `cancel <job-id>` to cancel it.
- A completed job is not successful until three conditions are true: the receipt reports
  `complete`, the package verifies, and the pulled local files match the recorded hashes.

## Testing

TDD covers these items: the pure run identity, the resource validation, the command rendering,
the parsing of the policy output, the guards against duplicate submission, the atomic staging and
resume behavior, and the refusal of local execution by the worker. The unit tests use injected
command runners for remote calls. A dry-run prints the exact submission and does not contact OAR.
A later real run is the only integration test that allocates Grid’5000 resources.
