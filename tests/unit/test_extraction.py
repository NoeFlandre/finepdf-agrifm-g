import io

import pytest
from PIL import Image, ImageDraw

from agrifm_g.adapters.appearance import measure
from agrifm_g.adapters.extraction import extract_images
from agrifm_g.domain.appearance import AppearanceRule, rejection_rule


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


def test_captionless_images_are_retained(monkeypatch):
    import agrifm_g.adapters.extraction as extraction

    class Page:
        images = [type("ImageItem", (), {"image": Image.new("RGB", (200, 150), "green")})()]

        def extract_text(self):
            return "The wheat trial is discussed here."

    class Reader:
        pages = [Page()]

    monkeypatch.setattr(extraction, "PdfReader", lambda _: Reader())

    accepted = extract_images(b"pdf")
    assert len(accepted) == 1
    assert accepted[0].caption == ""


def test_a_page_sized_document_raster_is_marked_for_filtering():
    scan = Image.new("RGB", (400, 566), "white")
    draw = ImageDraw.Draw(scan)
    for y in range(50, 520, 24):
        draw.line((25, y, 375, y), fill="black", width=1)
    for x in (25, 90, 170, 260, 375):
        draw.line((x, 50, x, 520), fill="black", width=1)

    pdf = io.BytesIO()
    scan.save(pdf, format="PDF", resolution=72)
    extracted = extract_images(pdf.getvalue())
    assert len(extracted) == 1
    assert extracted[0].document_page_scan is True


def test_a_full_page_colour_photo_is_not_marked_as_a_document_scan():
    photo = Image.new("RGB", (400, 566), "#6b8e23")
    draw = ImageDraw.Draw(photo)
    for y in range(0, photo.height, 12):
        draw.rectangle(
            (0, y, photo.width, y + 11),
            fill=(70 + y % 70, 90 + y % 80, 30 + y % 60),
        )

    pdf = io.BytesIO()
    photo.save(pdf, format="PDF", resolution=72)
    extracted = extract_images(pdf.getvalue())
    assert len(extracted) == 1
    assert extracted[0].document_page_scan is False


def test_full_raster_colour_count_is_not_recomputed_before_thumbnail(monkeypatch):
    image = Image.new("RGB", (512, 512), "blue")
    pdf = io.BytesIO()
    image.save(pdf, format="PDF", resolution=72)

    measured_sizes = []
    original_getcolors = Image.Image.getcolors

    def track_getcolors(instance, maxcolors=256):
        measured_sizes.append(instance.size)
        return original_getcolors(instance, maxcolors=maxcolors)

    monkeypatch.setattr(Image.Image, "getcolors", track_getcolors)

    extracted = extract_images(pdf.getvalue())
    assert len(extracted) == 1
    assert measured_sizes == [(256, 256)]


def test_a_nearly_solid_black_placeholder_is_rejected_from_its_pixels():
    placeholder = Image.new("RGB", (133, 119), "white")
    ImageDraw.Draw(placeholder).rounded_rectangle((2, 2, 130, 116), radius=18, fill="black")
    png = io.BytesIO()
    placeholder.save(png, format="PNG")

    assert rejection_rule(measure(png.getvalue())) is AppearanceRule.LOW_INFORMATION


def test_caption_terms_are_not_an_extraction_filter():
    import inspect

    import agrifm_g.adapters.extraction as extraction

    assert "caption_terms" not in inspect.signature(extraction.extract_images).parameters
