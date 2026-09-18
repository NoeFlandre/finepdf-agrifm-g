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

## Publish

```bash
HF_TOKEN=... uv run agrifm-g publish --dataset out/dataset --repo NoeFlandre/agrifm-g-finepdf-poc
```

Add `--dry-run` to print the target without uploading.

## Quality gauntlet

```bash
make qa
```

Runs, in order: ruff, ty, tests with coverage, acceptance scenarios, architecture
contracts, CRAP, mutation testing.
