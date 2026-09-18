# ADR-0002: Read FinePDF through parquet row groups, not the datasets-server

*Status: accepted — 2026-09-18*

## Context

The first implementation read rows from `datasets-server.huggingface.co/rows`. It is
the obvious interface, but during the first live run it returned HTTP 500 for every
request to `HuggingFaceFW/finepdfs` (the server was itself rate-limited upstream), for
at least several minutes. A POC whose data access depends on a shared cache being warm
is not reproducible.

## Decision

Read the parquet shard directly from the Hub with `HfFileSystem` + `pyarrow`, pulling
**one row group with three projected columns** (`id`, `url`, `text`).

The shard is 4.8 GB; one row group is ~24 MB and holds 1000 documents, fetched in about
a second by HTTP range requests. That row group is the POC's sampling window: the
manifest records the shard, the row group and the seed, so any run is reproducible from
the manifest alone.

## Consequences

- No dependency on a derived service; only the Hub itself.
- The sample is drawn from the first 1000 documents of one English shard, not from
  FinePDF as a whole. This is a real sampling bias, recorded in
  [known limitations](../known-limitations.md).
- Widening the window later means reading more row groups — a parameter change, not a
  redesign.
