# AGRIFM-G — FinePDF agriculture images

This repository builds an English-only image dataset from [FinePDF](https://huggingface.co/datasets/HuggingFaceFW/finepdfs).

> **Work in progress. This is a prototype only. It is not a final dataset.** This version can be incomplete or contain errors. The contents, labels, splits, and filters are provisional and can change. Use it for experiments only. It is not a validated or production-ready resource.

The current prototype snapshot has two splits. The splits are provisional. A document is in only one split.

- `conventional`: tractors, machinery, silos, farm buildings, field operations, and other conventional or industrial agriculture scenes.
- `sustainable`: permaculture, agroecology, agroforestry, hydroponics, organic and regenerative practices, and related sustainable-farm scenes.

The pipeline is fully automatic. It does these steps:

1. It applies a broad text gate.
2. It assigns each accepted document to a category. It uses extended category lexicons.
3. It extracts the embedded raster images.
4. Cheap pixel checks remove blank images, near-solid images, and page-shaped grayscale scans.
5. A pinned zero-shot CLIP screen removes only the images that are confidently document-like or unrelated.

The pipeline keeps uncertain images for diversity. A caption is optional metadata. A caption is never a filter.

## Local checks

On the local machine, do only the fixture-only smoke test. Full builds run on Grid’5000:

```bash
make smoke-offline
```

## Run the scaled build on Grid’5000

Heavy PDF work runs only inside one reserved Grid’5000 node. The Mac submits the job, monitors it, fetches the artifact, and verifies it:

```bash
uv run python -m scripts.grid5000 preflight
uv run python -m scripts.grid5000 submit --repo NoeFlandre/finepdf-agrifm-g
uv run python -m scripts.grid5000 status --run-id <run-id>
uv run python -m scripts.grid5000 fetch --run-id <run-id>
```

The runner checks the usage policy before and after the submission. It requests bounded CPU resources. It saves a checkpoint for each row group in one atomic step. It refuses duplicate active submissions.

WARNING: Do not clean up a remote run before you fetch it. Clean up a completed remote run only after you receive it locally and verify the dataset:

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

The card and the viewer come from the same parquet files and statistics. Each row has these items: the decoded `image`, `agriculture_split`, the model preference scores, the source document text, the optional caption, the provenance URL, and the content hashes.

To run the local quality gates, do this command:

```bash
make qa
```

For more data, read [the quickstart](docs/quickstart.md), [the schema](docs/schema.md), [the limitations](docs/known-limitations.md), and [the glossary](docs/glossary.md).

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
