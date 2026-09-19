# Dataset schema

## Published (Hugging Face)

Parquet, **one row per image**, with `datasets.Features` so the Hub viewer renders it:

| field | type | meaning |
| --- | --- | --- |
| `image` | `Image()` | the PNG itself, decoded by `datasets` |
| `doc_id` | string | FinePDF id, lowercased and reduced to `[a-z0-9-_]` |
| `page` | int32 | 0-based page the image was embedded in |
| `image_index` | int32 | 0-based position within its document |
| `width`, `height` | int32 | pixels |
| `image_sha256` | string | content hash, unique across the dataset |
| `image_path` | string | path the image had in the build directory |
| `source_url` | string | where the PDF was crawled from — the provenance record |
| `pdf_sha256` | string | hash of the retrieved PDF, so a refetch is verifiable |
| `text` | string | FinePDF's extracted text for the whole document |
| `n_images_in_doc` | int32 | images that document contributed |
| `extraction_version` | int32 | bumped when extraction changes stored bytes |

```python
from datasets import load_dataset

ds = load_dataset("NoeFlandre/finepdf-agrifm-g", split="train")
ds[0]["image"]  # PIL.Image
```

Alongside it: `stats.json` (the numbers in the card) and the generated `README.md`.

## Build directory (local, not published)

`build` writes a working directory that `package` consumes:

```
out/dataset/
├── metadata.jsonl        one JSON record per document
├── pdfs/<doc_id>.pdf     the retrieved document, kept locally only
└── images/<doc_id>/000.png, 001.png, …
```

## What is dropped

Before an image exists at all, its **document** must pass the text gate: at least 0.3 % of its
words present in `data/agronomy_lexicon.txt`. Documents below that are never fetched.

Then, before an image is published it must survive, in order:

1. **degenerate** — 32 px minimum on each side, more than one colour, aspect ratio no wider
   than 20:1, not a byte-identical duplicate of something already kept;
2. **appearance** — at least 4096 distinct colours, under 80 % near-white, no single colour
   over 55 % of the frame, and not a limited palette with almost no edges.

Every drop is counted by reason in `stats.json`. The appearance rules remove 66.7 % of images
at 100 % precision on the [labelled set](labelling.md), losing none of its 10 positives.

**No *topical* filtering happens yet**: nothing in the pipeline knows what agriculture looks
like. See [known limitations](known-limitations.md).
