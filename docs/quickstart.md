# Quickstart

Install the pinned environment:

```bash
uv sync --all-groups
```

## Local checks

The local smoke test uses only the committed PDF fixture and does not fetch FinePDF documents;
full builds run on Grid’5000:

```bash
make smoke-offline
```

## Scaled Grid’5000 build

The scaled command is Grid’5000-only. Do not run the heavy worker on the Mac:

```bash
uv run python -m scripts.grid5000 preflight
uv run python -m scripts.grid5000 submit --repo NoeFlandre/finepdf-agrifm-g
uv run python -m scripts.grid5000 status --run-id <run-id>
uv run python -m scripts.grid5000 fetch --run-id <run-id>
```

The default run uses one CPU host, 16 cores, 32 GB RAM, and a four-hour walltime. It installs the pinned CPU vision dependencies and runs the pinned CLIP model only inside the reserved node. Model files, package caches, and the virtual environment live in job-specific node-local temporary storage and are removed on exit. The runner performs `usagepolicycheck -t` on every configured site during preflight and around the single submission. Each row group is promoted atomically; rerun the same command with `--resume` only after the previous job is terminal.

After fetching, verify the local receipt, parquet schema, split counts, image decoding, hashes, and disjointness before publishing. Then remove only the confirmed remote run:

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

The dataset viewer reads the same split-specific parquet files described in the card.

## Quality checks

```bash
make qa
```
