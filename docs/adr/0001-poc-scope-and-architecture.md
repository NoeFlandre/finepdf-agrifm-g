# ADR-0001: POC scope and architecture boundaries

*Status: accepted — 2026-09-18*

## Context

AGRIFM-G needs a large, diverse corpus of ground-level agricultural images (see
[the dataset goal](../index.md)). Before any of that can be built, we need to know
that a FinePDF document can be turned into stored, addressable images and text at all,
reproducibly. A first pipeline written for scale would bury that question under
infrastructure.

## Decision

Build a deliberately tiny, end-to-end POC, and enforce two boundaries from the start.

**Pure domain, isolated I/O.** `agrifm_g.domain` holds sampling, the record shape,
normalisation and verification. It is plain data in, plain data out: it may not import
adapters, the CLI, `httpx`, `pypdf`, `PIL`, `pyarrow`, `huggingface_hub` — or even
`pathlib`, so that paths are dataset-relative strings and the domain cannot be tempted
to touch a filesystem. Every side effect lives in `agrifm_g.adapters`; `agrifm_g.pipeline`
composes them; `agrifm_g.cli` only parses arguments.

**Deep modules, small interfaces.** Each adapter exposes one verb — `rows`, `fetch`,
`extract_images`, `write_dataset`, `publish_dataset` — so swapping the FinePDF access
strategy (which we already did once, from the datasets-server to direct parquet reads)
touches one file.

Allowed dependency direction, checked by `import-linter` and by a test:

```
cli → pipeline → adapters → domain
```

## Out of scope for the POC

No agricultural or phenotyping relevance filtering, no satellite/diagram exclusion,
no deduplication, no OCR, no image quality scoring, no scale. These are the actual
product goals; the POC exists to make them cheap to attempt, not to pre-empt them.

## Consequences

- A run is cheap and reproducible: a seed and a size fully determine the sample.
- The interesting logic is pure, so it can be tested exhaustively and mutation-tested.
- The cost is indirection: fetching a document goes through a protocol rather than a
  direct call. At this size that is a real cost, accepted because the FinePDF access
  strategy is the part most likely to change.
