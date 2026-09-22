import pytest
from PIL import Image

from agrifm_g.adapters.extraction import extract_images


def test_a_single_page_pdf_yields_its_image(fixtures):
    images = extract_images((fixtures / "one_image.pdf").read_bytes())
    assert len(images) == 1
    image = images[0]
    assert (image.page, image.width, image.height) == (0, 200, 150)
    assert image.format == "png"
    assert image.data[:8] == b"\x89PNG\r\n\x1a\n"


def test_a_pdf_without_images_yields_nothing(fixtures):
    assert extract_images((fixtures / "no_image.pdf").read_bytes()) == ()


def test_images_are_reported_with_their_page_number(fixtures):
    images = extract_images((fixtures / "two_pages.pdf").read_bytes())
    assert [image.page for image in images] == [0, 1]


def test_degenerate_images_are_dropped(fixtures):
    assert extract_images((fixtures / "tiny_image.pdf").read_bytes()) == ()


def test_extraction_is_deterministic(fixtures):
    pdf = (fixtures / "two_pages.pdf").read_bytes()
    assert extract_images(pdf) == extract_images(pdf)


def test_an_unreadable_pdf_is_reported_as_such(fixtures):
    import pytest

    from agrifm_g.adapters.extraction import ExtractionError

    with pytest.raises(ExtractionError):
        extract_images(b"this is not a pdf")


def test_an_aes_encrypted_pdf_is_read_rather_than_crashing(fixtures):
    """Regression: a single AES-encrypted document used to abort an entire build."""
    images = extract_images((fixtures / "encrypted_aes.pdf").read_bytes())
    assert [(image.width, image.height) for image in images] == [(120, 90)]


def test_a_missing_crypto_backend_becomes_an_extraction_error(fixtures, monkeypatch):
    """Regression: pypdf's DependencyError does not derive from PyPdfError."""
    from pypdf.errors import DependencyError

    import agrifm_g.adapters.extraction as extraction

    def explode(*args, **kwargs):
        raise DependencyError("cryptography>=3.1 is required for AES algorithm")

    monkeypatch.setattr(extraction, "PdfReader", explode)
    with pytest.raises(extraction.ExtractionError):
        extract_images((fixtures / "one_image.pdf").read_bytes())


def test_caption_filter_uses_an_explicit_caption_not_nearby_page_text(monkeypatch):
    import agrifm_g.adapters.extraction as extraction

    class Page:
        images = [type("ImageItem", (), {"image": Image.new("RGB", (200, 150), "green")})()]

        def extract_text(self):
            return "The wheat trial is discussed here.\nFigure 1. Wheat leaf canopy."

    class Reader:
        pages = [Page()]

    monkeypatch.setattr(extraction, "PdfReader", lambda _: Reader())

    accepted = extract_images(b"pdf", caption_terms={"wheat"})
    assert len(accepted) == 1
    assert accepted[0].caption == "Figure 1. Wheat leaf canopy."
    assert extract_images(b"pdf", caption_terms={"maize"}) == ()
