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
| candidate | 230 | 11 | **4.8 %** |

**The base rate of interesting images in unfiltered FinePDF is 0.30 %** — one image in
every 337. That figure comes from the uniform stratum alone and is the number every later
claim must be read against.

**Keyword scoring the document text lifts that to 4.8 %: roughly a 16× enrichment.** That is
the empirical case for the text gate, measured before the gate was built.

The 12 keeps break down as: family 1 (phenotyping) 3 — two leaf-disease close-ups and a
forage-sampling bench; family 2 (operational) 7 — bales on stubble, a tractor mowing, farmers
carrying harvested greens, a lamb, milking, a dairy barn, a grazed pasture; family 3 (niche) 2
— wild bog and marsh plants.

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

## Open questions the images raised

The policy was written before these images were seen, and three classes came up often enough
to need a ruling. They are labelled `borderline`, never guessed, and **the labels are not final
until these are decided**:

| gap | count | the question |
| --- | --- | --- |
| **silviculture** | 10 | managed forest stands, clearcuts, tree planting. A crop on a 40-year rotation, or out of scope? |
| **fungi** | 3 | wild mushrooms as the subject. Not plants, but an agricultural product when cultivated. |
| **wild vegetation** | 3 | a sundew bog, a marsh in flower, a woodland stream. Plants are plainly the subject, and family 3 wants species breadth — but none of it is cultivated. |
| **people-in-a-field** | 2 | gardening and fieldwork photos where the person dominates the frame. Precedence rule 3 says portrait; the activity says practice. |
| **woody biomass** | 1 | a firewood pile: plant material, but fuel. |

Two of the wild-vegetation images were provisionally labelled `keep`/family 3. If that ruling
is reversed, family 3 drops to zero and the labelled set contains **no niche material at all**.

## What this set cannot do yet

- **It has 12 positives, not the 100 the issue asked for.** Reaching 100 at a 0.3 % base rate
  means labelling tens of thousands of uniform images, or leaning entirely on the candidate
  stratum and accepting its bias. This is a finding about FinePDF, not a shortfall of effort:
  **the source is thin in what we want.**
- **Recall estimates will be wide.** With 11 candidate-stratum positives, a filter that misses
  one moves measured recall by nine points.
- **Family 3 is barely represented**, and only by wild plants under a disputed ruling. The yield
  study should treat "does FinePDF contain niche agricultural imagery at all" as an open
  question, not a measurement problem.
