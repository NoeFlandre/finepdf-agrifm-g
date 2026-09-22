# Known limitations

## Text is only a proxy

The text gate and category assignment use exact English terms. A document can use an unexpected synonym and be missed, or mention agriculture while containing unrelated figures. The category split is document-level, not image-level.

## Visual filtering is intentionally cheap

The pipeline removes obvious blank, degenerate, tiny, or duplicate images but does not understand scenes. Charts, maps, diagrams, screenshots, and unrelated photographs can survive if they are embedded in an accepted document. A future model-based filter would change the recall/diversity trade-off and is outside this release.

## Source availability

FinePDF stores source URLs rather than PDF bytes. Many older URLs are unavailable, moved, or access-controlled. Failed fetches are cached so a resumable Grid’5000 run does not retry the same failure indefinitely. A rebuild can therefore change as the public web changes.

## Embedded images only

The extractor reads embedded raster images. Vector figures, page-rendered artwork, OCR-only figures, and images represented only by links are out of scope.

## Captions are metadata

Caption extraction is best-effort and remains useful for inspection, but captions are optional and never decide whether an image is retained. Caption text may be absent, incomplete, or paired approximately when a page contains several images.

## Provenance and licensing

Every row carries the source URL and PDF/image hashes. The pipeline does not independently resolve or audit the licence of each source document; downstream users must perform that review for their use case.

## Reproducibility

The sample seed, source shards, extraction version, run specification, checkpoints, and receipt are recorded. The source web and scheduler state are external, so exact byte reproduction is not guaranteed without the cached remote artifacts.
