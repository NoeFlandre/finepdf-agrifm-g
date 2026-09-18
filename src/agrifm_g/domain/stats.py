"""The numbers a reader needs before deciding to download anything."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from statistics import median

from agrifm_g.domain.dedup import DropReason
from agrifm_g.domain.records import EXTRACTION_VERSION, DocumentRecord, ImageRef


def build_stats(
    records: Sequence[DocumentRecord],
    *,
    sampled: int,
    dropped: Mapping[DropReason, int],
    seed: int,
) -> dict:
    """Aggregate a finished build. Pure, and deterministic for a given build."""
    return {
        "seed": seed,
        "extraction_version": EXTRACTION_VERSION,
        "documents": _document_stats(records, sampled),
        "images": _image_stats(_all_images(records), dropped),
    }


def _document_stats(records: Sequence[DocumentRecord], sampled: int) -> dict:
    return {
        "sampled": sampled,
        "built": len(records),
        "fetch_yield": _ratio(len(records), sampled),
        "with_images": _count_with_images(records),
        "text_length": _summarise(_text_lengths(records)),
        "images_per_document": _summarise(_image_counts(records)),
    }


def _image_stats(images: Sequence[ImageRef], dropped: Mapping[DropReason, int]) -> dict:
    return {
        "total": len(images),
        "dropped": _dropped_by_reason(dropped),
        "width": _summarise(_widths(images)),
        "height": _summarise(_heights(images)),
        "megapixels": round(_total_pixels(images) / 1e6, 2),
    }


def _all_images(records: Sequence[DocumentRecord]) -> list[ImageRef]:
    return [image for record in records for image in record.images]


def _count_with_images(records: Sequence[DocumentRecord]) -> int:
    return sum(1 for record in records if record.images)


def _text_lengths(records: Sequence[DocumentRecord]) -> list[int]:
    return [len(record.text) for record in records]


def _image_counts(records: Sequence[DocumentRecord]) -> list[int]:
    return [record.n_images for record in records]


def _widths(images: Sequence[ImageRef]) -> list[int]:
    return [image.width for image in images]


def _heights(images: Sequence[ImageRef]) -> list[int]:
    return [image.height for image in images]


def _total_pixels(images: Sequence[ImageRef]) -> int:
    return sum(image.width * image.height for image in images)


def _dropped_by_reason(dropped: Mapping[DropReason, int]) -> dict[str, int]:
    return {reason.value: count for reason, count in sorted(dropped.items())}


def _ratio(part: int, whole: int) -> float:
    return round(part / whole, 4) if whole else 0.0


def _summarise(values: Sequence[int]) -> dict[str, float]:
    if not values:
        return {"min": 0, "median": 0, "max": 0, "mean": 0.0}
    ordered = sorted(values)
    return {
        "min": ordered[0],
        "median": int(median(ordered)),
        "max": ordered[-1],
        "mean": round(sum(ordered) / len(ordered), 2),
    }
