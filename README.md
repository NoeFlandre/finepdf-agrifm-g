# AGRIFM-G — FinePDF extraction POC

[![qa](https://github.com/NoeFlandre/finepdf-agrifm-g/actions/workflows/qa.yml/badge.svg)](https://github.com/NoeFlandre/finepdf-agrifm-g/actions/workflows/qa.yml)

A minimal, reproducible pipeline that turns [FinePDF](https://huggingface.co/datasets/HuggingFaceFW/finepdfs)
documents into a dataset of PDFs, text and images — the first step towards the corpus
described in [DATASET_GOAL.md](DATASET_GOAL.md).

**This is a proof of concept.** It applies no agricultural or phenotyping filtering yet;
see [known limitations](docs/known-limitations.md) before drawing conclusions from it.

```bash
uv sync --all-groups
uv run agrifm-g build   --manifest data/sample_manifest.json --out out/dataset
uv run agrifm-g verify  --dataset out/dataset
uv run agrifm-g package --dataset out/dataset --out out/publish --repo <hf-repo>
```

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
| `data/sample_manifest.json` | the frozen, seeded sample |
| `docs/adr/` | why it is shaped this way |
