import json

import pytest
from hypothesis import given
from hypothesis import strategies as st

from agrifm_g.domain.records import (
    EXTRACTION_VERSION,
    DocumentRecord,
    ImageRef,
    record_from_json,
    record_to_json,
)


def a_record(n_images: int = 2) -> DocumentRecord:
    return DocumentRecord(
        doc_id="doc-1",
        source_url="https://example.org/a.pdf",
        pdf_path="pdfs/doc-1.pdf",
        pdf_sha256="b" * 64,
        text="hello",
        images=tuple(
            ImageRef(
                path=f"images/doc-1/{i:03d}.png",
                page=i,
                width=100,
                height=120,
                format="png",
                sha256=str(i) * 64,
                n_colours=8,
                dominant_colour_share=0.02,
                near_white_share=0.02,
                edge_density=0.25,
            )
            for i in range(n_images)
        ),
    )


def test_n_images_is_derived_not_stored():
    assert a_record(3).n_images == 3


def test_records_round_trip_through_json():
    record = a_record()
    assert record_from_json(json.loads(record_to_json(record))) == record


def test_serialisation_carries_the_extraction_version():
    assert json.loads(record_to_json(a_record()))["extraction_version"] == EXTRACTION_VERSION


def test_an_empty_doc_id_is_rejected():
    with pytest.raises(ValueError):
        DocumentRecord(
            doc_id="", source_url="u", pdf_path="p", pdf_sha256="b" * 64, text="t", images=()
        )


def test_duplicate_image_paths_are_rejected():
    duplicate = ImageRef(
        path="images/a.png",
        page=0,
        width=10,
        height=10,
        format="png",
        sha256="a" * 64,
        n_colours=30000,
        dominant_colour_share=0.02,
        near_white_share=0.02,
        edge_density=0.25,
    )
    with pytest.raises(ValueError):
        DocumentRecord(
            doc_id="d",
            source_url="u",
            pdf_path="p",
            pdf_sha256="b" * 64,
            text="t",
            images=(duplicate, duplicate),
        )


@given(
    doc_id=st.text(min_size=1, max_size=20),
    text=st.text(max_size=200),
    n_images=st.integers(min_value=0, max_value=5),
)
def test_round_trip_is_identity_and_n_images_matches(doc_id, text, n_images):
    record = DocumentRecord(
        doc_id=doc_id,
        source_url="https://example.org/a.pdf",
        pdf_path="pdfs/x.pdf",
        pdf_sha256="b" * 64,
        text=text,
        images=tuple(
            ImageRef(
                path=f"images/x/{i}.png",
                page=i,
                width=1,
                height=1,
                format="png",
                sha256=str(i) * 64,
                n_colours=3,
                dominant_colour_share=0.02,
                near_white_share=0.02,
                edge_density=0.25,
            )
            for i in range(n_images)
        ),
    )
    assert record_from_json(json.loads(record_to_json(record))) == record
    assert record.n_images == len(record.images)


def test_a_malformed_payload_is_rejected():
    with pytest.raises(ValueError):
        record_from_json({"doc_id": "d"})


GOLDEN = (
    '{"doc_id": "doc-1", "extraction_version": 3, '
    '"images": [{"dominant_colour_share": 0.02, "edge_density": 0.25, "format": "png", '
    '"height": 120, "n_colours": 8, "near_white_share": 0.02, "page": 0, '
    '"path": "images/doc-1/000.png", "sha256": "' + "0" * 64 + '", "width": 100}], '
    '"n_images": 1, "pdf_path": "pdfs/doc-1.pdf", '
    '"pdf_sha256": "' + "b" * 64 + '", '
    '"source_url": "https://example.org/a.pdf", "text": "hello"}'
)


def test_serialisation_matches_the_golden_line_exactly():
    assert record_to_json(a_record(n_images=1)) == GOLDEN


def test_non_ascii_text_is_stored_as_utf8_not_escaped():
    record = DocumentRecord(
        doc_id="d",
        source_url="u",
        pdf_path="p",
        pdf_sha256="b" * 64,
        text="blé récolté 麦",
        images=(),
    )
    assert "blé récolté 麦" in record_to_json(record)
