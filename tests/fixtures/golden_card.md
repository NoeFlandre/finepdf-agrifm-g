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

A reproducible [FinePDF](https://huggingface.co/datasets/HuggingFaceFW/finepdfs) sample flattened to **one row per retained embedded raster image**. Each row keeps the image caption, document text and provenance for the AGRIFM-G experiment.

```python
from datasets import load_dataset

ds = load_dataset("me/thing", split="train")
ds[0]["image"]  # PIL.Image
```

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
| `n_colours` | int32 | distinct colours in a 256 px thumbnail — the appearance filter's main signal |
| `image_path` | string | path the image had in the build directory |
| `edge_density` | float32 | share of edge pixels in a 256 px thumbnail |
| `caption` | string | explicit figure caption extracted from the PDF page |
| `source_url` | string | URL the PDF was crawled from — the provenance record |
| `pdf_sha256` | string | hash of the retrieved PDF, so a refetch is verifiable |
| `text` | string | FinePDF's extracted text for the whole document |
| `n_images_in_doc` | int32 | how many images that document contributed |
| `extraction_version` | int32 | bumped when extraction changes stored bytes |

## Selection and filtering

- **Document gate:** documents below the 0.5% agronomy-lexicon word-share threshold are not downloaded; the threshold keeps every labelled positive.

- **Caption gate:** only a line beginning with a figure label — `Figure`, `Fig.`, `Photo`, `Plate`, `Image`, `Figura`, `Abb.` — plus an identifier (or, unnumbered, a colon or dash) is a caption; nearby page prose is ignored. The caption must contain a whole-word hit from the **phenotype lexicon** (organs, traits, symptoms, crops and growing scenes) and is published in `caption`. Generic agricultural context words such as *field*, *soil*, *yield* and *trial* are deliberately excluded there, because they select charts and maps rather than pictures of plants.

- **Cheap visual gate:** images must be at least 32 px on each side, non-single-colour, no wider than 20:1 and unique by SHA-256. A colour image must then use more than 8,000 colours and have edge density ≥ 0.18; near-white, flat-background, sparse line-art and low-texture images are dropped. A **greyscale** image is judged on texture alone (edge density ≥ 0.30), because an 8-bit greyscale photograph holds at most 256 colours and the colour-count rule would reject every scanned field photograph and electron micrograph on a technicality.

On 567 hand-labelled images, the strict appearance rules removed **77.6%** at **100% precision**, losing none of the 10 labelled keeps. This is not semantic agricultural filtering; unrelated photographs and vector figures can remain.

## Reproduce and limitations

The bounded run samples 3 English FinePDF shards with seed `42`, one row group each, so the sample is not an accident of a single crawl segment. PDFs are fetched from their original URLs and are not redistributed; `source_url` and `pdf_sha256` preserve provenance, but source licences are not audited.

```bash
uv run python -m scripts.grid5000 preflight
uv run python -m scripts.grid5000 submit --repo <repo>
uv run python -m scripts.grid5000 fetch --run-id <run-id>
```

- 40% of sampled documents were retrieved and parsed in this run; FinePDF URLs date from 2023 and many are unavailable.
- Only embedded raster images are extracted: vector figures, OCR text and page renderings are out of scope. Caption layouts outside the explicit-label rule are dropped, and multi-image pages are paired by reading order.

## Citation

```bibtex
@misc{finepdf_agrifm_g,
  title  = {me/thing},
  author = {Flandre, No\'e},
  year   = {2026},
  url    = {https://huggingface.co/datasets/me/thing}
}
```
