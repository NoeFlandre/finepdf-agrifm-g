# AGRIFM-G — FinePDF agriculture images

This repository builds an English-only image dataset from [FinePDF](https://huggingface.co/datasets/HuggingFaceFW/finepdfs).

> **Work in progress — prototype only, not a final dataset.** This iteration may be incomplete or contain mistakes. Its contents, labels, splits, and filters are provisional and may change. It is for experimentation only, not a validated or production-ready resource.

The current prototype snapshot has two mutually exclusive, provisional splits:

- `conventional`: tractors, machinery, silos, farm buildings, field operations, and other conventional or industrial agriculture scenes.
- `sustainable`: permaculture, agroecology, agroforestry, hydroponics, organic and regenerative practices, and related sustainable-farm scenes.

The pipeline is fully automatic. It applies a broad text gate, assigns each accepted document with extended category lexicons, and extracts embedded raster images. Cheap pixel checks remove blank, near-solid, and page-shaped grayscale scans; a pinned zero-shot CLIP screen then removes only confidently document-like or unrelated images. Uncertain images remain for diversity. Captions are optional metadata and never a filter.

## Local checks

Local PDF work is limited to the fixture-only smoke test; full builds run on Grid’5000:

```bash
make smoke-offline
```

## Run the scaled build on Grid’5000

Heavy PDF work runs only inside one reserved Grid’5000 node. The Mac submits, monitors, fetches, and verifies the artifact:

```bash
uv run python -m scripts.grid5000 preflight
uv run python -m scripts.grid5000 submit --repo NoeFlandre/finepdf-agrifm-g
uv run python -m scripts.grid5000 status --run-id <run-id>
uv run python -m scripts.grid5000 fetch --run-id <run-id>
```

The runner checks the usage policy before and after submission, requests bounded CPU resources, checkpoints each row group atomically, and refuses duplicate active submissions. Clean up a completed remote run only after local receipt and dataset verification:

```bash
uv run python -m scripts.grid5000 cleanup \
  --run-id <run-id> --confirm-run-id <run-id>
```

## Load the current prototype release

```python
from datasets import load_dataset

dataset = load_dataset("NoeFlandre/finepdf-agrifm-g")
dataset["conventional"][0]
dataset["sustainable"][0]
```

The card and viewer are generated from the same parquet files and statistics. Each row includes the decoded `image`, `agriculture_split`, model preference scores, source document text, optional caption, provenance URL, and content hashes.

Run the local quality gates with:

```bash
make qa
```

See [the quickstart](docs/quickstart.md), [the schema](docs/schema.md), and [the limitations](docs/known-limitations.md) for details.

## Layout

| Path | Purpose |
| --- | --- |
| `src/agrifm_g/domain/` | Pure classification, filtering, records, sampling, and verification logic |
| `src/agrifm_g/adapters/` | FinePDF, PDF, storage, packaging, and Hugging Face boundaries |
| `src/agrifm_g/pipeline.py` | Text gate, category assignment, fetching, and extraction |
| `src/agrifm_g/cli.py` | Small-sample build, package, verify, and publish commands |
| `scripts/build_scaled_sample.py` | Resumable agriculture-split build and packaging |
| `scripts/grid5000/` | Policy-aware Grid’5000 submission, worker, receipt, and fetch workflow |
| `data/*agriculture*lexicon.txt` | Broad and category-specific English vocabularies |
