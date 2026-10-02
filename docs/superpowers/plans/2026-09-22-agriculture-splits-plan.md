# FinePDF Agriculture Splits Implementation Plan

> Historical plan for the first agriculture-split release. ADR-0004 specifies the current iteration, which filters images at image level. See [ADR-0004](../../adr/0004-image-level-relevance-filter.md).

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the phenotype sample with a deterministic FinePDF dataset in which captions are optional. The dataset has two agriculture image splits, `conventional` and `sustainable`, that do not share documents. Build it on Grid'5000 and publish it in place on Hugging Face.

**Architecture:** The FinePDF document text passes a broad agriculture gate. Before the download, two extended lexicons that handle phrases classify the text. The build keeps every embedded raster image in an accepted document. It drops an image only when the image fails a small set of obvious visual sanity rules, or when the global hash deduplication removes it. One remote worker writes both split parquet families and a receipt. Verify the receipt independently before the publication.

**Tech Stack:** Python 3.12, pypdf, Pillow, PyArrow/Datasets, pytest/Hypothesis, Ruff, uv, Grid'5000 OAR, Hugging Face Hub.

---

### Task 1: Lock the new domain contract with failing tests

**Files:**
- Create: `src/agrifm_g/domain/agriculture.py`
- Modify: `src/agrifm_g/domain/textgate.py`
- Modify: `src/agrifm_g/adapters/lexicon.py`
- Create: `data/agriculture_lexicon.txt`
- Create: `data/conventional_agriculture_lexicon.txt`
- Create: `data/sustainable_agriculture_lexicon.txt`
- Test: `tests/unit/test_agriculture.py`
- Test: `tests/unit/test_textgate.py`
- Test: `tests/unit/test_lexicon.py`

- [x] **Step 1: Add the red tests for the phrase-aware scoring and the split assignment.**

~~~python
def test_phrase_terms_match_as_whole_phrases():
    assert lexicon_hits("A combine harvester crossed the field", {"combine harvester"}) == 1
    assert lexicon_hits("a harvester", {"combine harvester"}) == 0


def test_category_classifier_returns_only_the_stronger_category():
    assert (
        classify_document(
            "tractor combine harvester silo",
            conventional_terms={"tractor", "combine harvester", "silo"},
            sustainable_terms={"permaculture"},
        )
        is AgricultureSplit.CONVENTIONAL
    )


def test_category_classifier_discards_ties_and_missing_evidence():
    terms = {"tractor"}
    assert classify_document("tractor permaculture", terms, {"permaculture"}) is None
    assert classify_document("farm report", terms, {"permaculture"}) is None
~~~

Also assert these facts about each committed lexicon:

- It has at least 100 terms.
- It includes the requested vocabulary for machinery, permaculture, hydroponics, agroforestry, and agroecology.
- It contains only lowercase terms.
- It contains single-word entries and multi-word entries.

- [x] **Step 2: Run the focused tests. Make sure they fail because symbols are missing.**

Run:

~~~bash
uv run pytest tests/unit/test_agriculture.py tests/unit/test_textgate.py tests/unit/test_lexicon.py -q
~~~

Expected: collection failures or assertion failures. The new API and the new files do not exist yet.

- [x] **Step 3: Implement the minimal phrase-aware matcher and classifier.**

`textgate.py` tokenizes with `[a-z0-9]+`. It normalizes the lexicon entries into token tuples. It counts exact matches of one or more tokens with n-gram membership. `agronomy_score` stays a document score that is normalized by length. `agriculture.py` defines:

~~~python
class AgricultureSplit(StrEnum):
    CONVENTIONAL = "conventional"
    SUSTAINABLE = "sustainable"


def classify_document(
    text: str,
    conventional_terms: Collection[str],
    sustainable_terms: Collection[str],
) -> AgricultureSplit | None: ...
~~~

`lexicon.py` exposes `AGRICULTURE_PATH`, `CONVENTIONAL_PATH`, `SUSTAINABLE_PATH`, `load_lexicon`, and `load_agriculture_lexicons`. The broad loader must return the union of the generic agriculture file and both category files. Thus each category term can pass the gate before the fetch.

- [x] **Step 4: Fill the three extended English lexicons.**

The conventional file covers these topics: tractors, combines, planters, ploughs, harrows, cultivators, sprayers, use of fertilizer and pesticide, silos, grain handling, barns, feedlots, livestock, mechanized, intensive, industrial, and commercial farming, irrigation, harvesting, and farm operations.

