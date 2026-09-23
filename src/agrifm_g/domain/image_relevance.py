"""Conservative, model-independent decisions for image-level agriculture relevance."""

from __future__ import annotations

import math
from dataclasses import dataclass

MAX_AGRICULTURE_PHOTO_PROBABILITY = 0.12
MIN_NEGATIVE_CLASS_PROBABILITY = 0.66


@dataclass(frozen=True, slots=True)
class ImageRelevanceScores:
    """Three-way CLIP preference across agriculture photos and common noise types."""

    agriculture_photo: float
    document_figure: float
    unrelated_photo: float

    def __post_init__(self) -> None:
        values = (self.agriculture_photo, self.document_figure, self.unrelated_photo)
        if any(not math.isfinite(value) or not 0 <= value <= 1 for value in values):
            raise ValueError("visual relevance scores must be finite probabilities")
        if not math.isclose(sum(values), 1.0, abs_tol=1e-4):
            raise ValueError("visual relevance probabilities must sum to one")


def is_clear_non_agricultural(scores: ImageRelevanceScores) -> bool:
    """Drop only when the model strongly prefers a negative class over farm photography."""
    strongest_negative = max(scores.document_figure, scores.unrelated_photo)
    return (
        scores.agriculture_photo <= MAX_AGRICULTURE_PHOTO_PROBABILITY
        and strongest_negative >= MIN_NEGATIVE_CLASS_PROBABILITY
    )
