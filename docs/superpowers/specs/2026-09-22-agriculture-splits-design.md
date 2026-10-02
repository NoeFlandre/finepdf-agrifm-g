# FinePDF Agriculture Splits Design

**Status:** Approved 2026-09-22. ADR-0004 changed the image filtering on 2026-09-23.

## Goal

Replace the phenotype-oriented FinePDF sample with two agriculture image splits. The splits
do not share documents. All documents are in English.

- `conventional`: operational farms, tractors, machinery, silos, barns, intensive and
  industrial agriculture, crop and livestock production, and related infrastructure.
- `sustainable`: permaculture, agroecology, agroforestry, organic and regenerative farming,
  hydroponics, aquaponics, conservation practices, biodiversity, and related systems.

The build must run on Grid'5000. It must not need human labelling or review. It must replace the
existing Hugging Face dataset in place.

## Decisions

### Text-first document classification

The FinePDF English `eng_Latn` text is the only semantic filter. A broad agriculture lexicon
filters the documents before the PDF download. Then two separate, extended lexicons classify each
document that passes as conventional or sustainable. The matching is deterministic and ignores
case. It matches whole words and whole phrases.

The classifier returns the category with the higher number of matching terms. The build discards
a document before the fetch when the counts are equal, or when no category has evidence. A
document has exactly one category. Its images cannot be in both splits.

Captions are optional metadata. Keep a caption when the extraction finds one. Never require a
caption. Never score a caption. Never use a caption to accept or reject an image, or to assign a
split.

### Image-level relevance filtering

The build considers all embedded raster images from the accepted documents. A caption is not
necessary. First, the build does cheap pixel checks that give high confidence:

- Accept only a valid, decodable image with both sides of at least 32 pixels.
- Reject single-colour, nearly blank, or overwhelmingly flat-colour images.
- Reject a single raster only when all of these conditions are true: its aspect ratio is within 3%
  of the PDF page, it is grayscale, at least 60% of it is near-white, and its edge density is at
  least 15%.
- Reject a low-information placeholder only when it has at most 64 thumbnail colours, one colour
  covers at least 75% of the pixels, and the edge density is at most 10%.
- Reject an antialiased near-solid placeholder when the coarse RGB quantization has at most 16
  bins, one bin covers at least 75% of the pixels, and the edge density is at most 10%.
- Reject images with an extreme separator-like aspect ratio.
- Remove exact duplicate image hashes.

After the deduplication, a pinned CPU-only CLIP model compares each image with three prompt
groups: agriculture-photo, document-figure, and unrelated-photo. Drop an image only when its
agriculture-photo score is 0.12 or less and a negative score is 0.66 or more. Keep the uncertain
examples. Captions and document text are not inputs to the model. Store the three class
preferences. Store the exact checkpoint, revision, prompt version, thresholds, and drop counts.
Before any PDF retrieval, run the committed keep/reject reference examples. Abort if the model
drops a known positive example, or if it rejects fewer than half of the obvious negative
examples.

### One-pass two-split packaging

One Grid'5000 worker processes each selected PDF one time. It stores the category on the
document record and deduplicates globally. It writes two parquet families:

```text
data/conventional-*.parquet
data/sustainable-*.parquet
```

The published schema includes `agriculture_split`, the CLIP class scores, the provenance, the
document text, the optional caption, and the appearance diagnostics. `stats.json` gives the
number of documents and images for each split, the model details, and all drop reasons. The
generated card has valid Hugging Face split metadata. It contains only English documentation
about agriculture.

### Grid'5000 and publication

The project keeps the existing policy-aware runner and changes it to use the agriculture output
path. The runner does these steps:

1. Run a preflight on every configured site and check the usage policy.
2. Submit exactly one bounded CPU job that can resume.
3. Checkpoint each shard or row-group build atomically.
4. Create and verify a receipt before it fetches the artifacts.
5. Validate both local parquet splits, the schema, the hashes, the row counts, and the images.
6. Replace the contents of the `NoeFlandre/finepdf-agrifm-g` repository in one upload.
7. Verify the live Hub revision, configs, splits, schema, and row counts independently.

Do not resume or publish an old phenotype run.

## Acceptance criteria

- No active production code needs a caption. No active production code imports the phenotype
  lexicon.
- The three committed agriculture lexicons are not empty and use lowercase. They handle phrases.
  They cover the requested machinery, conventional farming, permaculture, hydroponics,
  agroforestry, agroecology, and regenerative and organic practices.
- Unit tests and acceptance tests cover category assignment, ties, phrase matching, retention of
  images that have no caption, simple appearance filtering, split packaging, card metadata, and
  worker paths.
- Ruff, the format check, and the full test suite pass in the project environment.
- The Grid'5000 run has a complete receipt with both split files. No active job remains.
- The live Hugging Face dataset has exactly the intended agriculture splits and an English card.
  No old `train` parquet file and no phenotype description remain.
