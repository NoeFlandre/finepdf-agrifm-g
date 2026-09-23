"""Which images earn a place in the dataset, and why the others did not."""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable
from dataclasses import replace
from enum import StrEnum

from agrifm_g.domain.appearance import ImageMetrics, rejection_rule
from agrifm_g.domain.records import DocumentRecord, ImageRef

MAX_ASPECT_RATIO = 20.0
"""Beyond this, an image is a rule, a separator or a scan edge, not a picture."""


class DropReason(StrEnum):
    """Every removal is attributable."""

    DUPLICATE = "duplicate"
    SINGLE_COLOUR = "single_colour"
    ASPECT_RATIO = "aspect_ratio"
    FEW_COLOURS = "few_colours"
    MOSTLY_BLANK = "mostly_blank"
    FLAT_BACKGROUND = "flat_background"
    LOW_INFORMATION = "low_information"
    DOCUMENT_PAGE_SCAN = "document_page_scan"


def keep_reason(image: ImageRef) -> DropReason | None:
    """Return why this image should be dropped, or None to keep it."""
    if image.n_colours <= 1:
        return DropReason.SINGLE_COLOUR
    if image.document_page_scan:
        return DropReason.DOCUMENT_PAGE_SCAN
    if _has_extreme_aspect_ratio(image.width, image.height):
        return DropReason.ASPECT_RATIO
    return _appearance_reason(image)


def _has_extreme_aspect_ratio(width: int, height: int) -> bool:
    longest, shortest = max(width, height), min(width, height)
    return shortest == 0 or longest / shortest > MAX_ASPECT_RATIO


def _appearance_reason(image: ImageRef) -> DropReason | None:
    appearance = rejection_rule(_metrics(image))
    return DropReason(appearance.value) if appearance else None


def _metrics(image: ImageRef) -> ImageMetrics:
    return ImageMetrics(
        n_colours=image.n_colours,
        dominant_colour_share=image.dominant_colour_share,
        near_white_share=image.near_white_share,
        edge_density=image.edge_density,
        greyscale=image.greyscale,
    )


def deduplicate(
    records: Iterable[DocumentRecord],
) -> tuple[list[DocumentRecord], dict[DropReason, int]]:
    """Drop degenerate and repeated images, keeping the first occurrence of each."""
    seen: set[str] = set()
    dropped: Counter[DropReason] = Counter()
    kept = [_filter_record(record, seen, dropped) for record in records]
    return kept, dict(dropped)


def _filter_record(
    record: DocumentRecord, seen: set[str], dropped: Counter[DropReason]
) -> DocumentRecord:
    images = tuple(image for image in record.images if _keep(image, seen, dropped))
    return replace(record, images=images)


def _keep(image: ImageRef, seen: set[str], dropped: Counter[DropReason]) -> bool:
    reason = keep_reason(image)
    if reason is None and image.sha256 in seen:
        reason = DropReason.DUPLICATE
    if reason is not None:
        dropped[reason] += 1
        return False
    seen.add(image.sha256)
    return True
