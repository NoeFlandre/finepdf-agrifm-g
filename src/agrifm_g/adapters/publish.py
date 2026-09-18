"""Push a built dataset to a Hugging Face dataset repository."""

from __future__ import annotations

import os
from collections.abc import Sequence
from pathlib import Path

from agrifm_g.domain.records import DocumentRecord

CARD_FILE = "README.md"


class PublishError(RuntimeError):
    """The dataset could not be published."""


def publish_dataset(dataset_dir: Path, repo_id: str, *, dry_run: bool = True) -> str:
    """Upload `dataset_dir` to `repo_id`. Returns the repository URL.

    The token is read from the environment only; nothing is ever written to the repo.
    """
    url = f"https://huggingface.co/datasets/{repo_id}"
    if dry_run:
        return url
    token = os.environ.get("HF_TOKEN")
    if not token:
        raise PublishError("HF_TOKEN is not set")
    from huggingface_hub import HfApi

    api = HfApi(token=token)
    api.create_repo(repo_id=repo_id, repo_type="dataset", private=False, exist_ok=True)
    api.upload_folder(repo_id=repo_id, repo_type="dataset", folder_path=str(dataset_dir))
    return url


CARD_TEMPLATE = """---
license: other
task_categories:
  - image-classification
  - image-feature-extraction
tags:
  - agriculture
  - plant-phenotyping
  - finepdf
  - proof-of-concept
---

# {repo_id}

A **proof of concept** for [AGRIFM-G](https://github.com/NoeFlandre/finepdf-agrifm-g):
{n_documents} documents drawn from [FinePDF](https://huggingface.co/datasets/HuggingFaceFW/finepdfs),
each stored with its source PDF, FinePDF's extracted text, and every usable embedded
raster image — {n_images} images in total.

## What this is not

It is **not** an agricultural image dataset yet. No relevance filtering is applied:
satellite imagery, diagrams, plots and unrelated photographs are all still present.
The goal of the POC is a reproducible, verifiable extraction pipeline; the filtering
that AGRIFM-G actually needs comes next.

## How it was built

Sampled with seed {seed} from one row group of one English FinePDF shard, then fetched
and extracted by the pipeline in the repository above:

```bash
uv run agrifm-g build --manifest data/sample_manifest.json --out out/dataset
uv run agrifm-g verify --dataset out/dataset
```

## Layout

- `metadata.jsonl` — one record per document: `doc_id`, `source_url`, `pdf_path`,
  `text`, `images[]`, `n_images`, `extraction_version`
- `pdfs/<doc_id>.pdf`
- `images/<doc_id>/NNN.png`

## Provenance and licensing

Each record keeps the `source_url` it was crawled from. Licences of the underlying
documents are **not** resolved or audited; treat this sample as research material only.
"""


def write_dataset_card(
    dataset_dir: Path, repo_id: str, records: Sequence[DocumentRecord], *, manifest_seed: int
) -> Path:
    """Write the dataset card that ships with the upload."""
    card = dataset_dir / CARD_FILE
    card.write_text(
        CARD_TEMPLATE.format(
            repo_id=repo_id,
            n_documents=len(records),
            n_images=sum(record.n_images for record in records),
            seed=manifest_seed,
        ),
        encoding="utf-8",
    )
    return card
