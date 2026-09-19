import json

import pytest

from agrifm_g.adapters.extraction import ExtractedImage
from agrifm_g.adapters.storage import DocumentPayload, existing_files, read_records, write_dataset
from agrifm_g.domain.records import EXTRACTION_VERSION


def payload(doc_id="<urn:uuid:AB>", n_images=1):
    return DocumentPayload(
        raw_doc_id=doc_id,
        source_url="https://example.org/a.pdf",
        text="hello",
        pdf_bytes=b"%PDF-1.4 fake",
        images=tuple(
            ExtractedImage(
                page=i,
                width=100,
                height=100,
                format="png",
                data=b"\x89PNG" + bytes([i]),
                sha256=str(i) * 64,
                n_colours=30000,
                dominant_colour_share=0.02,
                near_white_share=0.02,
                edge_density=0.25,
            )
            for i in range(n_images)
        ),
    )


def test_writing_lays_out_pdfs_images_and_metadata(tmp_path):
    write_dataset(tmp_path, [payload()])
    assert (tmp_path / "pdfs" / "urn_uuid_ab.pdf").exists()
    assert (tmp_path / "images" / "urn_uuid_ab" / "000.png").exists()
    assert (tmp_path / "metadata.jsonl").exists()


def test_metadata_is_one_valid_record_per_document(tmp_path):
    write_dataset(tmp_path, [payload(), payload(doc_id="second")])
    lines = (tmp_path / "metadata.jsonl").read_text().splitlines()
    assert len(lines) == 2
    assert json.loads(lines[0])["extraction_version"] == EXTRACTION_VERSION


def test_records_round_trip_from_disk(tmp_path):
    written = write_dataset(tmp_path, [payload(n_images=2)])
    assert read_records(tmp_path) == written


def test_written_output_is_byte_stable(tmp_path):
    first = tmp_path / "a"
    second = tmp_path / "b"
    write_dataset(first, [payload(), payload(doc_id="second")])
    write_dataset(second, [payload(), payload(doc_id="second")])
    assert (first / "metadata.jsonl").read_bytes() == (second / "metadata.jsonl").read_bytes()


def test_every_referenced_file_exists_after_writing(tmp_path):
    records = write_dataset(tmp_path, [payload(n_images=3)])
    present = existing_files(tmp_path)
    assert all(image.path in present for record in records for image in record.images)


def test_colliding_document_ids_are_refused(tmp_path):
    with pytest.raises(ValueError):
        write_dataset(tmp_path, [payload(doc_id="a"), payload(doc_id="A")])
