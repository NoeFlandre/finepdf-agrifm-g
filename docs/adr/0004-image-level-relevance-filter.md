# ADR-0004: Filter document figures at image level

**Status:** Accepted on 2026-09-23

## Context

The published baseline had 2,934 images from 30,000 sampled FinePDF documents. Of these images,
2,670 had no caption. Thus, caption rules could not give broad coverage.

A historical labeled diagnostic set had 567 images. The cheap appearance rules rejected only 44
images. All 44 were labeled negative. But 523 labeled negatives stayed. The reviewed classes
included charts, diagrams, icons, screenshots, text pages, and unrelated images. The existing
document-level text classifier cannot distinguish these image types inside an agricultural paper.

The supplied examples also show two pixel-filter misses:

- Antialiased two-tone placeholders can have many exact RGB values.
- Dense page scans just below the former edge-density cutoff can pass the page-scan rule.

## Decision

Keep the document text gate and the conventional/sustainable split assignment unchanged.
Strengthen the cheap image checks with coarse RGB colour bins and a slightly more tolerant
grayscale page-scan check.

Then run a pinned CPU-only `openai/clip-vit-base-patch32` checkpoint. Run it after the cheap
checks and the global duplicate removal. It uses three fixed prompt groups: agricultural photos,
document figures, and unrelated photos.

Remove an image only if its agriculture-photo preference is at most 0.12 and one negative-class
preference is at least 0.66. Keep uncertain cases. Captions and document text are never model
inputs. Publish the model scores and the run configuration. Run the committed keep/reject image
examples before the pipeline fetches PDFs.

All inference, model downloads, dependency caches, and the temporary virtual environment run on
the reserved Grid'5000 node. They use a job-specific node-local temporary directory. The run
removes this directory on exit. Only checkpoints, logs, receipts, and publish artifacts stay in
the run directory.

## Consequences

- The pipeline catches page scans and simple placeholders before model inference.
- The pipeline can remove charts, tables, maps, and unrelated figures without captions.
- Borderline agricultural images stay. This keeps recall and visual diversity.
- The filter is a conservative screen. It is not a calibrated guarantee. Its scores and drop
  counts are visible for future evaluation.
- The production build does not use the historical labeled diagnostic set. The runtime filtering
  needs no human labeling or review.
