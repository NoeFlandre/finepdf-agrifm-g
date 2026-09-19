"""Measure an image once, cheaply, so the decision itself stays pure."""

from __future__ import annotations

import io

from PIL import Image, ImageFilter

from agrifm_g.domain.appearance import ImageMetrics

SAMPLE_SIDE = 256
"""Metrics are computed on a thumbnail: stable enough, and ~100x cheaper."""

NEAR_WHITE = 245
EDGE_THRESHOLD = 24


def measure(png_bytes: bytes) -> ImageMetrics:
    """Compute the appearance metrics of a stored PNG."""
    with Image.open(io.BytesIO(png_bytes)) as opened:
        sample = opened.convert("RGB")
    sample.thumbnail((SAMPLE_SIDE, SAMPLE_SIDE))
    pixels = sample.width * sample.height
    colours = sample.getcolors(maxcolors=1 << 24) or []
    grey = sample.convert("L")
    return ImageMetrics(
        n_colours=len(colours),
        dominant_colour_share=max((count for count, _ in colours), default=0) / pixels,
        near_white_share=sum(grey.point(lambda v: 255 if v >= NEAR_WHITE else 0).histogram()[255:])
        / pixels,
        edge_density=_edge_density(grey, pixels),
    )


def _edge_density(grey: Image.Image, pixels: int) -> float:
    edges = grey.filter(ImageFilter.FIND_EDGES)
    histogram = edges.histogram()
    return sum(histogram[EDGE_THRESHOLD:]) / pixels
