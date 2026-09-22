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
| `n_colours` | int32 | distinct colours in a 256 px thumbnail |
| `edge_density` | float32 | share of edge pixels in a 256 px thumbnail |
| `caption` | string | explicit `Figure`, `Fig.`, `Plate` or `Image` caption from the PDF page |
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

Before an image exists at all, its **document** must pass the text gate: at least 0.5 % of its
words present in `data/agronomy_lexicon.txt`. Documents below that are never fetched.

Then, before an image is published it must have an explicit caption whose text contains a
whole-word term from `data/phenotype_lexicon.txt`. A caption is recognised only when a PDF text
line starts with a figure label — `Figure`, `Fig.`, `Photo`, `Photograph`, `Plate`, `Pl.`,
`Image`, `Figura`, `Abb.` — followed by an identifier, or, for a page's only figure, by a colon
or a dash; nearby page prose is not used.

The two lexicons are deliberately different. The pre-fetch text gate uses the broad,
recall-tuned `agronomy_lexicon.txt`, because a document it rejects is never seen again. The
caption gate uses the narrow, precision-tuned `phenotype_lexicon.txt` — organs, traits,
symptoms, crops and growing scenes — and deliberately omits generic context words such as
*field*, *plot*, *trial*, *soil* and *yield*, which select charts and maps from economics, soil
and ecology papers rather than pictures of plants.

Before an image is published it must also survive, in order:

1. **degenerate** — 32 px minimum on each side, more than one colour, aspect ratio no wider
   than 20:1, not a byte-identical duplicate of something already kept;
2. **appearance** — under 80 % near-white and no single colour over 55 % of the frame, then
   one of two branches. A **colour** image needs more than 8,000 distinct colours, edge density
   at least 0.18, and must not be a limited palette with almost no edges. A **greyscale** image
   is judged on texture alone and needs edge density of at least 0.30: an 8-bit greyscale
   photograph holds at most 256 colours, so the colour-count rule cannot distinguish a scanned
   field photograph from a bar chart, while texture can. On the 33 greyscale images of the
   30-shard build, photographs and electron micrographs scored 0.300–0.382 and charts
   0.13–0.21; the nearest rejected image is a CT scan at 0.283.

Every drop is counted by reason in `stats.json`. The stricter appearance rules remove 77.6 % of
images at 100 % precision on the [labelled set](labelling.md), losing none of its 10 positives.

The caption gate is lexical, not semantic: nothing in the pipeline knows what the image itself
looks like. See [known limitations](known-limitations.md).
