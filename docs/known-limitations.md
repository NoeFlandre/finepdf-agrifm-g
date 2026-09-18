# Known limitations

This is a proof of concept. What follows is deliberate, not overlooked.

## The sample is not representative

The POC samples from the first row group (1000 documents) of one English FinePDF shard.
*Why:* it makes a run cost seconds and a few tens of megabytes (see
[ADR-0002](adr/0002-finepdf-access-via-parquet-row-groups.md)).
*Cleanup:* sample row groups and shards as well as rows, once the pipeline is worth
scaling.

## Roughly a quarter of documents survive the fetch

FinePDF records the URL a document was crawled from, not its bytes. Crawls date from
2023, so many URLs are dead, moved, or now behind a login. In the committed run, 16 of
60 sampled documents were retrieved and parsed. The pipeline skips the rest silently.
*Cleanup:* fall back to a web archive, and report a per-run yield instead of dropping
failures on the floor.

## No agricultural or phenotyping filtering whatsoever

Every goal in [the dataset goal](index.md) — prioritising crops, leaves, ears, disease
symptoms and field scenes; excluding satellite imagery, icons, diagrams and plots — is
**deferred**. The POC extracts every usable raster image from every document it can read.
The images in the published sample are therefore mostly *not* agricultural.
*Cleanup:* this is the next piece of work, and the reason the domain is kept pure: a
relevance filter is a function from a record to a decision.

## Other deferred items

- **No deduplication** — the same figure reprinted across documents is stored twice.
- **No OCR and no page rendering** — only embedded raster images are extracted, so a
  figure drawn as vector graphics is invisible to us.
- **Minimal image normalisation** — images below 32 px on a side are dropped; nothing
  else is judged.
- **Licensing is inherited, not audited** — provenance is recorded per document
  (`source_url`) but no licence is resolved. Anything downstream of the POC needs that
  audit first.

## Quality-gate caveats

- **Mutation testing covers the domain only.** Adapters are exercised through fakes and
  fixtures instead; mutating I/O code would mostly measure the fakes.
- **Nine mutants survive, all equivalent**: rewritten exception *messages*, and
  `ensure_ascii=None` (falsy, so identical to `False`). The floor is set at 90 % rather
  than 100 % for exactly this reason.
- **The local venv lives outside the repository** in development because the working
  copy sits on a slow external volume. CI uses the default `.venv`.
