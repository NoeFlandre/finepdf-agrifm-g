# The labelled set

Ground truth for every filter that follows, built against
[the relevance policy](relevance-policy.md). Labels live in
`data/labels/relevance_v1.jsonl`, keyed by `image_sha256` so they survive any rebuild.

*Pass 1 — 2026-09-18. 567 images labelled by the assistant, single labeller. The builds hold 1064 images in total; the rest are unlabelled.*

## How the sample was drawn

At a base rate near 1 %, a uniform draw cannot produce enough positives to measure recall.
So the sample is **stratified**, and the two strata are kept apart in every number below:

| stratum | how it was drawn | documents | images labelled |
| --- | --- | --- | --- |
| `uniform` | seeded random draw over 3 000 FinePDF documents | 150 | 337 |
| `candidate` | the 350 documents scoring highest against `data/agronomy_lexicon.txt` | 350 | 230 (of 727 built) |

`scripts/sample_for_labelling.py` writes both manifests, `scripts/build_label_set.py`
materialises them, `scripts/contact_sheet.py` renders them for judging, and
`scripts/record_labels.py` records the verdicts.

## What the labels say

| stratum | images | keeps | rate |
| --- | --- | --- | --- |
| uniform | 337 | 1 | **0.30 %** |
| candidate | 230 | 9 | **3.9 %** |

*(Under policy v1 the candidate rate was 4.8 %. The v2 rulings — wild vegetation, forestry and
fungi all rejected — moved 22 labels to reject.)*

**The base rate of interesting images in unfiltered FinePDF is 0.30 %** — one image in
every 337. That figure comes from the uniform stratum alone and is the number every later
claim must be read against.

**Keyword scoring the document text lifts that to 4.8 %: roughly a 16× enrichment.** That is
the empirical case for the text gate, measured before the gate was built.

The 10 keeps break down as: family 1 (phenotyping) 3 — two leaf-disease close-ups and a
forage-sampling bench; family 2 (operational) 7 — bales on stubble, a tractor mowing, farmers
carrying harvested greens, a lamb, milking, a dairy barn, a grazed pasture; **family 3 (niche):
zero**.

What everything else is:

| class | count | | class | count |
| --- | --- | --- | --- | --- |
| logo | 106 | | portrait | 35 |
| unrelated | 89 | | screenshot | 20 |
| blank | 84 | | map | 14 |
| icon | 73 | | text_page | 12 |
| diagram | 57 | | signature | 3 |
| chart | 41 | | microscopy | 1 |

**Two thirds of all rejects are logos, blanks, icons, diagrams and charts** — 361 of 555.
None of them needs a model: that is the case for the pixel heuristics, and the ceiling on what
they can be expected to remove.

## Agreement

A second pass over 30 randomly drawn, already-labelled images agreed **30/30 on the label and
30/30 on the class**. That is a weaker result than it looks: the draw contained no keeps, so it
measures consistency on the easy majority class only. Agreement on positives is unmeasured, and
a second labeller — a human one — is the right way to fix that.

## The rulings that shaped this set

The policy was written before these images were seen. Five classes came up often enough to
need a ruling, and [policy v2](relevance-policy.md) decided all of them the same way —
**cultivated, not merely botanical**:

| gap | count | the question |
| --- | --- | --- |
| **silviculture** | 10 | rejected — forestry, not agriculture |
| **fungi** | 3 | rejected — foraging; cultivated production would count |
| **wild vegetation** | 3 | rejected — ecology, not cultivation |
| **people-in-a-field** | 2 | rejected — subject beats setting |
| **woody biomass** | 1 | rejected — fuel |

**Family 3 is therefore empty.** That is the most useful thing this pass found: FinePDF's
agricultural material is operational (family 2) and occasionally phenotypic (family 1), but
rare cultivated species do not appear in it at this scale. Niche coverage has to come from a
different source.

## What this set cannot do yet

- **It has 10 positives, not the 100 the issue asked for.** Reaching 100 at a 0.3 % base rate
  means labelling tens of thousands of uniform images, or leaning entirely on the candidate
  stratum and accepting its bias. This is a finding about FinePDF, not a shortfall of effort:
  **the source is thin in what we want.**
- **Recall estimates will be wide.** With 11 candidate-stratum positives, a filter that misses
  one moves measured recall by nine points.
- **Family 3 is empty.** The yield study should treat "does FinePDF contain niche agricultural
  imagery at all" as an open question, not a measurement problem.
