"""Measure only obvious visual degeneracy; semantic relevance comes from document text."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

MAX_NEAR_WHITE_SHARE = 0.98
"""A frame this white is almost certainly blank or a scan margin."""

MAX_DOMINANT_COLOUR_SHARE = 0.98
"""A frame this uniform is a placeholder or a flat colour swatch."""

MAX_LOW_INFORMATION_COLOURS = 64
MIN_LOW_INFORMATION_DOMINANT_SHARE = 0.75
MAX_LOW_INFORMATION_EDGE_DENSITY = 0.10

MIN_DOCUMENT_PAGE_NEAR_WHITE_SHARE = 0.45
MIN_DOCUMENT_PAGE_EDGE_DENSITY = 0.18
DOCUMENT_PAGE_ASPECT_TOLERANCE = 0.03


class AppearanceRule(StrEnum):
    """Why an image was rejected by the cheap visual sanity filter."""

    FEW_COLOURS = "few_colours"
    MOSTLY_BLANK = "mostly_blank"
    FLAT_BACKGROUND = "flat_background"
    LOW_INFORMATION = "low_information"


@dataclass(frozen=True, slots=True)
class ImageMetrics:
    """Cheap diagnostics computed once from a small thumbnail."""

    n_colours: int
    dominant_colour_share: float
    near_white_share: float
    edge_density: float
    greyscale: bool = False


def rejection_rule(metrics: ImageMetrics) -> AppearanceRule | None:
    """Reject only images that are clearly blank, flat, or nearly featureless."""
    if metrics.n_colours <= 1:
        return AppearanceRule.FEW_COLOURS
    if metrics.near_white_share > MAX_NEAR_WHITE_SHARE:
        return AppearanceRule.MOSTLY_BLANK
    if metrics.dominant_colour_share > MAX_DOMINANT_COLOUR_SHARE:
        return AppearanceRule.FLAT_BACKGROUND
    if _is_low_information(metrics):
        return AppearanceRule.LOW_INFORMATION
    return None


def _is_low_information(metrics: ImageMetrics) -> bool:
    return (
        metrics.n_colours <= MAX_LOW_INFORMATION_COLOURS
        and metrics.dominant_colour_share >= MIN_LOW_INFORMATION_DOMINANT_SHARE
        and metrics.edge_density <= MAX_LOW_INFORMATION_EDGE_DENSITY
    )


def looks_like_document_page_scan(
    metrics: ImageMetrics,
    *,
    image_width: int,
    image_height: int,
    page_width: float,
    page_height: float,
    page_image_count: int,
) -> bool:
    """Match the conservative visual profile of a grayscale document-page scan."""
    if page_image_count != 1:
        return False
    if not _has_positive_dimensions(image_width, image_height, page_width, page_height):
        return False
    if not _has_document_scan_appearance(metrics):
        return False
    return _page_aspects_match(image_width, image_height, page_width, page_height)


def _has_positive_dimensions(
    image_width: int,
    image_height: int,
    page_width: float,
    page_height: float,
) -> bool:
    return min(image_width, image_height, page_width, page_height) > 0


def _has_document_scan_appearance(metrics: ImageMetrics) -> bool:
    return (
        metrics.greyscale
        and metrics.near_white_share >= MIN_DOCUMENT_PAGE_NEAR_WHITE_SHARE
        and metrics.edge_density >= MIN_DOCUMENT_PAGE_EDGE_DENSITY
    )


def _page_aspects_match(
    image_width: int,
    image_height: int,
    page_width: float,
    page_height: float,
) -> bool:
    image_ratio = image_width / image_height
    page_ratio = page_width / page_height
    aspect_similarity = min(image_ratio, page_ratio) / max(image_ratio, page_ratio)
    return aspect_similarity >= 1 - DOCUMENT_PAGE_ASPECT_TOLERANCE
