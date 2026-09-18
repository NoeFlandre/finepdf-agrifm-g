---
pretty_name: AGRIFM-G FinePDF image sample
license: cc-by-4.0
language:
  - en
size_categories:
  - n<1K
source_datasets:
  - HuggingFaceFW/finepdfs
task_categories:
  - image-feature-extraction
  - image-classification
tags:
  - agriculture
  - plant-phenotyping
  - finepdf
  - document-images
  - proof-of-concept
configs:
  - config_name: default
    data_files:
      - split: train
        path: data/train-*.parquet
---

# me/thing

A reproducible sample of [FinePDF](https://huggingface.co/datasets/HuggingFaceFW/finepdfs) documents, flattened to **one row per embedded image**, with the document's text and provenance carried alongside. Built by [finepdf-agrifm-g](https://github.com/NoeFlandre/finepdf-agrifm-g) as the first step towards AGRIFM-G, a visual foundation model for plant phenotyping.

```python
from datasets import load_dataset

ds = load_dataset("me/thing", split="train")
ds[0]["image"]  # PIL.Image
```

## What this is not

**No agricultural or phenotyping filtering is applied.** Satellite imagery, charts, diagrams, logos and unrelated photographs are all still present — the images here are mostly *not* agricultural. This release exists to prove the extraction pipeline is reproducible and verifiable; relevance filtering is the next piece of work.

## Contents

| | |
| --- | --- |
| rows (images) | 12 |
| parquet shards | 1 |
| documents sampled | 10 |
| documents retrieved and parsed | 4 (40%) |
| documents contributing images | 0 |
| image width (min / median / max) | 0 / 0 / 0 px |
| image height (min / median / max) | 0 / 0 / 0 px |
| total pixels | 0.0 MP |
| text length (median) | 0 characters |

## Schema

| field | type | meaning |
| --- | --- | --- |
| `image` | image | the extracted image itself, PNG, decoded by `datasets` |
| `doc_id` | string | FinePDF document id, lowercased and reduced to `[a-z0-9-_]` |
| `page` | int32 | 0-based page the image was embedded in |
| `image_index` | int32 | 0-based position of the image within its document |
| `width` | int32 | pixels |
| `height` | int32 | pixels |
| `image_sha256` | string | content hash; unique across the dataset |
| `image_path` | string | path the image had in the build directory |
| `source_url` | string | URL the PDF was crawled from — the provenance record |
| `pdf_sha256` | string | hash of the retrieved PDF, so a refetch is verifiable |
| `text` | string | FinePDF's extracted text for the whole document |
| `n_images_in_doc` | int32 | how many images that document contributed |
| `extraction_version` | int32 | bumped when extraction changes stored bytes |

## How it was built

Documents were sampled with seed `42` from a single row group of one English FinePDF shard, fetched from their original URLs, and their embedded raster images re-encoded to PNG. Images under 32 px on a side, single-colour images, images with an aspect ratio beyond 20:1, and exact duplicates (by SHA-256) are dropped; every drop is counted above.

```bash
uv run agrifm-g build   --manifest data/sample_manifest.json --out out/dataset
uv run agrifm-g package --dataset out/dataset --out out/publish --repo <repo>
```

## Provenance and licensing

Every row keeps the `source_url` its document was crawled from and the `pdf_sha256` of the retrieved file. The underlying documents' own licences are **not resolved or audited**: the collection, extraction code and metadata are released under CC-BY-4.0, but the images inherit whatever terms their source documents carry. Treat this as research material, and check provenance before any redistribution. Takedown requests via the repository's issue tracker.

## Limitations

- Roughly 40% of sampled documents were retrievable; FinePDF stores URLs from 2023 crawls, and many are dead or now gated.
- The sample is drawn from the first row group of one English shard, so it is not representative of FinePDF as a whole.
- Only embedded raster images are extracted: vector figures and page renderings are invisible to this pipeline, and no OCR is performed.

## Citation

```bibtex
@misc{agrifm_g_finepdf_poc,
  title  = {me/thing},
  author = {Flandre, No\'e},
  year   = {2026},
  url    = {https://huggingface.co/datasets/me/thing}
}
```
