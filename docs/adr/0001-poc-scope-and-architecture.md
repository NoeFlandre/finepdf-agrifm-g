# ADR-0001: POC scope and architecture boundaries

*Status: accepted — 2026-09-18*

## Context

AGRIFM-G needs a large and diverse corpus of ground-level agricultural images (see
[the dataset goal](../index.md)). First, we must know if we can convert a FinePDF document
into stored and addressable images and text, and if we can do it again with the same result.
A first pipeline that is written for scale hides this question under infrastructure.

## Decision

Build a very small, end-to-end POC. Enforce two boundaries from the start.

**Pure domain, isolated I/O.** `agrifm_g.domain` holds sampling, the record shape,
normalisation, and verification. Plain data goes in and plain data comes out. The domain must
not import adapters, the CLI, `httpx`, `pypdf`, `PIL`, `pyarrow`, or `huggingface_hub`. It must
not import `pathlib` also. Thus, paths are dataset-relative strings and the domain cannot touch
a filesystem. Every side effect is in `agrifm_g.adapters`. `agrifm_g.pipeline` composes the
adapters. `agrifm_g.cli` only parses arguments.

**Deep modules, small interfaces.** Each adapter has one verb: `rows`, `fetch`,
`extract_images`, `write_dataset`, `publish_dataset`. We already changed the FinePDF access
strategy one time, from the datasets-server to direct parquet reads. This change touched only
one file.

`import-linter` and a test check the allowed dependency direction:

```
cli → pipeline → adapters → domain
```

## Current scope and remaining boundary

The bounded experiment now includes cheap and deterministic gates:

- a broad agriculture text gate;
- document-level classification into two separate splits (conventional and sustainable);
- optional caption extraction;
- simple image appearance rules;
- exact-image deduplication.

These gates are broad proxies. They are not semantic image understanding.

These items are still out of scope:

- reliable exclusion of satellite images and diagrams;
- OCR;
- page rendering for vector figures;
- semantic deduplication;
- licensing resolution;
- broad multi-shard production scale.

They are product work beyond the lightweight POC.

## Consequences

- A run is cheap and reproducible. A seed and a size fully define the sample.
- The main logic is pure. Thus, we can test it exhaustively and mutation-test it.
- The cost is indirection. A document fetch goes through a protocol. It does not go through a
  direct call. At this size, this is a real cost. We accept it because the FinePDF access
  strategy is the part that is most likely to change.
