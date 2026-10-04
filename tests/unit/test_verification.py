import json

import pytest

from agrifm_g.domain.records import DocumentRecord, ImageRef, record_from_json, record_to_json
from agrifm_g.domain.verification import verify_records


def record(doc_id="d1", images=()):
    return DocumentRecord(
        doc_id=doc_id,
        source_url="https://example.org/a.pdf",
        pdf_path=f"pdfs/{doc_id}.pdf",
        pdf_sha256="b" * 64,
        text="t",
        images=images,
    )


def test_a_complete_dataset_has_no_problems():
    image = ImageRef(
        path="images/d1/000.png",
        page=0,
        width=50,
        height=50,
        format="png",
        sha256="a" * 64,
        n_colours=4,
        dominant_colour_share=0.02,
        near_white_share=0.02,
        edge_density=0.25,
    )
    assert verify_records([record(images=(image,))], {"pdfs/d1.pdf", "images/d1/000.png"}) == []


def test_a_missing_pdf_is_reported():
    assert verify_records([record()], set()) == ["d1: missing pdf file pdfs/d1.pdf"]


def test_a_missing_image_is_reported():
    image = ImageRef(
        path="images/d1/000.png",
        page=0,
        width=50,
        height=50,
        format="png",
        sha256="a" * 64,
        n_colours=4,
        dominant_colour_share=0.02,
        near_white_share=0.02,
        edge_density=0.25,
    )
    problems = verify_records([record(images=(image,))], {"pdfs/d1.pdf"})
    assert problems == ["d1: missing image file images/d1/000.png"]


def test_duplicate_doc_ids_are_reported():
    problems = verify_records([record(), record()], {"pdfs/d1.pdf"})
    assert "duplicate doc_id: d1" in problems


def test_a_pdf_whose_bytes_changed_is_reported():
    problems = verify_records([record()], {"pdfs/d1.pdf"}, {"pdfs/d1.pdf": "deadbeef"})
    assert problems == ["d1: pdf checksum mismatch for pdfs/d1.pdf"]


def test_a_matching_checksum_is_silent():
    assert verify_records([record()], {"pdfs/d1.pdf"}, {"pdfs/d1.pdf": "b" * 64}) == []


def test_changed_image_bytes_at_the_same_path_are_reported():
    image = ImageRef(
        path="images/d1/000.png",
        page=0,
        width=50,
        height=50,
        format="png",
        sha256="a" * 64,
        n_colours=4,
        dominant_colour_share=0.02,
        near_white_share=0.02,
        edge_density=0.25,
    )

    problems = verify_records(
        [record(images=(image,))],
        {"pdfs/d1.pdf", image.path},
        {"pdfs/d1.pdf": "b" * 64, image.path: "c" * 64},
    )

    assert problems == ["d1: image checksum mismatch for images/d1/000.png"]


def test_matching_image_checksum_is_silent():
    image = ImageRef(
        path="images/d1/000.png",
        page=0,
        width=50,
        height=50,
        format="png",
        sha256="c" * 64,
        n_colours=4,
        dominant_colour_share=0.02,
        near_white_share=0.02,
        edge_density=0.25,
    )

    assert (
        verify_records(
            [record(images=(image,))],
            {"pdfs/d1.pdf", image.path},
            {"pdfs/d1.pdf": "b" * 64, image.path: "c" * 64},
        )
        == []
    )


@pytest.mark.parametrize("recorded_hash", ["", "not-a-sha256"])
def test_missing_or_malformed_recorded_image_hash_is_a_mismatch(recorded_hash):
    image = ImageRef(
        path="images/d1/000.png",
        page=0,
        width=50,
        height=50,
        format="png",
        sha256=recorded_hash,
        n_colours=4,
        dominant_colour_share=0.02,
        near_white_share=0.02,
        edge_density=0.25,
    )

    assert verify_records(
        [record(images=(image,))],
        {"pdfs/d1.pdf", image.path},
        {"pdfs/d1.pdf": "b" * 64, image.path: "c" * 64},
    ) == ["d1: image checksum mismatch for images/d1/000.png"]


def test_missing_image_hash_field_is_rejected_by_record_loader():
    image = ImageRef(
        path="images/d1/000.png",
        page=0,
        width=50,
        height=50,
        format="png",
        sha256="a" * 64,
        n_colours=4,
        dominant_colour_share=0.02,
        near_white_share=0.02,
        edge_density=0.25,
    )
    payload = json.loads(record_to_json(record(images=(image,))))
    del payload["images"][0]["sha256"]

    with pytest.raises(ValueError, match="malformed record"):
        record_from_json(payload)
