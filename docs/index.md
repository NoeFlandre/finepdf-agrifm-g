# AGRIFM-G

AGRIFM-G is a reproducible and fully automatic pipeline. It converts English FinePDF documents into two agriculture image splits.

## Split contract

`conventional` covers operational and conventional agriculture. It includes tractors, harvesters, tillage, irrigation equipment, silos, barns, farm vehicles, crop production, and related farm work.

`sustainable` covers sustainable and alternative agriculture. It includes permaculture, agroecology, agroforestry, hydroponics, aquaponics, organic and regenerative farming, conservation practices, composting, and related systems.

The pipeline classifies each document from its text. It uses extended English lexicons. It discards a document if the scores are equal or if there is no category evidence. Thus, no image is in both splits. The pipeline considers the usable embedded raster images. A caption is not necessary.

## Image checks

Cheap pixel checks remove the obvious blank images and scans. Then a pinned zero-shot CLIP screen removes only the images that are confidently document-like or unrelated. Borderline images stay in the dataset. The model does not use captions or document text as input.

The visual screen can make mistakes. It is a conservative filter. It is not a calibrated classifier. It removes these items:

- invalid images and tiny images;
- single-colour images and nearly blank images;
- images that are overwhelmingly flat-colour;
- near-uniform placeholders;
- dense page-shaped grayscale scans;
- images with extreme aspect ratios;
- duplicate bytes.

Full-page colour photographs stay eligible. The pipeline records the model revision, the scores, and the drop counts.

## Where the work runs

The heavy scaled extraction runs on Grid’5000. It uses resumable row-group checkpoints. The local machine does the orchestration and the final artifact verification.

Start with the [quickstart](quickstart.md). Then read the [schema](schema.md), the [known limitations](known-limitations.md), and the [glossary](glossary.md).
