"""Which images earn a place in the dataset, and why the others did not."""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable
from dataclasses import replace
from enum import StrEnum

from agrifm_g.domain.records import DocumentRecord, ImageRef

MAX_ASPECT_RATIO = 20.0
"""Beyond this, an image is a rule, a separator or a scan edge, not a picture."""


class DropReason(StrEnum):
    """Every removal is attributable."""

    DUPLICATE = "duplicate"
    SINGLE_COLOUR = "single_colour"
    ASPECT_RATIO = "aspect_ratio"


def keep_reason(image: ImageRef) -> DropReason | None:
    """Return why this image should be dropped, or None to keep it."""
    if image.n_colours <= 1:
        return DropReason.SINGLE_COLOUR
    longest, shortest = max(image.width, image.height), min(image.width, image.height)
    if shortest == 0 or longest / shortest > MAX_ASPECT_RATIO:
        return DropReason.ASPECT_RATIO
    return None


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
