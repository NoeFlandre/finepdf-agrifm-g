"""Extract raster images from PDF bytes."""

from __future__ import annotations

import io
from dataclasses import dataclass
from typing import Any

from pypdf import PageObject, PdfReader
from pypdf._page import ImageFile
from pypdf.errors import PyPdfError

from agrifm_g.domain.normalisation import is_usable_image


class ExtractionError(RuntimeError):
    """The bytes handed over are not a PDF we can read."""


@dataclass(frozen=True, slots=True)
class ExtractedImage:
    """One image lifted out of a PDF, still in memory."""

    page: int
    width: int
    height: int
    format: str
    data: bytes


def extract_images(pdf_bytes: bytes) -> tuple[ExtractedImage, ...]:
    """Return the usable images of a PDF, in page order. Never touches the disk."""
    try:
        reader = PdfReader(io.BytesIO(pdf_bytes))
        pages = list(reader.pages)
    except (PyPdfError, ValueError, OSError) as error:
        raise ExtractionError(f"unreadable PDF: {error}") from error
    return tuple(
        image for page_number, page in enumerate(pages) for image in _page_images(page_number, page)
    )


def _page_images(page_number: int, page: PageObject) -> list[ExtractedImage]:
    try:
        embedded = list(page.images)
    except Exception:  # noqa: BLE001 - a broken page must not sink the document
        return []
    extracted = []
    for item in embedded:
        encoded = _as_png(item)
        if encoded is None:
            continue
        width, height, data = encoded
        if is_usable_image(width=width, height=height, n_bytes=len(data)):
            extracted.append(
                ExtractedImage(
                    page=page_number, width=width, height=height, format="png", data=data
                )
            )
    return extracted


def _as_png(item: ImageFile) -> tuple[int, int, bytes] | None:
    """Re-encode to PNG so the dataset has exactly one image format."""
    # pypdf types this as Optional[PIL.Image]; the stub resolves to None for `ty`.
    image: Any = item.image
    if image is None:
        return None
    buffer = io.BytesIO()
    try:
        image.convert("RGB").save(buffer, format="PNG", optimize=False)
    except (OSError, ValueError):  # unsupported filters and colour spaces are skipped
        return None
    return image.width, image.height, buffer.getvalue()
