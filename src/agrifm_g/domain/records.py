"""The dataset's record shape: one record per source document."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

EXTRACTION_VERSION = 8
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
    dominant_colour_share: float
    near_white_share: float
    edge_density: float
    greyscale: bool = False
    document_page_scan: bool = False
    caption: str = ""
    coarse_colour_bins: int = 0
    coarse_dominant_share: float = 0.0
    agriculture_photo_score: float | None = None
    document_figure_score: float | None = None
    unrelated_photo_score: float | None = None


@dataclass(frozen=True, slots=True)
class DocumentRecord:
    """One FinePDF document: its PDF, its text and its images."""

    doc_id: str
    source_url: str
    pdf_path: str
    pdf_sha256: str
    text: str
    images: tuple[ImageRef, ...]
    agriculture_split: str = ""

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
        "agriculture_split": record.agriculture_split,
        "images": [
            {
                "path": image.path,
                "page": image.page,
                "width": image.width,
                "height": image.height,
                "format": image.format,
                "sha256": image.sha256,
                "n_colours": image.n_colours,
                "dominant_colour_share": round(image.dominant_colour_share, 5),
                "near_white_share": round(image.near_white_share, 5),
                "edge_density": round(image.edge_density, 5),
                "greyscale": image.greyscale,
                "document_page_scan": image.document_page_scan,
                "caption": image.caption,
                "coarse_colour_bins": image.coarse_colour_bins,
                "coarse_dominant_share": round(image.coarse_dominant_share, 5),
                "agriculture_photo_score": _rounded_score(image.agriculture_photo_score),
                "document_figure_score": _rounded_score(image.document_figure_score),
                "unrelated_photo_score": _rounded_score(image.unrelated_photo_score),
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
                    dominant_colour_share=image["dominant_colour_share"],
                    near_white_share=image["near_white_share"],
                    edge_density=image["edge_density"],
                    greyscale=image.get("greyscale", False),
                    document_page_scan=image.get("document_page_scan", False),
                    caption=image.get("caption", ""),
                    coarse_colour_bins=image.get("coarse_colour_bins", 0),
                    coarse_dominant_share=image.get("coarse_dominant_share", 0.0),
                    agriculture_photo_score=image.get("agriculture_photo_score"),
                    document_figure_score=image.get("document_figure_score"),
                    unrelated_photo_score=image.get("unrelated_photo_score"),
                )
                for image in payload["images"]
            ),
            agriculture_split=payload.get("agriculture_split", ""),
        )
    except (KeyError, TypeError) as error:
        raise ValueError(f"malformed record: {error}") from error


def _rounded_score(value: float | None) -> float | None:
    return round(value, 6) if value is not None else None
