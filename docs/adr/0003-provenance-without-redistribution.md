# ADR-0003: Publish provenance, not the source PDFs

*Status: accepted — 2026-09-18*

## Context

The first release shipped every retrieved PDF: 78 MB of an 80 MB dataset, for files nothing
downstream reads. Worse, the licences of those documents are unknown — FinePDF records where
a document was crawled, not what may be done with it. Redistributing whole third-party PDFs
under our own repository name asserts a right we have not checked.

## Decision

Publish parquet only. For every row keep `source_url` and `pdf_sha256`, so anyone can refetch
the original and prove they got the same bytes we did. The PDFs stay in the local build cache,
which is a build artefact, not a deliverable.

Licensing is stated in two parts on the card: the **collection, extraction code and metadata**
are CC-BY-4.0; the **images** inherit whatever terms their source documents carry, which we do
not resolve. Takedown requests go through the repository's issue tracker.

## Consequences

- The published dataset drops from ~80 MB to the images alone, and the Hub viewer works.
- A full byte-for-byte rebuild depends on the open web still serving those URLs — which, at a
  27 % fetch yield, it largely does not. `pdf_sha256` makes that failure detectable rather than
  silent.
- We are still redistributing images extracted from those documents. That is a smaller claim
  than redistributing the documents, not a resolved one; a per-document licence audit remains
  open work.
