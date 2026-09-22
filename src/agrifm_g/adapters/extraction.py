"""Extract raster images from PDF bytes."""

from __future__ import annotations

import hashlib
import io
from dataclasses import dataclass, replace
from typing import Any

from pypdf import PageObject, PdfReader
from pypdf._page import ImageFile
from pypdf.errors import DependencyError, PyPdfError

from agrifm_g.adapters.appearance import measure
from agrifm_g.domain.captions import captions_for_images, extract_caption_blocks
from agrifm_g.domain.normalisation import is_usable_image


class ExtractionError(RuntimeError):
    """The bytes handed over are not a PDF we can read.

    `DependencyError` is listed explicitly because pypdf does not derive it from
    `PyPdfError`: an encrypted document raised it straight through an earlier version of
    this function and took a 350-document build down with it.
    """


@dataclass(frozen=True, slots=True)
class ExtractedImage:
    """One image lifted out of a PDF, still in memory."""

    page: int
    width: int
    height: int
    format: str
    data: bytes
    sha256: str
    n_colours: int
    dominant_colour_share: float
    near_white_share: float
    edge_density: float
    greyscale: bool = False
    caption: str = ""


def extract_images(pdf_bytes: bytes) -> tuple[ExtractedImage, ...]:
    """Return every usable embedded raster image, with optional caption metadata."""
    try:
        reader = PdfReader(io.BytesIO(pdf_bytes))
        pages = list(reader.pages)
    except (PyPdfError, DependencyError, ValueError, OSError) as error:
        raise ExtractionError(f"unreadable PDF: {error}") from error
    return tuple(
        image
        for page_number, page in enumerate(pages)
        for image in _page_images(page_number, page)
    )


def _page_images(
    page_number: int,
    page: PageObject,
) -> list[ExtractedImage]:
    try:
        embedded = list(page.images)
    except Exception:  # noqa: BLE001 - a broken page must not sink the document
        return []
    candidates = _extract_page_images(page_number, embedded)
    captions = captions_for_images(extract_caption_blocks(_page_text(page)), len(candidates))
    return _captioned_images(candidates, captions)


def _page_text(page: PageObject) -> str:
    try:
        return page.extract_text() or ""
    except Exception:  # noqa: BLE001 - caption extraction must not sink a document
        return ""


def _captioned_images(
    candidates: list[ExtractedImage],
    captions: tuple[str, ...],
) -> list[ExtractedImage]:
    return [replace(image, caption=captions[index]) for index, image in enumerate(candidates)]


def _extract_page_images(page_number: int, embedded: list[ImageFile]) -> list[ExtractedImage]:
    extracted = []
    for item in embedded:
        encoded = _as_png(item)
        if encoded is None:
            continue
        width, height, _, data = encoded
        if is_usable_image(width=width, height=height, n_bytes=len(data)):
            metrics = measure(data)
            extracted.append(
                ExtractedImage(
                    page=page_number,
                    width=width,
                    height=height,
                    format="png",
                    data=data,
                    sha256=hashlib.sha256(data).hexdigest(),
                    n_colours=metrics.n_colours,
                    dominant_colour_share=metrics.dominant_colour_share,
                    near_white_share=metrics.near_white_share,
                    edge_density=metrics.edge_density,
                    greyscale=metrics.greyscale,
                )
            )
    return extracted


def _as_png(item: ImageFile) -> tuple[int, int, int, bytes] | None:
    """Re-encode to PNG, and count colours so flat filler can be recognised later."""
    # pypdf types this as Optional[PIL.Image]; the stub resolves to None for `ty`.
    image: Any = item.image
    if image is None:
        return None
    buffer = io.BytesIO()
    try:
        rgb = image.convert("RGB")
        rgb.save(buffer, format="PNG", optimize=False)
    except (OSError, ValueError):  # unsupported filters and colour spaces are skipped
        return None
    colours = rgb.getcolors(maxcolors=256)
    return image.width, image.height, len(colours) if colours else 257, buffer.getvalue()