The sustainable file covers these topics: permaculture, agroecology, agroforestry, silvopasture, food forests, organic, biodynamic, regenerative, and conservation agriculture, no-till, cover crops, compost, mulch, biochar, crop rotation, polyculture, intercropping, biodiversity, pollinators, hedgerows, biological pest control, rainwater harvesting, soil health, rotational grazing, hydroponics, aquaponics, aeroponics, vertical and indoor farming, greenhouses, aquaculture, community-supported agriculture, food sovereignty, and low-input and climate-resilient practices.

The broad file contains terms for these topics: general agriculture, crops, fields, farms, soil, livestock, plants, production, harvest, rural infrastructure, and food systems. All entries are English and lowercase. Comments start with `#`.

- [x] **Step 5: Run the focused tests and commit the domain contract.**

Run:

~~~bash
uv run pytest tests/unit/test_agriculture.py tests/unit/test_textgate.py tests/unit/test_lexicon.py -q
uv run ruff check src/agrifm_g/domain/agriculture.py src/agrifm_g/domain/textgate.py src/agrifm_g/adapters/lexicon.py tests/unit/test_agriculture.py tests/unit/test_textgate.py tests/unit/test_lexicon.py
~~~

Expected: all focused tests pass. Commit:

~~~bash
git add src/agrifm_g/domain/agriculture.py src/agrifm_g/domain/textgate.py src/agrifm_g/adapters/lexicon.py data/agriculture_lexicon.txt data/conventional_agriculture_lexicon.txt data/sustainable_agriculture_lexicon.txt tests/unit/test_agriculture.py tests/unit/test_textgate.py tests/unit/test_lexicon.py
git commit -m "feat: add agriculture split lexicons and classifier"
~~~

### Task 2: Make the extraction caption-optional and simplify the visual drops

**Files:**
- Modify: `src/agrifm_g/adapters/extraction.py`
- Modify: `src/agrifm_g/domain/appearance.py`
- Modify: `src/agrifm_g/domain/dedup.py`
- Modify: `src/agrifm_g/domain/records.py`
- Modify: `src/agrifm_g/adapters/storage.py`
- Test: `tests/unit/test_extraction.py`
- Test: `tests/unit/test_appearance.py`
- Test: `tests/unit/test_dedup.py`
- Test: `tests/unit/test_records.py`

- [x] **Step 1: Add red regression tests that prove images without a caption stay.**

Add a fake page with one embedded image and text that has no explicit caption. Assert that `extract_images(pdf_bytes)` returns the image with `caption == ""`. Assert that a page with a caption returns the image and the metadata. Also assert that no `caption_terms` argument exists, so no argument can filter the image out.

- [x] **Step 2: Run the extraction tests. Make sure the old API and behavior fail.**

Run:

~~~bash
uv run pytest tests/unit/test_extraction.py -q
~~~

Expected: the new behavior for images without a caption exposes the existing `zip` and caption-filter contract.

- [x] **Step 3: Remove the caption filtering. Keep the optional caption metadata.**

Change `extract_images(pdf_bytes)` and `_page_images` so that they accept no caption lexicon. Keep the pairing of captions by reading order. Always return every usable candidate with its matched caption, or with an empty string. The pipeline must never import `contains_lexicon_word` for the extraction.

- [x] **Step 4: Replace the strict appearance rules with rules for obvious degenerate images.**

Keep the dimension checks, the aspect-ratio checks, the exact hash deduplication, and the blank and flat checks. Keep two combined appearance rules:

~~~python
if metrics.near_white_share > 0.98:
    return AppearanceRule.MOSTLY_BLANK
if metrics.dominant_colour_share > 0.98:
    return AppearanceRule.FLAT_BACKGROUND
if metrics.n_colours <= 1:
    return AppearanceRule.FEW_COLOURS
if (
    metrics.n_colours <= 64
    and metrics.dominant_colour_share >= 0.75
    and metrics.edge_density <= 0.10
):
    return AppearanceRule.LOW_INFORMATION
~~~

Also mark a single grayscale embedded raster as a document-page scan when all of these conditions are true: its aspect ratio is within 3% of the page, its near-white share is at least 0.45, and its edge density is at least 0.18. Reject only this combined profile. Do not apply a general threshold for edge density, greyscale texture, line art, or colour count. Keep full-page colour photos eligible. Keep the metrics for diagnostics. Update `DropReason` and increase the extraction version. Test both supplied noise profiles. Also test that full-page photos and ordinary figures with few colours stay.

