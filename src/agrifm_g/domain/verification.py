"""Referential integrity of a built dataset, expressed over plain data."""

from __future__ import annotations

from collections.abc import Iterable

from agrifm_g.domain.records import DocumentRecord


def verify_records(records: Iterable[DocumentRecord], existing_files: set[str]) -> list[str]:
    """Return one human-readable problem per broken reference; empty means valid."""
    problems: list[str] = []
    seen: set[str] = set()
    for record in records:
        problems.extend(_duplicate_problems(record, seen))
        problems.extend(_missing_file_problems(record, existing_files))
    return problems


def _duplicate_problems(record: DocumentRecord, seen: set[str]) -> list[str]:
    problems = [f"duplicate doc_id: {record.doc_id}"] if record.doc_id in seen else []
    seen.add(record.doc_id)
    return problems


def _missing_file_problems(record: DocumentRecord, existing_files: set[str]) -> list[str]:
    missing = (
        []
        if record.pdf_path in existing_files
        else [f"{record.doc_id}: missing pdf file {record.pdf_path}"]
    )
    missing.extend(
        f"{record.doc_id}: missing image file {image.path}"
        for image in record.images
        if image.path not in existing_files
    )
    return missing
