from agrifm_g.domain.records import DocumentRecord, ImageRef
from agrifm_g.domain.verification import verify_records


def record(doc_id="d1", images=()):
    return DocumentRecord(
        doc_id=doc_id,
        source_url="https://example.org/a.pdf",
        pdf_path=f"pdfs/{doc_id}.pdf",
        text="t",
        images=images,
    )


def test_a_complete_dataset_has_no_problems():
    image = ImageRef(path="images/d1/000.png", page=0, width=50, height=50, format="png")
    assert verify_records([record(images=(image,))], {"pdfs/d1.pdf", "images/d1/000.png"}) == []


def test_a_missing_pdf_is_reported():
    assert verify_records([record()], set()) == ["d1: missing pdf file pdfs/d1.pdf"]


def test_a_missing_image_is_reported():
    image = ImageRef(path="images/d1/000.png", page=0, width=50, height=50, format="png")
    problems = verify_records([record(images=(image,))], {"pdfs/d1.pdf"})
    assert problems == ["d1: missing image file images/d1/000.png"]


def test_duplicate_doc_ids_are_reported():
    problems = verify_records([record(), record()], {"pdfs/d1.pdf"})
    assert "duplicate doc_id: d1" in problems