- [x] **Step 5: Run all extraction, appearance, and record tests, then commit.**

Run:

~~~bash
uv run pytest tests/unit/test_extraction.py tests/unit/test_appearance.py tests/unit/test_dedup.py tests/unit/test_records.py -q
~~~

Expected: all focused tests pass. Commit:

~~~bash
git add src/agrifm_g/adapters/extraction.py src/agrifm_g/domain/appearance.py src/agrifm_g/domain/dedup.py src/agrifm_g/domain/records.py src/agrifm_g/adapters/storage.py tests/unit/test_extraction.py tests/unit/test_appearance.py tests/unit/test_dedup.py tests/unit/test_records.py
git commit -m "feat: retain captionless images and simplify visual filtering"
~~~

### Task 3: Carry the document categories through the build and package two splits

**Files:**
- Modify: `src/agrifm_g/pipeline.py`
- Modify: `src/agrifm_g/adapters/storage.py`
- Modify: `src/agrifm_g/domain/rows.py`
- Modify: `src/agrifm_g/adapters/packaging.py`
- Modify: `src/agrifm_g/domain/stats.py`
- Modify: `src/agrifm_g/domain/card.py`
- Test: `tests/unit/test_pipeline.py`
- Test: `tests/unit/test_rows.py`
- Test: `tests/unit/test_packaging.py`
- Test: `tests/unit/test_stats.py`
- Test: `tests/unit/test_card.py`

- [x] **Step 1: Add failing tests for the category propagation and the split files.**

Test `build_with_outcome`:

~~~python
outcome = build_with_outcome(
    manifest,
    source,
    fetcher,
    out,
    terms={"agriculture"},
    conventional_terms={"tractor"},
    sustainable_terms={"permaculture"},
)
assert outcome.records[0].agriculture_split == "conventional"
assert outcome.ambiguous_out == 1
~~~

Test that the packaging writes `data/conventional-*.parquet` and `data/sustainable-*.parquet`. Test that it includes `agriculture_split`. Test that it never writes a `train-*.parquet` file. Load both files with `datasets.load_dataset`. Assert that each row has the matching split value.

- [x] **Step 2: Run the new tests. Make sure they fail as expected.**

Run:

~~~bash
uv run pytest tests/unit/test_pipeline.py tests/unit/test_rows.py tests/unit/test_packaging.py tests/unit/test_stats.py tests/unit/test_card.py -q
~~~

- [x] **Step 3: Extend the records and the pipeline with the category assignment.**

Add `agriculture_split: str = ""` to `DocumentRecord` and `DocumentPayload`. Serialize it. Include it in the flattened rows. Change the selection of the pipeline payload to these steps:

1. Score the text with the broad lexicon.
2. Classify the text with the two category lexicons.
3. When the build rejects a document, increment `gated_out` or `ambiguous_out`. Do not fetch the document.
4. Fetch each accepted row once. Call `extract_images(pdf_bytes)` without caption arguments.
5. Write the category on each accepted document record.

Keep the legacy behavior of the API without categories for small non-scaled tests. When the category lexicons are absent, the build has no restriction and the split is empty. The scaled build always supplies the new lexicons.

- [x] **Step 4: Implement the split-aware packaging and statistics.**

Group the flattened rows by the two `AgricultureSplit` values. Write the deterministic filenames `{split}-{index:05d}-of-{n_shards:05d}.parquet`. Remove stale `*.parquet` files before the write. Fail when a scaled record has an unknown or empty split. Add `agriculture_split` to `Features`.

Add `documents.text_gated`, `documents.ambiguous`, and a `splits` object that contains the document count and the image count for each split. Keep the totals and the drop reasons deterministic.

- [x] **Step 5: Rewrite the generated card for the two English splits.**

The front matter must declare:

~~~yaml
configs:
  - config_name: default
    data_files:
      - split: conventional
        path: data/conventional-*.parquet
      - split: sustainable
        path: data/sustainable-*.parquet
~~~

The prose must explain these topics: the classification of the text at document level, the optional captions, the broad retention of images, the simple visual sanity filters, the provenance, the reproduction on Grid'5000, and the counts of both splits. Remove all phenotype wording, the old precision claims, and the `train` loading examples.

- [x] **Step 6: Run the focused packaging tests and commit.**

