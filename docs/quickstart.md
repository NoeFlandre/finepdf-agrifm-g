# Quickstart

Install the pinned environment:

```bash
uv sync --all-groups
```

## Local checks

The local smoke test uses only the committed PDF fixture. It does not fetch FinePDF documents. Full builds run on Grid’5000:

```bash
make smoke-offline
```

## Scaled Grid’5000 build

WARNING: The scaled command is for Grid’5000 only. Do not run the heavy worker on the Mac.

```bash
uv run python -m scripts.grid5000 preflight
uv run python -m scripts.grid5000 submit --repo NoeFlandre/finepdf-agrifm-g
uv run python -m scripts.grid5000 status --run-id <run-id>
uv run python -m scripts.grid5000 fetch --run-id <run-id>
```

The default run uses one CPU host, 16 cores, 32 GB RAM, and a four-hour walltime. It installs the pinned CPU vision dependencies. It runs the pinned CLIP model only inside the reserved node. Model files, package caches, and the virtual environment stay in job-specific node-local temporary storage. The run removes them on exit.

The runner does `usagepolicycheck -t` on each configured site during preflight. It also does this check before and after the single submission. The run promotes each row group in one atomic step.

CAUTION: Rerun the same command with `--resume` only after the previous job is terminal.

After you fetch the run, verify these items before you publish: the local receipt, the parquet schema, the split counts, the image decoding, the hashes, and the disjointness. Then remove only the confirmed remote run:

```bash
uv run python -m scripts.grid5000 cleanup \
  --run-id <run-id> --confirm-run-id <run-id>
```

## Hugging Face loading

```python
from datasets import load_dataset

dataset = load_dataset("NoeFlandre/finepdf-agrifm-g")
conventional = dataset["conventional"]
sustainable = dataset["sustainable"]
```

The dataset viewer reads the same split-specific parquet files that the card describes.

## Quality checks

```bash
make qa
```
