# AGRIFM-G

A minimal, reproducible pipeline that turns FinePDF documents into a
text + image dataset. Start with the [quickstart](quickstart.md); read
[known limitations](known-limitations.md) before trusting anything here.

## Image Dataset Goal

Build a **large, diverse dataset of ground-level agricultural images** extracted from FinePDF to pretrain **AGRIFM-G**, a visual foundation model for **plant phenotyping**.

Prioritize:
- Crops, plants, fruits, leaves, wheat ears, grains, seedlings
- Different species, cultivars and growth stages
- Diseases and biotic/abiotic stress
- Field scenes and agricultural activities
- Images useful for counting, detection, segmentation and phenotype characterization

Exclude:
- Satellite/remote-sensing imagery
- Icons, diagrams, plots and non-photographic figures
- Generic images unrelated to agriculture or phenotyping

## Dataset Types Sought

The corpus is built from three **complementary** dataset families. The objective is
complementarity, not raw image count.

### 1. Pure phenotyping
Precise images of plants, organs, canopies and plots, acquired via UAV, ground-based
platforms, greenhouses, etc.
*Profile: disparate, condensed, precise.*

### 2. Operational agricultural images
Photos of farms, tools, machinery and practices (grafting, pruning, irrigation,
harvesting, etc.).
*Profile: disparate, moderately condensed, diverse.*

### 3. Niche datasets
Infrequent species, rare crops, or very fine-grained taxonomies.
*Profile: disparate, sparsely condensed, moderately diverse.*

**Selection principle:** prefer datasets that fill gaps across these three families
rather than maximizing the total number of images.
