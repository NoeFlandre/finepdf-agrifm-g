# Agriculture split policy

The pipeline implements this policy automatically from the document text. The policy is broad on purpose. The goal is useful agricultural diversity. The goal is not a narrow visual taxonomy.

## Conventional split

The `conventional` lexicon covers farm machinery and ordinary production operations. It includes tractors, combines, harvesters, planters, seeders, tillage, ploughing, spraying, irrigation equipment, silos, grain storage, barns, livestock facilities, farm vehicles, crop production, harvesting, and field work.

## Sustainable split

The `sustainable` lexicon covers practices and systems. It includes permaculture, agroecology, agroforestry, organic, regenerative, conservation, no-till, cover crops, crop rotation, intercropping, hydroponics, aquaponics, vertical farming, composting, rainwater harvesting, biological control, and low-input farming.

The lists are extended on purpose. They are English-only. The pipeline assigns a document to the category that has more exact lexicon hits. It excludes ties. It also excludes documents that have no category evidence. This document-level rule keeps the splits separate. But it can leave unrelated figures inside a relevant paper.

## Visual sanity checks

The pipeline drops only obvious failures:

- invalid or undecodable images;
- images below the minimum usable size;
- single-colour images, nearly blank images, or overwhelmingly flat-colour images;
- nearly uniform low-colour placeholders with very little edge detail;
- a single page-shaped grayscale raster with a paper-like background (at least 60%) and dense edges (at least 15%);
- antialiased near-solid placeholders with at most 16 coarse colour bins, a 75% dominant bin, and at most 10% edge density;
- extreme aspect ratios;
- exact duplicate image bytes.

A caption is not necessary. The pipeline keeps the captions that extraction finds. Images without a caption stay eligible.

## CLIP screen

The pipeline first does the cheap checks and the global deduplication. Then the pinned zero-shot CLIP model compares each remaining image with three prompt groups: agricultural photography, document figures, and unrelated photos. The model rejects an image only when both conditions are true:

- the agricultural-photo score is at most 0.12;
- one negative class is at least 0.66.

The scores are uncalibrated preferences. The pipeline keeps ambiguous images. The pipeline does not give captions or document text to CLIP.

## Limits of the checks

The page-scan check is narrow on purpose. Full-page colour photos and figures stay eligible. The check can miss scans that are split across several raster objects. It can also miss colour scans. It can reject a page-sized grayscale figure that looks like a document. CLIP can also confuse unusual agricultural photos with graphics. The pipeline records the pinned revision, the prompts, the scores, and the drop counts for reproducibility.
