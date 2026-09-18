"""Orchestration: manifest -> rows -> PDFs -> images -> dataset directory."""

from __future__ import annotations

import json
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


def build_dataset(
    manifest: Manifest, source: RowSource, fetcher: PdfFetcher, out_dir: Path
) -> list[DocumentRecord]:
    """Materialise the manifest into a dataset directory, skipping unusable documents."""
    payloads = [
        payload
        for row in source.rows(manifest.indices)
        if (payload := _payload_for(row, fetcher)) is not None
    ]
    return write_dataset(out_dir, payloads)


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
