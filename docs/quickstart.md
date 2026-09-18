# Quickstart

```bash
uv sync --all-groups
```

## Build the tiny dataset

The committed manifest (`data/sample_manifest.json`) fixes the sample, so a build is
reproducible without re-sampling:

```bash
uv run agrifm-g build --manifest data/sample_manifest.json --out out/dataset
uv run agrifm-g verify --dataset out/dataset
```

`verify` exits non-zero if any record references a file that is not on disk.

## Re-draw the sample

```bash
uv run agrifm-g sample --size 60 --seed 20260918 --out data/sample_manifest.json
```

Same seed, same documents.

## Package and publish

`build` produces a working directory (PDFs, loose PNGs, `metadata.jsonl`). `package` turns it
into what is actually published: deduplicated parquet shards, `stats.json` and a generated card.

```bash
uv run agrifm-g package --dataset out/dataset --out out/publish \
  --repo NoeFlandre/finepdf-agrifm-g
HF_TOKEN=... uv run agrifm-g publish --dataset out/publish \
  --repo NoeFlandre/finepdf-agrifm-g
make publish-check
```

Add `--dry-run` to `publish` to print the target without uploading. `publish-check` loads the
live repo with `load_dataset` and fails if the published schema has drifted.

## Quality gauntlet

```bash
make qa
```

Runs, in order: ruff, ty, tests with coverage, acceptance scenarios, architecture
contracts, CRAP, mutation testing.
