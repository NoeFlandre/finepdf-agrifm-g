# AGRIFM-G — FinePDF agriculture images

This repository builds an English-only image dataset from [FinePDF](https://huggingface.co/datasets/HuggingFaceFW/finepdfs).
The published dataset has two mutually exclusive splits:

- `conventional`: tractors, machinery, silos, farm buildings, field operations, and other conventional or industrial agriculture scenes.
- `sustainable`: permaculture, agroecology, agroforestry, hydroponics, organic and regenerative practices, and related sustainable-farm scenes.

The pipeline is fully automatic. It applies a broad text gate, classifies each accepted document with extended category lexicons, extracts every usable embedded raster image, and applies only cheap visual sanity checks. Captions are optional metadata and never a filter.

## Run locally on a small sample

```bash
uv sync --all-groups
uv run agrifm-g build --manifest data/sample_manifest.json --out out/dataset
uv run agrifm-g verify --dataset out/dataset
uv run agrifm-g package --dataset out/dataset --out out/publish --repo <hf-repo>
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

## Load the published dataset

```python
from datasets import load_dataset

dataset = load_dataset("NoeFlandre/finepdf-agrifm-g")
dataset["conventional"][0]
dataset["sustainable"][0]
```

The card and viewer are generated from the same parquet files and statistics. Each row includes the decoded `image`, `agriculture_split`, source document text, optional caption, provenance URL, and content hashes.

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
