"""Referential integrity of a built dataset, expressed over plain data."""

from __future__ import annotations

from collections.abc import Iterable, Mapping

from agrifm_g.domain.records import DocumentRecord


def verify_records(
    records: Iterable[DocumentRecord],
    existing_files: set[str],
    hashes: Mapping[str, str] | None = None,
) -> list[str]:
    """Return one human-readable problem per broken reference; empty means valid.

    `hashes` maps a dataset-relative path to the SHA-256 of the bytes actually on disk.
    It is optional: a dataset published without its PDFs still verifies.
    """
    problems: list[str] = []
    seen: set[str] = set()
    for record in records:
        problems.extend(_duplicate_problems(record, seen))
        problems.extend(_missing_file_problems(record, existing_files))
        problems.extend(_hash_problems(record, hashes or {}))
    return problems


def _hash_problems(record: DocumentRecord, hashes: Mapping[str, str]) -> list[str]:
    problems: list[str] = []
    pdf_problem = _checksum_problem(
        record.doc_id, "pdf", record.pdf_path, record.pdf_sha256, hashes
    )
    if pdf_problem is not None:
        problems.append(pdf_problem)
    for image in record.images:
        image_problem = _checksum_problem(record.doc_id, "image", image.path, image.sha256, hashes)
        if image_problem is not None:
            problems.append(image_problem)
    return problems


def _checksum_problem(
    doc_id: str,
    artifact_type: str,
    path: str,
    expected_hash: str,
    hashes: Mapping[str, str],
) -> str | None:
    actual_hash = hashes.get(path)
    if actual_hash is None or actual_hash == expected_hash:
        return None
    return f"{doc_id}: {artifact_type} checksum mismatch for {path}"


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
