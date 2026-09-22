# Agriculture split policy

This policy is implemented automatically from document text. It is intentionally broad: the goal is useful agricultural diversity, not a narrow visual taxonomy.

## Conventional split

The `conventional` lexicon covers farm machinery and ordinary production operations, including tractors, combines, harvesters, planters, seeders, tillage, ploughing, spraying, irrigation equipment, silos, grain storage, barns, livestock facilities, farm vehicles, crop production, harvesting, and field work.

## Sustainable split

The `sustainable` lexicon covers practices and systems such as permaculture, agroecology, agroforestry, organic, regenerative, conservation, no-till, cover crops, crop rotation, intercropping, hydroponics, aquaponics, vertical farming, composting, rainwater harvesting, biological control, and low-input farming.

The lists are deliberately extended and English-only. A document is assigned to the category with more exact lexicon hits. Ties and documents with no category evidence are excluded. This document-level rule keeps the splits mutually exclusive, but it can leave unrelated figures inside an otherwise relevant paper.

## Visual sanity checks

The pipeline drops only obvious failures:

- invalid or undecodable images;
- images below the minimum usable size;
- single-colour, nearly blank, or overwhelmingly flat-colour images;
- extreme aspect ratios;
- exact duplicate image bytes.

There is no caption requirement. Captions are retained when extraction finds them, and captionless images remain eligible. There is no semantic classifier, OCR gate, texture threshold, or line-art rule.
