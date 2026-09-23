"""Measure an image once, cheaply, so the decision itself stays pure."""

from __future__ import annotations

import io
from collections import Counter
from typing import Any

from PIL import Image, ImageFilter

from agrifm_g.domain.appearance import ImageMetrics

SAMPLE_SIDE = 256
"""Metrics are computed on a thumbnail: stable enough, and ~100x cheaper."""

NEAR_WHITE = 245
EDGE_THRESHOLD = 24

GREY_TOLERANCE = 8
"""How far R, G and B may differ before a pixel counts as coloured (JPEG noise allowance)."""

GREYSCALE_SHARE = 0.99
"""An image this uniformly neutral is greyscale, whatever colour space it was stored in."""


def measure(png_bytes: bytes) -> ImageMetrics:
    """Compute the appearance metrics of a stored PNG."""
    with Image.open(io.BytesIO(png_bytes)) as opened:
        sample = opened.convert("RGB")
    sample.thumbnail((SAMPLE_SIDE, SAMPLE_SIDE))
    pixels = sample.width * sample.height
    colours = sample.getcolors(maxcolors=1 << 24) or []
    coarse_colours = _coarse_histogram(colours)
    grey = sample.convert("L")
    return ImageMetrics(
        n_colours=len(colours),
        dominant_colour_share=max((count for count, _ in colours), default=0) / pixels,
        near_white_share=sum(grey.point(lambda v: 255 if v >= NEAR_WHITE else 0).histogram()[255:])
        / pixels,
        edge_density=_edge_density(grey, pixels),
        greyscale=_is_greyscale(colours, pixels),
        coarse_colour_bins=len(coarse_colours),
        coarse_dominant_share=max(coarse_colours.values(), default=0) / pixels,
    )


def _coarse_histogram(colours: list[tuple[int, Any]]) -> Counter:
    """Quantize the existing histogram, adding no full thumbnail pixel pass."""
    counts: Counter = Counter()
    for count, pixel in colours:
        channels = pixel[:3] if isinstance(pixel, tuple) else (pixel, pixel, pixel)
        counts[tuple(channel >> 5 for channel in channels)] += count
    return counts


def _is_greyscale(colours: list[tuple[int, Any]], pixels: int) -> bool:  # noqa: ANN401
    """Neutral pixels as a share of the frame, read off the colour histogram.

    Cheaper than a second pass over the pixels, and it tolerates the few stray coloured
    pixels that scanning and JPEG artefacts leave behind in an otherwise grey scan.
    """
    if not pixels:
        return False
    neutral = sum(count for count, pixel in colours if _is_neutral(pixel))
    return neutral / pixels >= GREYSCALE_SHARE


def _is_neutral(pixel: int | tuple[int, ...]) -> bool:
    """A single-band pixel is neutral by definition; an RGB one must be near-achromatic."""
    if not isinstance(pixel, tuple):
        return True
    channels = pixel[:3]
    return max(channels) - min(channels) <= GREY_TOLERANCE


def _edge_density(grey: Image.Image, pixels: int) -> float:
    edges = grey.filter(ImageFilter.FIND_EDGES)
    histogram = edges.histogram()
    return sum(histogram[EDGE_THRESHOLD:]) / pixels
