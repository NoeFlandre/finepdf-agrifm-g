# ADR-0002: Read FinePDF through parquet row groups, not the datasets-server

*Status: accepted — 2026-09-18*

## Context

The first implementation read rows from `datasets-server.huggingface.co/rows`. This is the
obvious interface. But during the first live run, it returned HTTP 500 for each request to
`HuggingFaceFW/finepdfs`. The server was itself rate-limited upstream. This lasted at least
several minutes. A POC that depends on a warm shared cache is not reproducible.

## Decision

Read the parquet shard directly from the Hub with `HfFileSystem` + `pyarrow`. Pull
**one row group with three projected columns** (`id`, `url`, `text`).

The shard is 4.8 GB. One row group is ~24 MB and holds 1000 documents. HTTP range requests
fetch it in about one second. This row group is the sampling window of the POC. The manifest
records the shard, the row group, and the seed. Thus, the manifest alone is enough to reproduce
any run.

## Consequences

- The pipeline has no dependency on a derived service. It depends only on the Hub.
- The sample comes from the first 1000 documents of one English shard. It does not come from
  all of FinePDF. This is a real sampling bias. [The known limitations](../known-limitations.md)
  record it.
- To widen the window later, read more row groups, or read the same row group across more
  shards. This is a parameter change. It is not a redesign.
