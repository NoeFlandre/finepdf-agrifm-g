# ADR-0003: Publish provenance, not the source PDFs

*Status: accepted — 2026-09-18*

## Context

The first release included each retrieved PDF. The PDFs were 78 MB of an 80 MB dataset. No
downstream user reads these files. Also, the licences of these documents are unknown. FinePDF
records where it crawled a document. It does not record what the user can do with the document.
To redistribute whole third-party PDFs under our repository name is to claim a right that we did
not check.

## Decision

Publish parquet only. For each row, keep `source_url` and `pdf_sha256`. Thus, anyone can fetch
the original again and prove that the bytes are the same as ours. The PDFs stay in the local
build cache. The cache is a build artefact. It is not a deliverable.

The card states the licensing in two parts:

- The **collection, extraction code and metadata** are CC-BY-4.0.
- The **images** keep the terms of their source documents. We do not resolve these terms.

Takedown requests go through the issue tracker of the repository.

## Consequences

- The published dataset becomes smaller, from ~80 MB to the images alone. The Hub viewer works.
- A full byte-for-byte rebuild depends on the open web. The web must still serve those URLs.
  With a 27 % fetch yield, it mostly does not. `pdf_sha256` makes this failure detectable. It
  is not silent.
- We still redistribute images that we extract from those documents. This claim is smaller than
  the redistribution of the documents. It is not a resolved claim. A per-document licence audit
  is still open work.
