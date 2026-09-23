# AGRIFM-G

AGRIFM-G is a reproducible, fully automatic pipeline that turns English FinePDF documents into two agriculture image splits.

## Split contract

`conventional` covers operational and conventional agriculture: tractors, harvesters, tillage, irrigation equipment, silos, barns, farm vehicles, crop production, and related farm work.

`sustainable` covers sustainable and alternative agriculture: permaculture, agroecology, agroforestry, hydroponics, aquaponics, organic and regenerative farming, conservation practices, composting, and related systems.

Documents are classified from their text with extended English lexicons. A tie or missing category evidence is discarded, so no image is present in both splits. Usable embedded raster images are considered without requiring captions. Cheap pixel checks remove obvious blanks and scans; a pinned zero-shot CLIP screen then removes only confidently document-like or unrelated images. Borderline images remain, and captions or document text are not model inputs.

The visual screen can still make mistakes: it is a conservative filter, not a calibrated classifier. It removes invalid, tiny, single-colour, nearly blank, overwhelmingly flat-colour, near-uniform placeholders, dense page-shaped grayscale scans, extreme aspect ratios, and duplicate bytes. Full-page colour photographs remain eligible; model revision, scores, and drop counts are recorded.

Heavy scaled extraction runs on Grid’5000 with resumable row-group checkpoints. The local machine handles orchestration and final artifact verification.

Start with the [quickstart](quickstart.md), then read the [schema](schema.md) and [known limitations](known-limitations.md).
