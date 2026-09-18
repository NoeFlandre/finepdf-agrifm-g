from agrifm_g.domain.records import DocumentRecord, ImageRef
from agrifm_g.domain.rows import image_rows


def record(n_images=2, doc_id="d1"):
    return DocumentRecord(
        doc_id=doc_id,
        source_url="https://example.org/a.pdf",
        pdf_path=f"pdfs/{doc_id}.pdf",
        pdf_sha256="b" * 64,
        text="hello",
        images=tuple(
            ImageRef(
                path=f"images/{doc_id}/{i:03d}.png",
                page=i,
                width=10 + i,
                height=20 + i,
                format="png",
                sha256=str(i) * 64,
                n_colours=5,
            )
            for i in range(n_images)
        ),
    )


def test_one_row_per_image_carrying_its_document_context():
    rows = image_rows([record(2)])
    assert len(rows) == 2
    assert rows[0]["doc_id"] == "d1"
    assert rows[0]["image_index"] == 0
    assert rows[1]["image_index"] == 1
    assert rows[0]["text"] == "hello"
    assert rows[0]["n_images_in_doc"] == 2
    assert rows[0]["image_path"] == "images/d1/000.png"


def test_a_document_without_images_contributes_no_rows():
    assert image_rows([record(0)]) == []


def test_row_order_is_stable_and_independent_of_input_order():
    first = image_rows([record(1, "b"), record(1, "a")])
    second = image_rows([record(1, "a"), record(1, "b")])
    assert [row["doc_id"] for row in first] == [row["doc_id"] for row in second] == ["a", "b"]


def test_a_row_carries_every_declared_column_with_the_right_value():
    row = image_rows([record(2)])[1]
    assert row == {
        "doc_id": "d1",
        "page": 1,
        "image_index": 1,
        "width": 11,
        "height": 21,
        "image_sha256": "1" * 64,
        "image_path": "images/d1/001.png",
        "source_url": "https://example.org/a.pdf",
        "pdf_sha256": "b" * 64,
        "text": "hello",
        "n_images_in_doc": 2,
        "extraction_version": 2,
    }
