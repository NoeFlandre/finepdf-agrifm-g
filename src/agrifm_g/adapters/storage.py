"""The on-disk dataset layout: pdfs/, images/<doc>/, metadata.jsonl."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path

from agrifm_g.adapters.extraction import ExtractedImage
from agrifm_g.domain.normalisation import safe_doc_id
from agrifm_g.domain.records import DocumentRecord, ImageRef, record_from_json, record_to_json

METADATA_FILE = "metadata.jsonl"


@dataclass(frozen=True, slots=True)
class DocumentPayload:
    """Everything gathered about one document, before it reaches the disk."""

    raw_doc_id: str
    source_url: str
    text: str
    pdf_bytes: bytes
    images: tuple[ExtractedImage, ...]
    agriculture_split: str = ""


def write_dataset(out_dir: Path, payloads: Iterable[DocumentPayload]) -> list[DocumentRecord]:
    """Write the whole dataset and return the records exactly as stored."""
    records = [_write_document(out_dir, payload) for payload in payloads]
    _reject_collisions(records)
    lines = "".join(f"{record_to_json(record)}\n" for record in records)
    (out_dir / METADATA_FILE).write_text(lines, encoding="utf-8")
    return records


def read_records(out_dir: Path) -> list[DocumentRecord]:
    """Read back what `write_dataset` wrote."""
    text = (out_dir / METADATA_FILE).read_text(encoding="utf-8")
    return [record_from_json(json.loads(line)) for line in text.splitlines() if line]


def existing_files(out_dir: Path) -> set[str]:
    """Every file present in the dataset directory, as dataset-relative paths."""
    return {
        str(path.relative_to(out_dir))
        for path in out_dir.rglob("*")
        if path.is_file() and path.name != METADATA_FILE
    }


def _write_document(out_dir: Path, payload: DocumentPayload) -> DocumentRecord:
    doc_id = safe_doc_id(payload.raw_doc_id)
    pdf_path = f"pdfs/{doc_id}.pdf"
    _write_bytes(out_dir / pdf_path, payload.pdf_bytes)
    images = tuple(
        _write_image(out_dir, doc_id, position, image)
        for position, image in enumerate(payload.images)
    )
    return DocumentRecord(
        doc_id=doc_id,
        source_url=payload.source_url,
        pdf_path=pdf_path,
        pdf_sha256=hashlib.sha256(payload.pdf_bytes).hexdigest(),
        text=payload.text,
        images=images,
        agriculture_split=payload.agriculture_split,
    )


def _write_image(out_dir: Path, doc_id: str, position: int, image: ExtractedImage) -> ImageRef:
    path = f"images/{doc_id}/{position:03d}.{image.format}"
    _write_bytes(out_dir / path, image.data)
    return ImageRef(
        path=path,
        page=image.page,
        width=image.width,
        height=image.height,
        format=image.format,
        sha256=image.sha256,
        n_colours=image.n_colours,
        # rounded once, here, so what is stored and what is held in memory agree
        dominant_colour_share=round(image.dominant_colour_share, 5),
        near_white_share=round(image.near_white_share, 5),
        edge_density=round(image.edge_density, 5),
        greyscale=image.greyscale,
        document_page_scan=image.document_page_scan,
        caption=image.caption,
    )


def _write_bytes(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)


def _reject_collisions(records: Sequence[DocumentRecord]) -> None:
    ids = [record.doc_id for record in records]
    if len(set(ids)) != len(ids):
        raise ValueError("two source documents normalise to the same doc_id")


def file_hashes(out_dir: Path) -> dict[str, str]:
    """SHA-256 of every stored PDF, keyed by dataset-relative path."""
    return {
        str(path.relative_to(out_dir)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in (out_dir / "pdfs").glob("*.pdf")
    }
