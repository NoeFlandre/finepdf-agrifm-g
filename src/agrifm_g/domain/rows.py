"""The published table: one row per image, carrying its document's context."""

from __future__ import annotations

from collections.abc import Iterable

from agrifm_g.domain.records import EXTRACTION_VERSION, DocumentRecord

COLUMNS = (
    "image",
    "doc_id",
    "agriculture_split",
    "page",
    "image_index",
    "width",
    "height",
    "image_sha256",
    "image_path",
    "n_colours",
    "edge_density",
    "agriculture_photo_score",
    "document_figure_score",
    "unrelated_photo_score",
    "caption",
    "source_url",
    "pdf_sha256",
    "text",
    "n_images_in_doc",
    "extraction_version",
)


def image_rows(records: Iterable[DocumentRecord]) -> list[dict]:
    """Flatten records into published rows, ordered by document then image."""
    return [
        _row(record, index)
        for record in sorted(records, key=lambda record: record.doc_id)
        for index in range(record.n_images)
    ]


def _row(record: DocumentRecord, index: int) -> dict:
    image = record.images[index]
    return {
        "doc_id": record.doc_id,
        "agriculture_split": record.agriculture_split,
        "page": image.page,
        "image_index": index,
        "width": image.width,
        "height": image.height,
        "image_sha256": image.sha256,
        "image_path": image.path,
        "n_colours": image.n_colours,
        "edge_density": round(image.edge_density, 5),
        "agriculture_photo_score": image.agriculture_photo_score,
        "document_figure_score": image.document_figure_score,
        "unrelated_photo_score": image.unrelated_photo_score,
        "caption": image.caption,
        "source_url": record.source_url,
        "pdf_sha256": record.pdf_sha256,
        "text": record.text,
        "n_images_in_doc": record.n_images,
        "extraction_version": EXTRACTION_VERSION,
    }
