# Known limitations

## Text is only a proxy

The text gate and the category assignment use exact English terms. A document can use an unexpected synonym. In this case, the pipeline misses the document. A document can also mention agriculture and contain unrelated figures. The category split is at document level. It is not at image level.

## Visual filtering is conservative

Cheap pixel checks remove blank images, near-solid images, tiny images, duplicates, and page-shaped grayscale scans. A pinned zero-shot CLIP model screens the remaining images. It compares farm photography with document figures and unrelated photos.

The model is not calibrated for this dataset. Its confidence can be wrong. The wording of the prompt has an effect. The conservative threshold keeps uncertain examples on purpose. Thus, some irrelevant graphics or page fragments can stay. Some unusual agricultural images can be lost. The per-row scores, the model revision, the prompt version, and the drop counts show this trade-off.

The committed image smoke-test examples are small. They check the broad difference between photo and noise. They do not estimate the coverage of each conventional or sustainable farming practice.

## Source availability

FinePDF stores source URLs. It does not store PDF bytes. Many older URLs are unavailable, moved, or access-controlled. The pipeline caches the failed fetches. Thus, a resumable Grid’5000 run does not retry the same failure again and again. A rebuild can give a different result when the public web changes.

## Embedded images only

The extractor reads embedded raster images. These items are out of scope:

- vector figures;
- page-rendered artwork;
- OCR-only figures;
- images that exist only as links.

## Captions are metadata

Caption extraction is best-effort. It is useful for inspection. Captions are optional. A caption never decides if the pipeline keeps an image. Caption text can be absent or incomplete. It can also be paired only approximately when a page has several images.

## Provenance and licensing

Every row has the source URL and the PDF and image hashes. The pipeline does not resolve or audit the licence of each source document. Downstream users must do this review for their use case.

## Reproducibility

The pipeline records these items: the sample seed, the source shards, the extraction version, the run specification, the checkpoints, and the receipt. The source web and the scheduler state are external. Thus, an exact byte reproduction is not guaranteed without the cached remote artifacts.
