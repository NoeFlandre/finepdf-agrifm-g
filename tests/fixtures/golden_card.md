---
pretty_name: FinePDF Agriculture Images
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
  - conventional-agriculture
  - sustainable-agriculture
  - finepdf
  - document-images
configs:
  - config_name: default
    data_files:
      - split: conventional
        path: data/conventional-*.parquet
      - split: sustainable
        path: data/sustainable-*.parquet
---

# me/thing

An English-only [FinePDF](https://huggingface.co/datasets/HuggingFaceFW/finepdfs) image dataset for general agricultural scenes and operations. Each row is one retained embedded raster image with document text, optional caption, and provenance.

## Load the splits

~~~python
from datasets import load_dataset

dataset = load_dataset("me/thing")
dataset["conventional"][0]["image"]  # PIL.Image
dataset["sustainable"][0]["image"]  # PIL.Image
~~~

## Contents

| | |
| --- | --- |
| rows (images) | 12 |
| parquet shards | 1 |
| documents sampled | 10 |
| documents retrieved and parsed | 4 (40%) |
| documents skipped by broad text gate | 0 |
| ambiguous documents skipped | 0 |
| documents contributing images | 0 |
| image width (min / median / max) | 0 / 0 / 0 px |
| image height (min / median / max) | 0 / 0 / 0 px |
| total pixels | 0.0 MP |
| text length (median) | 0 characters |
| conventional documents / images | 0 / 0 |
| sustainable documents / images | 0 / 0 |

## Schema

| field | type | meaning |
| --- | --- | --- |
| `image` | image | the extracted embedded raster image, decoded by `datasets` |
| `doc_id` | string | FinePDF document id, lowercased and made filesystem-safe |
| `agriculture_split` | string | the mutually exclusive conventional or sustainable split |
| `page` | int32 | 0-based page where the image was embedded |
| `image_index` | int32 | 0-based image position within its document |
| `width` | int32 | image width in pixels |
| `height` | int32 | image height in pixels |
| `image_sha256` | string | content hash, unique across the published rows |
| `image_path` | string | path in the temporary build directory |
| `n_colours` | int32 | distinct colours measured on a thumbnail |
| `edge_density` | float32 | thumbnail edge share, used only by narrow noise checks |
| `caption` | string | optional PDF caption when one was detected |
| `source_url` | string | original PDF URL for provenance |
| `pdf_sha256` | string | hash of the retrieved PDF |
| `text` | string | FinePDF English document text used for classification |
| `n_images_in_doc` | int32 | number of retained images from the document |
| `extraction_version` | int32 | version of the stored extraction contract |

## Selection and filtering

- The input is FinePDF's English `eng_Latn` text. A broad agriculture lexicon keeps documents worth downloading.
- Each passing document is assigned to the category with more exact matches from the extended conventional and sustainable agriculture lexicons. Ties and documents without category evidence are discarded. An image is never duplicated across splits.
- All usable embedded raster images from an accepted document are considered; captions are optional metadata and never a filter.
- Cheap sanity filters remove invalid, tiny, single-colour, nearly blank, overwhelmingly flat-colour, extreme-aspect-ratio, and duplicate images. Page-shaped grayscale scans with paper-like backgrounds and dense edges, plus nearly uniform low-colour placeholders, are also removed.

## Reproduce and limitations

The build sampled 3 English FinePDF shards with seed `42`. PDFs are fetched from their original URLs and are not redistributed; `source_url` and `pdf_sha256` preserve provenance, but source licences are not audited.

~~~bash
uv run python -m scripts.grid5000 preflight
uv run python -m scripts.grid5000 submit --repo <repo>
uv run python -m scripts.grid5000 fetch --run-id <run-id>
~~~

- 40% of sampled documents were retrieved and parsed in this run; FinePDF URLs date from 2023 and many are unavailable.
- Only embedded raster images are extracted. Vector figures, OCR-only figures and linked images are out of scope. The conservative page-scan check can miss tiled or colour scans; document-level classification can leave unrelated figures in an otherwise relevant paper; this is intentional for recall and diversity.

## Citation

~~~bibtex
@misc{finepdf_agrifm_g,
  title  = {me/thing},
  author = {Flandre, No\'e},
  year   = {2026},
  url    = {https://huggingface.co/datasets/me/thing}
}
~~~
