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

## Build the bounded scaled experiment

The cheap scaled run processes one row group from each of thirty FinePDF shards
(30,000 documents), applies the validated
0.5% text gate, keeps only explicitly captioned images whose captions contain a lexicon word,
and applies the strict appearance rules:

The scaled extractor runs only on a reserved Grid’5000 node. The Mac submits and verifies the
job:

```bash
uv run python -m scripts.grid5000 preflight
uv run python -m scripts.grid5000 submit --repo NoeFlandre/finepdf-agrifm-g
uv run python -m scripts.grid5000 status --run-id <run-id>
uv run python -m scripts.grid5000 fetch --run-id <run-id>
```

The default pool covers Grenoble, Lille, Lyon, Nancy, Nantes, Rennes, Sophia, Toulouse and
Luxembourg. Preflight runs `usagepolicycheck -t` on every site; submission runs it immediately
before and after the single OAR job. The default request is one CPU host with 16 cores, 32 GB
RAM and a four-hour walltime. Each completed row group is promoted atomically, so a terminated
allocation can resume the exact run without recomputing completed groups.

If the allocation terminates before packaging, rerun the same submit command with `--resume`.
The runner refuses to create a second job while the previous one is still active.

After local receipt/hash/schema verification, remove only that run's remote files:

```bash
uv run python -m scripts.grid5000 cleanup \
  --run-id <run-id> --confirm-run-id <run-id>
```

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
