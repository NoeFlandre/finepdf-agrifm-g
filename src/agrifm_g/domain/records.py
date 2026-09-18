"""The dataset's record shape: one record per source document."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

EXTRACTION_VERSION = 2
"""Bumped whenever extraction changes in a way that alters stored bytes."""


@dataclass(frozen=True, slots=True)
class ImageRef:
    """A single image extracted from a document, stored next to the metadata."""

    path: str
    page: int
    width: int
    height: int
    format: str
    sha256: str
    n_colours: int


@dataclass(frozen=True, slots=True)
class DocumentRecord:
    """One FinePDF document: its PDF, its text and its images."""

    doc_id: str
    source_url: str
    pdf_path: str
    pdf_sha256: str
    text: str
    images: tuple[ImageRef, ...]

    def __post_init__(self) -> None:
        if not self.doc_id:
            raise ValueError("doc_id must not be empty")
        paths = [image.path for image in self.images]
        if len(set(paths)) != len(paths):
            raise ValueError(f"duplicate image paths in record {self.doc_id}")

    @property
    def n_images(self) -> int:
        return len(self.images)


def record_to_json(record: DocumentRecord) -> str:
    """Serialise one record as a single JSONL line (stable key order)."""
    payload = {
        "doc_id": record.doc_id,
        "source_url": record.source_url,
        "pdf_path": record.pdf_path,
        "pdf_sha256": record.pdf_sha256,
        "text": record.text,
        "images": [
            {
                "path": image.path,
                "page": image.page,
                "width": image.width,
                "height": image.height,
                "format": image.format,
                "sha256": image.sha256,
                "n_colours": image.n_colours,
            }
            for image in record.images
        ],
        "n_images": record.n_images,
        "extraction_version": EXTRACTION_VERSION,
    }
    return json.dumps(payload, ensure_ascii=False, sort_keys=True)


def record_from_json(payload: dict[str, Any]) -> DocumentRecord:
    """Rebuild a record from its serialised form, failing loudly on a bad shape."""
    try:
        return DocumentRecord(
            doc_id=payload["doc_id"],
            source_url=payload["source_url"],
            pdf_path=payload["pdf_path"],
            pdf_sha256=payload["pdf_sha256"],
            text=payload["text"],
            images=tuple(
                ImageRef(
                    path=image["path"],
                    page=image["page"],
                    width=image["width"],
                    height=image["height"],
                    format=image["format"],
                    sha256=image["sha256"],
                    n_colours=image["n_colours"],
                )
                for image in payload["images"]
            ),
        )
    except (KeyError, TypeError) as error:
        raise ValueError(f"malformed record: {error}") from error
