# FinePDF Agriculture Splits Implementation Plan

> Historical plan for the first agriculture-split release. The current image-level filtering
> iteration is specified in [ADR-0004](../../adr/0004-image-level-relevance-filter.md).

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (\`- [ ]\`) syntax for tracking.

**Goal:** Replace the phenotype sample with a deterministic, caption-optional FinePDF dataset containing mutually exclusive \`conventional\` and \`sustainable\` agriculture image splits, built on Grid'5000 and published in place on Hugging Face.

**Architecture:** FinePDF document text passes a broad agriculture gate and is classified with two extended phrase-aware lexicons before download. Every embedded raster image in an accepted document is retained unless it fails a small set of obvious visual sanity rules or global hash deduplication. One remote worker writes both split parquet families and a receipt that is independently verified before publication.

**Tech Stack:** Python 3.12, pypdf, Pillow, PyArrow/Datasets, pytest/Hypothesis, Ruff, uv, Grid'5000 OAR, Hugging Face Hub.

---

### Task 1: Lock the new domain contract with failing tests

**Files:**
- Create: \`src/agrifm_g/domain/agriculture.py\`
- Modify: \`src/agrifm_g/domain/textgate.py\`
- Modify: \`src/agrifm_g/adapters/lexicon.py\`
- Create: \`data/agriculture_lexicon.txt\`
- Create: \`data/conventional_agriculture_lexicon.txt\`
- Create: \`data/sustainable_agriculture_lexicon.txt\`
- Test: \`tests/unit/test_agriculture.py\`
- Test: \`tests/unit/test_textgate.py\`
- Test: \`tests/unit/test_lexicon.py\`

- [x] **Step 1: Add the red tests for phrase-aware scoring and split assignment.**

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

Also assert that each committed lexicon has at least 100 terms, includes the requested machinery,
permaculture, hydroponics, agroforestry, and agroecology vocabulary, contains only lowercase terms,
and contains both single-word and multi-word entries.

- [x] **Step 2: Run the focused tests and verify the expected missing-symbol failures.**

Run:

~~~bash
uv run pytest tests/unit/test_agriculture.py tests/unit/test_textgate.py tests/unit/test_lexicon.py -q
~~~

Expected: collection or assertion failures caused by the new API and files not existing yet.

- [x] **Step 3: Implement the phrase-aware matcher and classifier minimally.**

\`textgate.py\` will tokenize with \`[a-z0-9]+\`, normalize lexicon entries into token tuples, and
count exact one- or multi-token matches using n-gram membership. \`agronomy_score\` remains a
length-normalized document score. \`agriculture.py\` will define:

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

\`lexicon.py\` will expose \`AGRICULTURE_PATH\`, \`CONVENTIONAL_PATH\`, \`SUSTAINABLE_PATH\`,
\`load_lexicon\`, and \`load_agriculture_lexicons\`. The broad loader must return the union of the
generic agriculture file and both category files so every category term can pass the pre-fetch
gate.

- [x] **Step 4: Populate the three extended English lexicons.**

The conventional file will cover tractors, combines, planters, ploughs, harrows, cultivators,
sprayers, fertilizer and pesticide use, silos, grain handling, barns, feedlots, livestock,
mechanized/intensive/industrial/commercial farming, irrigation, harvesting, and farm operations.

The sustainable file will cover permaculture, agroecology, agroforestry, silvopasture, food
forests, organic/biodynamic/regenerative/conservation agriculture, no-till, cover crops,
compost, mulch, biochar, crop rotation, polyculture, intercropping, biodiversity, pollinators,
hedgerows, biological pest control, rainwater harvesting, soil health, rotational grazing,
hydroponics, aquaponics, aeroponics, vertical/indoor farming, greenhouses, aquaculture,
community-supported agriculture, food sovereignty, low-input and climate-resilient practices.

The broad file will contain general agriculture, crops, fields, farms, soil, livestock, plant,
production, harvest, rural infrastructure, and food-system terms. All entries are English and
lowercase; comments begin with \`#\`.

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

### Task 2: Make extraction caption-optional and simplify visual drops

**Files:**
- Modify: \`src/agrifm_g/adapters/extraction.py\`
- Modify: \`src/agrifm_g/domain/appearance.py\`
- Modify: \`src/agrifm_g/domain/dedup.py\`
- Modify: \`src/agrifm_g/domain/records.py\`
- Modify: \`src/agrifm_g/adapters/storage.py\`
- Test: \`tests/unit/test_extraction.py\`
- Test: \`tests/unit/test_appearance.py\`
- Test: \`tests/unit/test_dedup.py\`
- Test: \`tests/unit/test_records.py\`

- [x] **Step 1: Add red regression tests proving captionless images survive.**

Add a fake page with one embedded image and text containing no explicit caption. Assert that
\`extract_images(pdf_bytes)\` returns the image with \`caption == ""\`. Assert that a page with a
caption returns the image and metadata but that no \`caption_terms\` argument exists or can filter
it out.

- [x] **Step 2: Run extraction tests and observe the old API/behavior fail.**

Run:

~~~bash
uv run pytest tests/unit/test_extraction.py -q
~~~

Expected: the new captionless behavior exposes the existing \`zip\`/caption-filter contract.

- [x] **Step 3: Remove caption filtering while retaining optional caption metadata.**

Change \`extract_images(pdf_bytes)\` and \`_page_images\` to accept no caption lexicon. Keep reading
order caption pairing, but always return every usable candidate with either its matched caption or
an empty string. The pipeline must never import \`contains_lexicon_word\` for extraction.

- [x] **Step 4: Replace strict appearance rules with obvious-degenerate rules.**

Keep dimension and aspect-ratio checks, exact hash deduplication, blank/flat checks, and two
combined appearance rules:

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

Also mark a single grayscale embedded raster as a document-page scan when its aspect ratio is
within 3% of the page, its near-white share is at least 0.45, and its edge density is at least
0.18. Reject only that combined profile. Do not apply a general edge-density, greyscale texture,
line-art, or colour-count threshold. Keep full-page colour photos eligible and retain metrics for
diagnostics. Update \`DropReason\`, bump the extraction version, and test both supplied noise
profiles plus preserved full-page photos and ordinary low-colour figures.

- [x] **Step 5: Run all extraction/appearance/record tests, then commit.**

Run:

~~~bash
uv run pytest tests/unit/test_extraction.py tests/unit/test_appearance.py tests/unit/test_dedup.py tests/unit/test_records.py -q
~~~

Expected: all focused tests pass. Commit:

~~~bash
git add src/agrifm_g/adapters/extraction.py src/agrifm_g/domain/appearance.py src/agrifm_g/domain/dedup.py src/agrifm_g/domain/records.py src/agrifm_g/adapters/storage.py tests/unit/test_extraction.py tests/unit/test_appearance.py tests/unit/test_dedup.py tests/unit/test_records.py
git commit -m "feat: retain captionless images and simplify visual filtering"
~~~

### Task 3: Carry document categories through the build and package two splits

**Files:**
- Modify: \`src/agrifm_g/pipeline.py\`
- Modify: \`src/agrifm_g/adapters/storage.py\`
- Modify: \`src/agrifm_g/domain/rows.py\`
- Modify: \`src/agrifm_g/adapters/packaging.py\`
- Modify: \`src/agrifm_g/domain/stats.py\`
- Modify: \`src/agrifm_g/domain/card.py\`
- Test: \`tests/unit/test_pipeline.py\`
- Test: \`tests/unit/test_rows.py\`
- Test: \`tests/unit/test_packaging.py\`
- Test: \`tests/unit/test_stats.py\`
- Test: \`tests/unit/test_card.py\`

- [x] **Step 1: Add failing tests for category propagation and split files.**

Test that \`build_with_outcome\`:

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

Test that packaging writes \`data/conventional-*.parquet\` and
\`data/sustainable-*.parquet\`, includes \`agriculture_split\`, and never writes a
\`train-*.parquet\`. Load both files with \`datasets.load_dataset\` and assert each row has the
matching split value.

- [x] **Step 2: Run the new tests and observe expected failures.**

Run:

~~~bash
uv run pytest tests/unit/test_pipeline.py tests/unit/test_rows.py tests/unit/test_packaging.py tests/unit/test_stats.py tests/unit/test_card.py -q
~~~

- [x] **Step 3: Extend records and pipeline with category assignment.**

Add \`agriculture_split: str = ""\` to \`DocumentRecord\` and \`DocumentPayload\`, serialize it, and
include it in flattened rows. Change pipeline payload selection to:

1. score the broad text lexicon;
2. classify with the two category lexicons;
3. increment \`gated_out\` or \`ambiguous_out\` without fetching when rejected;
4. fetch accepted rows once and call \`extract_images(pdf_bytes)\` without caption arguments;
5. write the category onto every accepted document record.

Keep the legacy no-category API behavior for small non-scaled tests by treating absent category
lexicons as an unrestricted build with an empty split, while the scaled build always supplies the
new lexicons.

- [x] **Step 4: Implement split-aware packaging and statistics.**

Group flattened rows by the two \`AgricultureSplit\` values, write deterministic filenames
\`{split}-{index:05d}-of-{n_shards:05d}.parquet\`, remove stale \`*.parquet\` files before writing,
and fail if a scaled record has an unknown/empty split. Add \`agriculture_split\` to \`Features\`.

Add \`documents.text_gated\`, \`documents.ambiguous\`, and a \`splits\` object containing per-split
document and image counts. Keep totals and drop reasons deterministic.

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

The prose must explain document-level text classification, optional captions, broad image
retention, simple visual sanity filters, provenance, Grid'5000 reproduction, and both split
counts. Remove all phenotype wording, old precision claims, and \`train\` loading examples.

- [x] **Step 6: Run focused packaging tests and commit.**

Run:

~~~bash
uv run pytest tests/unit/test_pipeline.py tests/unit/test_rows.py tests/unit/test_packaging.py tests/unit/test_stats.py tests/unit/test_card.py -q
uv run ruff check src/agrifm_g/pipeline.py src/agrifm_g/adapters/storage.py src/agrifm_g/domain/rows.py src/agrifm_g/adapters/packaging.py src/agrifm_g/domain/stats.py src/agrifm_g/domain/card.py tests/unit
~~~

Expected: focused tests and Ruff pass. Commit:

~~~bash
git add src/agrifm_g/pipeline.py src/agrifm_g/adapters/storage.py src/agrifm_g/domain/rows.py src/agrifm_g/adapters/packaging.py src/agrifm_g/domain/stats.py src/agrifm_g/domain/card.py tests/unit/test_pipeline.py tests/unit/test_rows.py tests/unit/test_packaging.py tests/unit/test_stats.py tests/unit/test_card.py tests/fixtures/golden_card.md
git commit -m "feat: package conventional and sustainable splits"
~~~

### Task 4: Refactor the scaled build and Grid'5000 worker

**Files:**
- Modify: \`scripts/build_scaled_sample.py\`
- Modify: \`scripts/grid5000/worker.py\`
- Modify: \`scripts/grid5000/remote.py\`
- Modify: \`scripts/grid5000/config.py\`
- Modify: \`tests/unit/test_scaled_build.py\`
- Modify: \`tests/unit/test_grid5000_worker.py\`
- Modify: \`tests/unit/test_grid5000.py\`
- Modify: \`tests/unit/test_grid5000_cli.py\`

- [x] **Step 1: Add red tests for the agriculture output path and no phenotype inputs.**

Assert that worker arguments use \`out/agriculture-30000\`, that the publish path matches it, that
the scaled script loads all three agriculture lexicons, and that no rendered worker command uses
the old phenotype path. Assert the existing \`env AGRIFM_G_GRID5000_JOB=1\` command shape remains
valid.

- [x] **Step 2: Run Grid-focused tests and observe failures.**

Run:

~~~bash
uv run pytest tests/unit/test_scaled_build.py tests/unit/test_grid5000_worker.py tests/unit/test_grid5000.py tests/unit/test_grid5000_cli.py -q
~~~

- [x] **Step 3: Update the scaled build.**

Use \`out/agriculture-30000\` by default, load the broad/category lexicons, remove every
\`caption_terms\` argument, return text-gated and ambiguous counts from each staged group, and pass
the category counts to \`package_dataset\`. Resume validation must recompute both text and category
decisions from the same source rows and reject incomplete/unknown category records.

- [x] **Step 4: Update the worker, fetch path, and run identity.**

Point worker and remote fetch logic at \`out/agriculture-30000\`. Add a configuration/profile marker
such as \`pipeline="agriculture-splits-v1"\` to \`RunConfig\` so a phenotype spec cannot collide with
the agriculture output even when the commit is reused. Preserve bounded OAR resources, atomic
staging, receipt generation, and the corrected \`env\` command.

- [x] **Step 5: Run Grid tests, shell checks, and commit.**

Run:

~~~bash
uv run pytest tests/unit/test_scaled_build.py tests/unit/test_grid5000_worker.py tests/unit/test_grid5000.py tests/unit/test_grid5000_cli.py -q
bash -n scripts/grid5000/worker.sh
uv run ruff check scripts/build_scaled_sample.py scripts/grid5000
~~~

Expected: all focused tests, shell syntax, and Ruff pass. Commit:

~~~bash
git add scripts/build_scaled_sample.py scripts/grid5000 tests/unit/test_scaled_build.py tests/unit/test_grid5000_worker.py tests/unit/test_grid5000.py tests/unit/test_grid5000_cli.py
git commit -m "feat: run agriculture split builds on Grid5000"
~~~

### Task 5: Rewrite active documentation and remove phenotype release language

**Files:**
- Modify: \`README.md\`
- Modify: \`docs/index.md\`
- Modify: \`docs/quickstart.md\`
- Modify: \`docs/schema.md\`
- Modify: \`docs/relevance-policy.md\`
- Modify: \`docs/known-limitations.md\`
- Modify: \`docs/labelling.md\`
- Modify: \`tests/fixtures/golden_card.md\`
- Delete: \`data/agronomy_lexicon.txt\`
- Delete: \`data/phenotype_lexicon.txt\`

- [x] **Step 1: Replace active documentation with the agriculture split contract.**

Document the two split definitions, document-level classification, optional captions, simple visual
drops, source/provenance limitations, Grid'5000 commands, and HF loading examples:

~~~python
dataset = load_dataset("NoeFlandre/finepdf-agrifm-g")
dataset["conventional"][0]
dataset["sustainable"][0]
~~~

- [x] **Step 2: Run a repository-wide active-code scan.**

Run:

~~~bash
rg -n "phenotype|caption_terms|train-\\*|load_phenotype|agronomy_lexicon" src scripts tests docs README.md data
~~~

Expected: no production pipeline, worker, card, test, or active documentation references remain;
only intentionally preserved historical label artifacts may be retained, and any such occurrence
must be removed or clearly excluded from the release.

- [x] **Step 3: Run the full local quality gates.**

Run:

~~~bash
uv run pytest -q
uv run ruff check .
uv run ruff format --check .
~~~

Expected: all tests and formatting pass. Type checking is attempted separately and reported if the
existing environment cannot resolve optional dependencies.

- [x] **Step 4: Commit documentation and release contract.**

~~~bash
git add README.md docs data tests/fixtures/golden_card.md
git commit -m "docs: describe agriculture split dataset"
~~~

### Task 6: Execute, verify, and publish the Grid'5000 build

**Files/artifacts:**
- Create local run state under \`out/grid5000/\`.
- Create local verified publish artifact under the run state directory.
- Update \`NoeFlandre/finepdf-agrifm-g\` only after all artifact gates pass.

- [x] **Step 1: Verify the committed checkout and remote policy.**

Run \`git status --short --branch\`, \`usagepolicycheck -t\` on every configured site through the
preflight CLI, and the Grid runner dry-run. Do not submit if the checkout is dirty, policy output
is not explicitly clean, or the resource command is not bounded.

- [x] **Step 2: Submit exactly one agriculture run.**

Use all configured sites for preflight, then let the selector choose the first healthy site for one
job. Use the smallest working CPU allocation and a realistic walltime; do not submit duplicate jobs.
Record the run ID and OAR job ID in local state.

- [x] **Step 3: Monitor and inspect the terminal result.**

Poll status without starting another job. A scheduler terminal state is not success evidence; fetch
the receipt only when the job is complete, inspect stdout/stderr, require \`status: complete\`, and
require both split parquet families, \`README.md\`, and \`stats.json\` in the receipt.

- [x] **Step 4: Fetch and validate the artifact locally.**

Run the runner fetch command, verify receipt hashes, load both splits with \`datasets\`, assert the
schema and \`agriculture_split\` values, decode a sample of images from each split, compare row/count
statistics to \`stats.json\`, and assert no image hash occurs in both splits.

- [x] **Step 5: Replace and independently verify the HF dataset.**

Upload the verified publish directory with a mirror-style commit so stale \`train\` files are removed.
Then query the live Hub independently using \`hf datasets info\`, \`hf datasets parquet\`, and
\`datasets.load_dataset("NoeFlandre/finepdf-agrifm-g")\`. Verify the new revision, exactly the two
split names, row counts, schema, card YAML, and no phenotype text.

- [x] **Step 6: Perform exact cleanup and final policy check.**

After live verification and confirmation that the OAR job is inactive, remove only the exact new
remote run root through the guarded cleanup command. Inspect the two obsolete failed run roots by
exact ID and remove them only if they are inactive and project-owned. Run the final policy check,
record job IDs and artifact revision, and leave the local verified publication state intact.

## Self-review

- The spec's text-only semantic filter is covered by Task 1 and Task 3; captions are explicitly
  removed from acceptance logic in Task 2 and Task 4.
- Both extended category lexicons and requested agriculture concepts are covered by Task 1.
- Broad image retention and simple visual rules are covered by Task 2.
- Mutually exclusive two-split packaging, viewer metadata, and card prose are covered by Task 3.
- Grid'5000-only execution, checkpoints, receipt verification, and policy checks are covered by
  Tasks 4 and 6.
- In-place HF replacement and independent verification are covered by Task 6.
- No step relies on a placeholder or an unbounded destructive action; remote cleanup is exact-ID
  gated and happens only after complete artifact verification.

Execution completed inline with RED→GREEN checkpoints.
