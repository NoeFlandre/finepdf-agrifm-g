# AGRIFM-G — FinePDF extraction POC

[![qa](https://github.com/NoeFlandre/finepdf-agrifm-g/actions/workflows/qa.yml/badge.svg)](https://github.com/NoeFlandre/finepdf-agrifm-g/actions/workflows/qa.yml)

A minimal, reproducible pipeline that turns [FinePDF](https://huggingface.co/datasets/HuggingFaceFW/finepdfs)
documents into a dataset of PDFs, text and images — the first step towards the corpus
described in [DATASET_GOAL.md](DATASET_GOAL.md).

**This is a proof of concept.** It applies only cheap caption-lexicon and appearance filters,
not semantic agricultural or phenotyping filtering; see [known limitations](docs/known-limitations.md)
before drawing conclusions from it.

```bash
uv sync --all-groups
uv run agrifm-g build   --manifest data/sample_manifest.json --out out/dataset
uv run agrifm-g verify  --dataset out/dataset
uv run agrifm-g package --dataset out/dataset --out out/publish --repo <hf-repo>
```

For the bounded scaled experiment (thirty FinePDF shards, one row group each, 30,000
documents):

```bash
uv run python -m scripts.grid5000 preflight
uv run python -m scripts.grid5000 submit --repo <hf-repo>
# after OAR reports completion:
uv run python -m scripts.grid5000 fetch --run-id <run-id>
```

The scaled extractor is Grid’5000-only; the Mac performs submission, monitoring and local
artifact verification, not the heavy PDF work. The runner checks usage-policy conformance on
every configured site, submits one bounded CPU job, and resumes completed row groups after an
interrupted allocation. Use `cleanup --run-id <run-id> --confirm-run-id <run-id>` only after
the fetched artifact has been verified.

If an OAR allocation terminates before packaging, rerun the same submission options with
`--resume`; the runner verifies that the previous job is terminal and reuses only completed
row-group checkpoints.

`build` produces a working directory; `package` produces what is published: deduplicated
parquet shards with an `Image()` column, generated `stats.json` and a generated card.

- Published sample: <https://huggingface.co/datasets/NoeFlandre/finepdf-agrifm-g>
- What we actually want to keep: [relevance policy](docs/relevance-policy.md)
- Documentation: `uv run mkdocs serve`
- Full quality gauntlet: `make qa`

## Layout

| Path | What it holds |
| --- | --- |
| `src/agrifm_g/domain/` | pure logic: sampling, records, normalisation, verification |
| `src/agrifm_g/adapters/` | every side effect: FinePDF, HTTP, PDF parsing, disk, the Hub |
| `src/agrifm_g/pipeline.py` | composition of the above |
| `src/agrifm_g/cli.py` | `sample`, `build`, `verify`, `publish` |
| `scripts/build_scaled_sample.py` | bounded multi-row-group build and package |
| `scripts/grid5000/` | policy-aware Grid’5000 submission, worker and receipt workflow |
| `data/sample_manifest.json` | the frozen, seeded sample |
| `docs/adr/` | why it is shaped this way |