Run:

~~~bash
uv run pytest tests/unit/test_pipeline.py tests/unit/test_rows.py tests/unit/test_packaging.py tests/unit/test_stats.py tests/unit/test_card.py -q
uv run ruff check src/agrifm_g/pipeline.py src/agrifm_g/adapters/storage.py src/agrifm_g/domain/rows.py src/agrifm_g/adapters/packaging.py src/agrifm_g/domain/stats.py src/agrifm_g/domain/card.py tests/unit
~~~

Expected: the focused tests and Ruff pass. Commit:

~~~bash
git add src/agrifm_g/pipeline.py src/agrifm_g/adapters/storage.py src/agrifm_g/domain/rows.py src/agrifm_g/adapters/packaging.py src/agrifm_g/domain/stats.py src/agrifm_g/domain/card.py tests/unit/test_pipeline.py tests/unit/test_rows.py tests/unit/test_packaging.py tests/unit/test_stats.py tests/unit/test_card.py tests/fixtures/golden_card.md
git commit -m "feat: package conventional and sustainable splits"
~~~

### Task 4: Refactor the scaled build and the Grid'5000 worker

**Files:**
- Modify: `scripts/build_scaled_sample.py`
- Modify: `scripts/grid5000/worker.py`
- Modify: `scripts/grid5000/remote.py`
- Modify: `scripts/grid5000/config.py`
- Modify: `tests/unit/test_scaled_build.py`
- Modify: `tests/unit/test_grid5000_worker.py`
- Modify: `tests/unit/test_grid5000.py`
- Modify: `tests/unit/test_grid5000_cli.py`

- [x] **Step 1: Add red tests for the agriculture output path and for no phenotype inputs.**

Assert that the worker arguments use `out/agriculture-30000`. Assert that the publish path matches it. Assert that the scaled script loads all three agriculture lexicons. Assert that no rendered worker command uses the old phenotype path. Assert that the existing command shape `env AGRIFM_G_GRID5000_JOB=1` stays valid.

- [x] **Step 2: Run the Grid-focused tests. Make sure they fail.**

Run:

~~~bash
uv run pytest tests/unit/test_scaled_build.py tests/unit/test_grid5000_worker.py tests/unit/test_grid5000.py tests/unit/test_grid5000_cli.py -q
~~~

- [x] **Step 3: Update the scaled build.**

Use `out/agriculture-30000` as the default. Load the broad and category lexicons. Remove every `caption_terms` argument. Return the text-gated and ambiguous counts from each staged group. Give the category counts to `package_dataset`. The resume validation must recompute the text decisions and the category decisions from the same source rows. It must reject incomplete records and records with an unknown category.

- [x] **Step 4: Update the worker, the fetch path, and the run identity.**

Point the worker and the remote fetch logic at `out/agriculture-30000`. Add a configuration or profile marker, such as `pipeline="agriculture-splits-v1"`, to `RunConfig`. Thus a phenotype spec cannot collide with the agriculture output when the commit is the same. Keep the bounded OAR resources, the atomic staging, the receipt generation, and the corrected `env` command.

- [x] **Step 5: Run the Grid tests and the shell checks, then commit.**

Run:

~~~bash
uv run pytest tests/unit/test_scaled_build.py tests/unit/test_grid5000_worker.py tests/unit/test_grid5000.py tests/unit/test_grid5000_cli.py -q
bash -n scripts/grid5000/worker.sh
uv run ruff check scripts/build_scaled_sample.py scripts/grid5000
~~~

Expected: all focused tests, the shell syntax check, and Ruff pass. Commit:

~~~bash
git add scripts/build_scaled_sample.py scripts/grid5000 tests/unit/test_scaled_build.py tests/unit/test_grid5000_worker.py tests/unit/test_grid5000.py tests/unit/test_grid5000_cli.py
git commit -m "feat: run agriculture split builds on Grid5000"
~~~

### Task 5: Rewrite the active documentation and remove the phenotype release language

**Files:**
- Modify: `README.md`
- Modify: `docs/index.md`
- Modify: `docs/quickstart.md`
- Modify: `docs/schema.md`
- Modify: `docs/relevance-policy.md`
- Modify: `docs/known-limitations.md`
- Modify: `docs/labelling.md`
- Modify: `tests/fixtures/golden_card.md`
- Delete: `data/agronomy_lexicon.txt`
- Delete: `data/phenotype_lexicon.txt`

