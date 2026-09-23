# Known limitations

## Text is only a proxy

The text gate and category assignment use exact English terms. A document can use an unexpected synonym and be missed, or mention agriculture while containing unrelated figures. The category split is document-level, not image-level.

## Visual filtering is conservative

Cheap pixel checks remove blank, near-solid, tiny, duplicate, and page-shaped grayscale scans. A pinned zero-shot CLIP model screens remaining images for farm photography versus document figures and unrelated photos. It is not calibrated for this dataset: confidence can be wrong, prompt wording matters, and the conservative threshold intentionally keeps uncertain examples. Some irrelevant graphics or page fragments can therefore remain, while unusual agricultural images may be lost. The per-row scores, model revision, prompt version, and drop counts make this trade-off visible.

The committed image smoke-test examples are small and check broad photo-versus-noise behavior; they do not estimate coverage of every conventional or sustainable farming practice.

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
