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
- nearly uniform low-colour placeholders with very little edge detail;
- a single page-shaped grayscale raster with a paper-like background (at least 60%) and dense edges (at least 15%);
- antialiased near-solid placeholders with at most 16 coarse colour bins, a 75% dominant bin, and at most 10% edge density;
- extreme aspect ratios;
- exact duplicate image bytes.

There is no caption requirement. Captions are retained when extraction finds them, and captionless images remain eligible. After those inexpensive checks and global deduplication, pinned zero-shot CLIP compares each remaining image against agricultural-photography, document-figure, and unrelated-photo prompt groups. It rejects only when the agricultural-photo score is at most 0.12 and either negative class is at least 0.66. Scores are uncalibrated preferences; ambiguous images are retained. Captions and document text are not passed to CLIP.

The page-scan check is deliberately narrow: full-page colour photos and figures remain eligible. It can miss scans split across multiple raster objects or colour scans; it may also reject a page-sized grayscale figure that looks document-like. CLIP can also confuse unusual agricultural photos with graphics, so its pinned revision, prompts, scores, and drop counts are recorded for reproducibility.
