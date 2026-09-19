"""Reject images from their appearance alone: no model, no labels at decision time.

The thresholds were fitted on `data/labels/relevance_v1.jsonl` by `scripts/fit_appearance.py`
and are deliberately conservative: this stage may only drop what it is nearly certain about,
because an image dropped here is never seen by anything downstream.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

# Every threshold sits several times away from the weakest labelled keep, because the set
# holds only 10 of them: the weakest keep has 12 483 colours, 10 % near-white, a 5 % dominant
# colour and an edge density of 0.22. Margins, not a fitted boundary.
MIN_COLOURS = 4096
"""Below this an image is a logo, an icon or line art, not a photograph. (3x margin.)"""

MAX_NEAR_WHITE_SHARE = 0.80
"""A frame this white is a scan artefact or a blank. (8x margin.)"""

MAX_DOMINANT_COLOUR_SHARE = 0.55
"""One flat colour over half the frame is a background or a placeholder. (11x margin.)"""

LINE_ART_COLOURS = 16384
LINE_ART_EDGE_DENSITY = 0.08
"""Limited palette *and* almost no edges: a diagram or a chart on a plain ground.
(The weakest keep sits at 0.22 edge density, ~3x above this.)"""


class AppearanceRule(StrEnum):
    """Why an image was rejected on appearance."""

    FEW_COLOURS = "few_colours"
    MOSTLY_BLANK = "mostly_blank"
    FLAT_BACKGROUND = "flat_background"
    LINE_ART = "line_art"


@dataclass(frozen=True, slots=True)
class ImageMetrics:
    """Cheap statistics computed once, at extraction time.

    Size is deliberately absent: the size rules live in `normalisation` and `dedup`, and a
    field no rule reads is a field that drifts.
    """

    n_colours: int
    dominant_colour_share: float
    near_white_share: float
    edge_density: float


def rejection_rule(metrics: ImageMetrics) -> AppearanceRule | None:
    """Return the rule that rejects this image, or None to pass it on."""
    if metrics.n_colours <= MIN_COLOURS:
        return AppearanceRule.FEW_COLOURS
    if metrics.near_white_share > MAX_NEAR_WHITE_SHARE:
        return AppearanceRule.MOSTLY_BLANK
    if metrics.dominant_colour_share > MAX_DOMINANT_COLOUR_SHARE:
        return AppearanceRule.FLAT_BACKGROUND
    if _is_line_art(metrics):
        return AppearanceRule.LINE_ART
    return None


def _is_line_art(metrics: ImageMetrics) -> bool:
    """A limited palette on its own is not enough; it must also be nearly edgeless."""
    return metrics.n_colours <= LINE_ART_COLOURS and metrics.edge_density < LINE_ART_EDGE_DENSITY
