"""Orchestration: manifest -> rows -> PDFs -> images -> dataset directory."""

from __future__ import annotations

import json
from collections.abc import Collection
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from agrifm_g.adapters.extraction import ExtractionError, extract_images
from agrifm_g.adapters.finepdf import (
    DEFAULT_CONFIG,
    DEFAULT_DATASET,
    DEFAULT_SPLIT,
    FinePdfRow,
    RowSource,
)
from agrifm_g.adapters.pdfsource import FetchError, PdfFetcher
from agrifm_g.adapters.storage import DocumentPayload, write_dataset
from agrifm_g.domain.agriculture import AgricultureSplit, classify_document
from agrifm_g.domain.records import DocumentRecord
from agrifm_g.domain.sampling import select_indices
from agrifm_g.domain.textgate import DEFAULT_THRESHOLD, agronomy_score, passes_gate

DEFAULT_WORKERS = 16
"""How many documents to retrieve at once.

Retrieval is almost entirely waiting on hosts that mostly no longer answer, so the build is
bound by timeouts rather than by work. Threads overlap that waiting; results are still
collected in manifest order, so a build stays reproducible.
"""


@dataclass(frozen=True, slots=True)
class Manifest:
    """The frozen, reproducible definition of the sample."""

    dataset: str
    config: str
    split: str
    seed: int
    size: int
    indices: tuple[int, ...]
    doc_ids: tuple[str, ...]

    def to_json(self) -> str:
        return json.dumps(
            {
                "dataset": self.dataset,
                "config": self.config,
                "split": self.split,
                "seed": self.seed,
                "size": self.size,
                "indices": list(self.indices),
                "doc_ids": list(self.doc_ids),
            },
            indent=2,
            sort_keys=True,
        )

    @classmethod
    def from_json(cls, payload: dict[str, Any]) -> Manifest:
        try:
            return cls(
                dataset=payload["dataset"],
                config=payload["config"],
                split=payload["split"],
                seed=payload["seed"],
                size=payload["size"],
                indices=tuple(payload["indices"]),
                doc_ids=tuple(payload["doc_ids"]),
            )
        except (KeyError, TypeError) as error:
            raise ValueError(f"malformed manifest: {error}") from error


def build_manifest(
    source: RowSource,
    *,
    size: int,
    seed: int,
    dataset: str = DEFAULT_DATASET,
    config: str = DEFAULT_CONFIG,
    split: str = DEFAULT_SPLIT,
) -> Manifest:
    """Resolve a seeded sample into concrete document ids."""
    indices = select_indices(total=source.total(), size=size, seed=seed)
    rows = source.rows(indices)
    return Manifest(
        dataset=dataset,
        config=config,
        split=split,
        seed=seed,
        size=size,
        indices=tuple(indices),
        doc_ids=tuple(row.doc_id for row in rows),
    )


@dataclass(frozen=True, slots=True)
class BuildOutcome:
    """What a build did, including the documents it never fetched."""

    records: list[DocumentRecord]
    sampled: int
    gated_out: int
    ambiguous_out: int = 0


def build_dataset(
    manifest: Manifest,
    source: RowSource,
    fetcher: PdfFetcher,
    out_dir: Path,
    *,
    terms: Collection[str] = (),
    threshold: float = DEFAULT_THRESHOLD,
    conventional_terms: Collection[str] | None = None,
    sustainable_terms: Collection[str] | None = None,
    workers: int = DEFAULT_WORKERS,
) -> list[DocumentRecord]:
    """Materialise the manifest into a dataset directory, skipping unusable documents."""
    return build_with_outcome(
        manifest,
        source,
        fetcher,
        out_dir,
        terms=terms,
        threshold=threshold,
        conventional_terms=conventional_terms,
        sustainable_terms=sustainable_terms,
        workers=workers,
    ).records


def build_with_outcome(
    manifest: Manifest,
    source: RowSource,
    fetcher: PdfFetcher,
    out_dir: Path,
    *,
    terms: Collection[str] = (),
    threshold: float = DEFAULT_THRESHOLD,
    conventional_terms: Collection[str] | None = None,
    sustainable_terms: Collection[str] | None = None,
    workers: int = DEFAULT_WORKERS,
) -> BuildOutcome:
    """As `build_dataset`, but also reports how many documents the text gate skipped.

    With no `terms` the gate is inert: scoring against an empty lexicon would reject
    everything, so an empty lexicon means "no gate" rather than "no documents".
    """
    rows = source.rows(manifest.indices)
    wanted: list[tuple[FinePdfRow, str]] = []
    gated_out = 0
    ambiguous_out = 0
    for row in rows:
        if not _worth_fetching(row, terms, threshold):
            gated_out += 1
            continue
        split = _classify_if_configured(row.text, conventional_terms, sustainable_terms)
        if split is None and conventional_terms is not None and sustainable_terms is not None:
            ambiguous_out += 1
            continue
        wanted.append((row, split.value if split else ""))
    payloads = [
        payload
        for payload in _payloads(wanted, fetcher, workers=workers)
        if payload is not None
    ]
    return BuildOutcome(
        records=write_dataset(out_dir, payloads),
        sampled=len(rows),
        gated_out=gated_out,
        ambiguous_out=ambiguous_out,
    )


def _payloads(
    rows: list[tuple[FinePdfRow, str]],
    fetcher: PdfFetcher,
    *,
    workers: int,
) -> list[DocumentPayload | None]:
    """Retrieve and extract in manifest order, overlapping the waiting when asked to."""
    if workers <= 1 or not rows:
        return [_payload_for(row, split, fetcher) for row, split in rows]
    with ThreadPoolExecutor(max_workers=min(workers, len(rows))) as pool:
        return list(
            pool.map(lambda item: _payload_for(item[0], item[1], fetcher), rows)
        )


def _worth_fetching(row: FinePdfRow, terms: Collection[str], threshold: float) -> bool:
    if not terms:
        return True
    return passes_gate(agronomy_score(row.text, terms), threshold=threshold)


def _payload_for(
    row: FinePdfRow,
    split: str,
    fetcher: PdfFetcher,
) -> DocumentPayload | None:
    try:
        pdf_bytes = fetcher.fetch(row.url)
        images = extract_images(pdf_bytes)
    except (FetchError, ExtractionError):
        return None
    return DocumentPayload(
        raw_doc_id=row.doc_id,
        source_url=row.url,
        text=row.text,
        pdf_bytes=pdf_bytes,
        images=images,
        agriculture_split=split,
    )


def _classify_if_configured(
    text: str,
    conventional_terms: Collection[str] | None,
    sustainable_terms: Collection[str] | None,
) -> AgricultureSplit | None:
    if conventional_terms is None or sustainable_terms is None:
        return None
    return classify_document(text, conventional_terms, sustainable_terms)
