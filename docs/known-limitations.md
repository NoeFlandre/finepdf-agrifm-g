# Known limitations

This is a proof of concept. What follows is deliberate, not overlooked.

## The sample is not representative

The current release covers one row group from each of thirty English FinePDF shards
(30,000 documents). Only 1,124 documents were retrieved and parsed, and 15 images were
published, so this remains a small and highly availability-biased sample — though spreading it
over thirty shards means it is no longer an accident of a single crawl segment.
*Why:* it keeps the cheap experiment bounded (see
[ADR-0002](adr/0002-finepdf-access-via-parquet-row-groups.md)).
*Cleanup:* more row groups per shard, and more shards, once the pipeline is worth
scaling further.

## The published dataset is parquet; the PDFs are not redistributed

Rows carry `source_url` and `pdf_sha256` instead of the source file
([ADR-0003](adr/0003-provenance-without-redistribution.md)). A byte-exact rebuild
therefore depends on the open web still serving those URLs, which it largely does not.

## Roughly 4 % of documents survive the fetch

FinePDF records the URL a document was crawled from, not its bytes. Crawls date from
2023, so many URLs are dead, moved, or now behind a login. In the current release,
1,124 of 30,000 sampled documents were retrieved and parsed (3.8 %), yielding 15 published
images from 10 documents. Documents below the text gate are skipped before fetching; failed
retrievals and failed parsing produce no row. Successful fetches are cached as PDFs and failed
fetches as `.gone` markers, so a rebuild does not repeatedly retry the same dead URL unless the
cache is removed.
*Cleanup:* fall back to a web archive, and report a per-run yield instead of dropping
failures on the floor.

## The relevance signal is textual, not visual

The POC keeps only images whose explicit caption contains a whole-word term from
`data/phenotype_lexicon.txt` — organs, traits, symptoms, crops and growing scenes. That list is
narrower than the pre-fetch agronomy lexicon and deliberately omits generic context words
(*field*, *plot*, *trial*, *soil*, *yield*), which select charts and maps rather than pictures of
plants. It is still a **text proxy**: nothing inspects the pixels for agricultural content, so a
chart captioned "Figure 3. Grain yield of six cultivars" is retained and a photograph with an
unlucky caption is lost.
*Cleanup:* a visual relevance filter is the next piece of work, and the reason the domain is
kept pure: a relevance filter is a function from a record to a decision. What it should decide
is specified in the [relevance policy](relevance-policy.md); only its textual half is applied to
the published rows.

## Other deferred items

- **No semantic deduplication** — exact image duplicates are removed, but the same figure
  reprinted with small changes across documents is stored twice.
- **No OCR and no page rendering** — only embedded raster images are extracted, so a
  figure drawn as vector graphics is invisible to us.
- **Caption recall is limited** — only text lines beginning with a figure label (`Figure`,
  `Fig.`, `Photo`, `Plate`, `Pl.`, `Image`, and the `Figura`/`Abb.` abbreviations) count as
  captions. Captions in unusual layouts, captions rendered as images, and uncaptioned but useful
  images are dropped; multi-image pages are paired by reading order. About 87 % of images that
  pass the visual rules never get a caption attached, which makes this the largest single loss
  in the pipeline.

  **Pairing by page geometry was tried and rejected.** Matching each image to the caption
  printed under it (via `pdfplumber` bounding boxes, joined to pypdf's images on pixel
  dimensions) captioned *fewer* images than reading order, not more: on 300 cached documents,
  6.3 % against 13.4 %, and 15 phenotype-qualifying images against 34. Two causes — roughly a
  quarter of images could not be joined to a box at all, and `extract_text_lines` groups a
  two-column page into lines spanning both columns, so a caption starting mid-line no longer
  matches the label pattern. Using geometry only to fill gaps left by reading order raised the
  caption count 240 → 253 but left phenotype hits unchanged at 34, so it bought a dependency
  and ~3x slower extraction for nothing. Anything that revisits this needs column
  segmentation first, not bounding boxes alone.
- **Cheap image filtering only** — images below 32 px on a side and plainly degenerate or
  non-photographic images are dropped, and the caption gate is lexical; semantic relevance is
  not judged. Two known leaks survive in the current release: a caption whose phenotype terms
  are used in a non-plant sense (`pathogen`, `seed` in a dermal-toxicology figure) and a
  colourful pathway *diagram* whose caption names an organ (`kernels`). Neither can be caught
  without looking at the pixels.
- **Licensing is inherited, not audited** — provenance is recorded per document
  (`source_url`) but no licence is resolved. Anything downstream of the POC needs that
  audit first.

## Quality-gate caveats

- **Mutation testing covers the domain only.** Adapters are exercised through fakes and
  fixtures instead; mutating I/O code would mostly measure the fakes.
- **Forty-five mutants survive out of 819 (94.5 % killed)**: the current survivors are
  equivalent or low-value cases such as rewritten exception *messages*, `ensure_ascii=None`
  (falsy, so identical to `False`), rounding digits that do not change any rendered value,
  and rewrites of size-category *labels*.
  The floor is set at 90 % rather than 100 % for exactly this reason.
- **The local venv lives outside the repository** in development because the working
  copy sits on a slow external volume. CI uses the default `.venv`.

## The appearance filter is not a topical filter

`agrifm_g.domain.appearance` drops images that are plainly not photographs: more than 8,000
colours and at least 0.18 edge density are required, in addition to rejecting almost entirely
white images, one flat colour over half the frame, or a limited palette with almost no edges.
Measured on the 567 labelled images it removes **77.6 % at 100 % precision**, keeping all 10
labelled positives.

What it cannot do:

- **Anti-aliased vector figures survive it.** A rendered diagram with soft edges carries tens of
  thousands of distinct colours and reads as photographic. One is in the published sample.
- **It has no idea what agriculture looks like.** The current release is not topically
  filtered, so unrelated photographs, diagrams and screenshots can survive.
- **Its thresholds rest on ten positives.** Re-fit them when the label set grows, with
  `scripts/fit_appearance.py`.


## The text gate lets generic vocabulary through

The lexicon contains words that are agricultural in most contexts and not in others — *field*,
*plant*, *species*, *yield*, *trial*. An amateur-radio newsletter talking about a "field day"
scores like an agronomy paper, and several are in the published sample.

A tightened lexicon without those 23 ambiguous terms skips 64 % of documents at full recall,
against 53 % for the current one — but its weakest positive sits only 1.3x above the threshold,
where the current setting has 1.2x. With ten labelled positives, margin is worth more than
saved fetches, so the generic terms stay. Revisit with `scripts/fit_text_gate.py` once the
label set is larger.
