"""Orchestration: manifest -> rows -> PDFs -> images -> dataset directory."""

from __future__ import annotations

import json
from collections.abc import Collection
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
from agrifm_g.domain.records import DocumentRecord
from agrifm_g.domain.sampling import select_indices
from agrifm_g.domain.textgate import DEFAULT_THRESHOLD, agronomy_score, passes_gate


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


def build_dataset(
    manifest: Manifest,
    source: RowSource,
    fetcher: PdfFetcher,
    out_dir: Path,
    *,
    terms: Collection[str] = (),
    threshold: float = DEFAULT_THRESHOLD,
) -> list[DocumentRecord]:
    """Materialise the manifest into a dataset directory, skipping unusable documents."""
    return build_with_outcome(
        manifest, source, fetcher, out_dir, terms=terms, threshold=threshold
    ).records


def build_with_outcome(
    manifest: Manifest,
    source: RowSource,
    fetcher: PdfFetcher,
    out_dir: Path,
    *,
    terms: Collection[str] = (),
    threshold: float = DEFAULT_THRESHOLD,
) -> BuildOutcome:
    """As `build_dataset`, but also reports how many documents the text gate skipped.

    With no `terms` the gate is inert: scoring against an empty lexicon would reject
    everything, so an empty lexicon means "no gate" rather than "no documents".
    """
    rows = source.rows(manifest.indices)
    wanted = [row for row in rows if _worth_fetching(row, terms, threshold)]
    payloads = [payload for row in wanted if (payload := _payload_for(row, fetcher)) is not None]
    return BuildOutcome(
        records=write_dataset(out_dir, payloads),
        sampled=len(rows),
        gated_out=len(rows) - len(wanted),
    )


def _worth_fetching(row: FinePdfRow, terms: Collection[str], threshold: float) -> bool:
    if not terms:
        return True
    return passes_gate(agronomy_score(row.text, terms), threshold=threshold)


def _payload_for(row: FinePdfRow, fetcher: PdfFetcher) -> DocumentPayload | None:
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
    )
