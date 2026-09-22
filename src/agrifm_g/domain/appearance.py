"""Reject images from their appearance alone: no model, no labels at decision time.

The thresholds were fitted on `data/labels/relevance_v1.jsonl` by `scripts/fit_appearance.py`
and are deliberately conservative: this stage may only drop what it is nearly certain about,
because an image dropped here is never seen by anything downstream.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

# The stricter preset keeps all ten labelled positives while removing another third of the
# appearance survivors. The set is still small, so these remain experimental boundaries.
MIN_COLOURS = 8000
"""Below this an image is usually a logo, an icon or line art, not a photograph."""

MIN_EDGE_DENSITY = 0.18
"""Below this a colourful image is too smooth to be a useful photograph."""

GREYSCALE_MIN_EDGE_DENSITY = 0.30
"""Greyscale images are judged on texture alone, because `MIN_COLOURS` cannot judge them.

An 8-bit greyscale photograph holds at most 256 distinct colours, so the colour-count rule
rejects every one of them on a technicality — scanned field photographs and electron
micrographs included, which are exactly what this dataset wants. Texture separates them
cleanly instead: on the 33 greyscale images of the 30-shard build, the photographs and
micrographs sit at 0.300-0.382 and the charts at 0.13-0.21. The nearest reject is a CT scan
at 0.283, so this boundary carries a ~6% margin and is the tightest in this module.
"""

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
    FLAT_GREYSCALE = "flat_greyscale"
    MOSTLY_BLANK = "mostly_blank"
    FLAT_BACKGROUND = "flat_background"
    LINE_ART = "line_art"
    LOW_TEXTURE = "low_texture"


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
    greyscale: bool = False


def rejection_rule(metrics: ImageMetrics) -> AppearanceRule | None:
    """Return the rule that rejects this image, or None to pass it on."""
    if metrics.greyscale:
        return _greyscale_rejection(metrics)
    checks = (
        (metrics.n_colours <= MIN_COLOURS, AppearanceRule.FEW_COLOURS),
        (metrics.near_white_share > MAX_NEAR_WHITE_SHARE, AppearanceRule.MOSTLY_BLANK),
        (metrics.dominant_colour_share > MAX_DOMINANT_COLOUR_SHARE, AppearanceRule.FLAT_BACKGROUND),
        (_is_line_art(metrics), AppearanceRule.LINE_ART),
        (metrics.edge_density < MIN_EDGE_DENSITY, AppearanceRule.LOW_TEXTURE),
    )
    return next((rule for failed, rule in checks if failed), None)


def _greyscale_rejection(metrics: ImageMetrics) -> AppearanceRule | None:
    """Judge a greyscale image on texture and blankness, never on its colour count."""
    checks = (
        (metrics.near_white_share > MAX_NEAR_WHITE_SHARE, AppearanceRule.MOSTLY_BLANK),
        (metrics.dominant_colour_share > MAX_DOMINANT_COLOUR_SHARE, AppearanceRule.FLAT_BACKGROUND),
        (metrics.edge_density < GREYSCALE_MIN_EDGE_DENSITY, AppearanceRule.FLAT_GREYSCALE),
    )
    return next((rule for failed, rule in checks if failed), None)


def _is_line_art(metrics: ImageMetrics) -> bool:
    """A limited palette on its own is not enough; it must also be nearly edgeless."""
    return metrics.n_colours <= LINE_ART_COLOURS and metrics.edge_density < LINE_ART_EDGE_DENSITY
