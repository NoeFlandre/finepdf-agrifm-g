"""Measure only obvious visual degeneracy; semantic relevance comes from document text."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

MAX_NEAR_WHITE_SHARE = 0.98
"""A frame this white is almost certainly blank or a scan margin."""

MAX_DOMINANT_COLOUR_SHARE = 0.98
"""A frame this uniform is a placeholder or a flat colour swatch."""


class AppearanceRule(StrEnum):
    """Why an image was rejected by the cheap visual sanity filter."""

    FEW_COLOURS = "few_colours"
    MOSTLY_BLANK = "mostly_blank"
    FLAT_BACKGROUND = "flat_background"


@dataclass(frozen=True, slots=True)
class ImageMetrics:
    """Cheap diagnostics computed once from a small thumbnail."""

    n_colours: int
    dominant_colour_share: float
    near_white_share: float
    edge_density: float
    greyscale: bool = False


def rejection_rule(metrics: ImageMetrics) -> AppearanceRule | None:
    """Reject only images that are clearly blank, flat, or single-colour."""
    if metrics.n_colours <= 1:
        return AppearanceRule.FEW_COLOURS
    if metrics.near_white_share > MAX_NEAR_WHITE_SHARE:
        return AppearanceRule.MOSTLY_BLANK
    if metrics.dominant_colour_share > MAX_DOMINANT_COLOUR_SHARE:
        return AppearanceRule.FLAT_BACKGROUND
    return None
