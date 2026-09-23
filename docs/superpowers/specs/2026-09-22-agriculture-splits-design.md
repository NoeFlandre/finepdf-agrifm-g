# FinePDF Agriculture Splits Design

**Status:** Approved 2026-09-22; image filtering revised 2026-09-23 by ADR-0004

## Goal

Replace the phenotype-oriented FinePDF sample with two mutually exclusive, English-only
agriculture image splits:

- `conventional`: operational farms, tractors, machinery, silos, barns, intensive and
  industrial agriculture, crop and livestock production, and related infrastructure.
- `sustainable`: permaculture, agroecology, agroforestry, organic and regenerative farming,
  hydroponics, aquaponics, conservation practices, biodiversity, and related systems.

The build must run on Grid'5000, require no human labelling or review, and replace the existing
Hugging Face dataset in place.

## Decisions

### Text-first document classification

FinePDF's English `eng_Latn` text is the only semantic filter. A broad agriculture lexicon gates
documents before PDF download. Two separate, extended lexicons then classify each passing document
as conventional or sustainable. Whole-word and whole-phrase matching is deterministic and
case-insensitive.

The classifier returns the category with the higher number of matching terms. Ties and documents
with no category evidence are discarded before fetching. A document is assigned to exactly one
category; its images cannot appear in both splits.

Captions remain optional metadata when extraction finds them. They are never required, scored, or
used to accept/reject an image or assign a split.

### Image-level relevance filtering

All embedded raster images from accepted documents are considered, whether or not they have a
caption. Cheap, high-confidence pixel checks run first:

- valid decodable image with both sides at least 32 pixels;
- reject single-colour, nearly blank, or overwhelmingly flat-colour images;
- reject a single raster whose aspect ratio matches the PDF page within 3% only when it is
  grayscale, at least 60% near-white, and has at least 15% edge density;
- reject low-information placeholders only when there are at most 64 thumbnail colours, one
  colour covers at least 75% of pixels, and edge density is at most 10%;
- reject antialiased near-solid placeholders when coarse RGB quantization has at most 16 bins,
  one bin covers at least 75% of pixels, and edge density is at most 10%;
- reject extreme separator-like aspect ratios;
- remove exact duplicate image hashes.

After deduplication, a pinned CPU-only CLIP model compares each image with agriculture-photo,
document-figure, and unrelated-photo prompt groups. Drop only images with agriculture-photo score
at most 0.12 and either negative score at least 0.66. Keep uncertain examples. Captions and
document text are not model inputs. Store the three class preferences and the exact checkpoint,
revision, prompt version, thresholds, and drop counts. Run the committed keep/reject reference
examples before any PDF retrieval; abort if a known positive is dropped or fewer than half of the
obvious negatives are rejected.

### One-pass two-split packaging

One Grid'5000 worker processes each selected PDF once, stores the category on the document record,
deduplicates globally, and writes two parquet families:

```text
data/conventional-*.parquet
data/sustainable-*.parquet
```

The published schema includes `agriculture_split`, CLIP class scores, provenance, document text,
optional caption, and appearance diagnostics. `stats.json` reports document/image counts per split,
model details, and all drop reasons. The generated card uses valid Hugging Face split metadata and
contains only English, agriculture-focused documentation.

### Grid'5000 and publication

The existing policy-aware runner is retained and updated to the agriculture output path. It will:

1. preflight every configured site and check the usage policy;
2. submit exactly one bounded, resumable CPU job;
3. checkpoint each shard/row-group build atomically;
4. create and verify a receipt before fetching artifacts;
5. validate both local parquet splits, schema, hashes, row counts, and images;
6. replace the existing `NoeFlandre/finepdf-agrifm-g` repository contents in one upload;
7. independently verify the live Hub revision, configs, splits, schema, and row counts.

No old phenotype run will be resumed or published.

## Acceptance criteria

- No active production code requires a caption or imports the phenotype lexicon.
- The three committed agriculture lexicons are non-empty, lowercase, phrase-aware, and broad
  enough to cover the requested machinery, conventional farming, permaculture, hydroponics,
  agroforestry, agroecology, and regenerative/organic practices.
- Unit and acceptance tests cover category assignment, ties, phrase matching, captionless image
  retention, simple appearance filtering, split packaging, card metadata, and worker paths.
- Ruff, formatting, and the full test suite pass in the project environment.
- The Grid'5000 run has a complete receipt with both split files and no remaining active job.
- The live HF dataset has exactly the intended agriculture splits and an English card, with no old
  `train` parquet or phenotype description remaining.