- [x] **Step 1: Replace the active documentation with the agriculture split contract.**

Document these items: the two split definitions, the classification at document level, the optional captions, the simple visual drops, the limits of the source and the provenance, the Grid'5000 commands, and the HF loading examples:

~~~python
dataset = load_dataset("NoeFlandre/finepdf-agrifm-g")
dataset["conventional"][0]
dataset["sustainable"][0]
~~~

- [x] **Step 2: Scan the active code in the whole repository.**

Run:

~~~bash
rg -n "phenotype|caption_terms|train-\\*|load_phenotype|agronomy_lexicon" src scripts tests docs README.md data
~~~

Expected: no reference remains in the production pipeline, the worker, the card, the tests, or the active documentation. You can keep only the historical label artifacts that you intend to keep. Remove each such occurrence, or clearly exclude it from the release.

- [x] **Step 3: Run the full local quality gates.**

Run:

~~~bash
uv run pytest -q
uv run ruff check .
uv run ruff format --check .
~~~

Expected: all tests and the format check pass. Try the type check separately. If the existing environment cannot resolve the optional dependencies, report that.

- [x] **Step 4: Commit the documentation and the release contract.**

~~~bash
git add README.md docs data tests/fixtures/golden_card.md
git commit -m "docs: describe agriculture split dataset"
~~~

### Task 6: Run, verify, and publish the Grid'5000 build

**Files/artifacts:**
- Create the local run state in `out/grid5000/`.
- Create the local verified publish artifact in the run state directory.
- Update `NoeFlandre/finepdf-agrifm-g` only after all artifact gates pass.

- [x] **Step 1: Verify the committed checkout and the remote policy.**

Run `git status --short --branch`. Run `usagepolicycheck -t` on every configured site through the preflight CLI. Run the Grid runner dry-run. Do not submit when the checkout is dirty, when the policy output is not explicitly clean, or when the resource command is not bounded.

- [x] **Step 2: Submit exactly one agriculture run.**

Run the preflight on all configured sites. Then let the selector choose the first healthy site for one job. Use the smallest CPU allocation that works and a realistic walltime. Do not submit duplicate jobs. Record the run ID and the OAR job ID in the local state.

- [x] **Step 3: Monitor and inspect the final result.**

Poll the status. Do not start another job. A final state of the scheduler is not evidence of success. Fetch the receipt only when the job is complete. Inspect stdout and stderr. Require `status: complete`. Require both split parquet families, `README.md`, and `stats.json` in the receipt.

- [x] **Step 4: Fetch and validate the artifact locally.**

Run the fetch command of the runner. Verify the receipt hashes. Load both splits with `datasets`. Assert the schema and the `agriculture_split` values. Decode a sample of images from each split. Compare the row and count statistics with `stats.json`. Assert that no image hash occurs in both splits.

- [x] **Step 5: Replace the HF dataset and verify it independently.**

Upload the verified publish directory with a mirror-style commit. Thus the commit removes the stale `train` files. Then query the live Hub independently with `hf datasets info`, `hf datasets parquet`, and `datasets.load_dataset("NoeFlandre/finepdf-agrifm-g")`. Verify the new revision, exactly the two split names, the row counts, the schema, the card YAML, and that no phenotype text remains.

- [x] **Step 6: Do the exact cleanup and the final policy check.**

First verify the live dataset. Then confirm that the OAR job is inactive. Then remove only the exact new remote run root with the guarded cleanup command. Inspect the two obsolete failed run roots by exact ID. Remove them only if they are inactive and belong to the project. Run the final policy check. Record the job IDs and the artifact revision. Keep the local verified publication state.

## Self-review

- Task 1 and Task 3 cover the semantic filter that uses only text from the spec. Task 2 and Task 4 explicitly remove the captions from the acceptance logic.
- Task 1 covers both extended category lexicons and the requested agriculture concepts.
- Task 2 covers the broad image retention and the simple visual rules.
- Task 3 covers the packaging of two splits that do not share documents, the viewer metadata, and the card prose.
- Task 4 and Task 6 cover the Grid'5000-only execution, the checkpoints, the verification of the receipt, and the policy checks.
- Task 6 covers the in-place HF replacement and the independent verification.
- No step depends on a placeholder or on an unbounded destructive action. The cleanup of the remote run is gated by the exact ID. It happens only after the complete artifact verification.

The execution was complete and inline, with RED to GREEN checkpoints.
