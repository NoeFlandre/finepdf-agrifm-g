# ADR-0004: Filter document figures at image level

**Status:** Accepted on 2026-09-23

## Context

The published baseline contained 2,934 images from 30,000 sampled FinePDF documents. Of those,
2,670 had no caption, so caption rules could not provide broad coverage. A historical labeled
diagnostic set contained 567 images: the cheap appearance rules rejected only 44, all labeled
negative, while 523 labeled negatives still survived. The reviewed classes included charts,
diagrams, icons, screenshots, text pages, and unrelated images. The existing document-level text
classifier cannot distinguish those image types inside an otherwise agricultural paper.

The supplied examples also expose two pixel-filter misses: antialiased two-tone placeholders can
have many exact RGB values, and dense page scans just below the former edge-density cutoff can
escape the page-scan rule.

## Decision

Keep the document text gate and conventional/sustainable split assignment unchanged. Strengthen the
cheap image checks with coarse RGB colour bins and a modestly more tolerant grayscale page-scan
check. Then, after cheap checks and global duplicate removal, run a pinned CPU-only
`openai/clip-vit-base-patch32` checkpoint against three fixed prompt groups: agricultural photos,
document figures, and unrelated photos.

Remove an image only if its agriculture-photo preference is at most 0.12 and one negative-class
preference is at least 0.66. Keep uncertain cases. Captions and document text are never model
inputs. Publish the model scores and run configuration, and run the committed keep/reject image
examples before fetching PDFs.

All inference, model downloads, dependency caches, and the temporary virtual environment run on the
reserved Grid'5000 node. They use a job-specific node-local temporary directory that is removed on
exit; only checkpoints, logs, receipts, and publish artifacts remain in the run directory.

## Consequences

- Page scans and simple placeholders are caught before model inference.
- Charts, tables, maps, and unrelated figures can be removed independently of captions.
- Borderline agricultural images remain, preserving recall and visual diversity.
- The filter is a conservative screen, not a calibrated guarantee; its scores and drop counts are
  visible for future evaluation.
- The historical labeled diagnostic set is not consulted by the production build. Runtime
  filtering requires no human labeling or review.
