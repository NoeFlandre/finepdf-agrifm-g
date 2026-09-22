# AGRIFM-G

AGRIFM-G is a reproducible, fully automatic pipeline that turns English FinePDF documents into two agriculture image splits.

## Split contract

`conventional` covers operational and conventional agriculture: tractors, harvesters, tillage, irrigation equipment, silos, barns, farm vehicles, crop production, and related farm work.

`sustainable` covers sustainable and alternative agriculture: permaculture, agroecology, agroforestry, hydroponics, aquaponics, organic and regenerative farming, conservation practices, composting, and related systems.

Documents are classified from their text with extended English lexicons. A tie or missing category evidence is discarded, so no image is present in both splits. Every usable embedded raster image from an accepted document is retained; captions may be stored but are not required.

The only visual exclusions are cheap sanity checks for invalid, tiny, single-colour, nearly blank, overwhelmingly flat-colour, extreme-aspect-ratio, or exact-duplicate images. The pipeline does not claim semantic image understanding.

Heavy scaled extraction runs on Grid’5000 with resumable row-group checkpoints. The local machine handles orchestration and final artifact verification.

Start with the [quickstart](quickstart.md), then read the [schema](schema.md) and [known limitations](known-limitations.md).
