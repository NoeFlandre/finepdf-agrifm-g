import pytest

from agrifm_g.domain.image_relevance import (
    ImageRelevanceScores,
    is_clear_non_agricultural,
)


def test_a_confident_document_figure_is_rejected():
    scores = ImageRelevanceScores(
        agriculture_photo=0.04,
        document_figure=0.83,
        unrelated_photo=0.13,
    )
    assert is_clear_non_agricultural(scores)


def test_a_confident_unrelated_photo_is_rejected():
    scores = ImageRelevanceScores(
        agriculture_photo=0.06,
        document_figure=0.12,
        unrelated_photo=0.82,
    )
    assert is_clear_non_agricultural(scores)


@pytest.mark.parametrize(
    "scores",
    [
        ImageRelevanceScores(0.55, 0.35, 0.10),
        ImageRelevanceScores(0.18, 0.70, 0.12),
        ImageRelevanceScores(0.08, 0.60, 0.32),
    ],
)
def test_agricultural_and_uncertain_images_are_kept(scores):
    assert not is_clear_non_agricultural(scores)


@pytest.mark.parametrize(
    "values",
    [
        (-0.01, 0.50, 0.51),
        (0.25, 0.75, 0.01),
        (float("nan"), 0.5, 0.5),
    ],
)
def test_scores_must_be_finite_probabilities(values):
    with pytest.raises(ValueError, match="probabilities"):
        ImageRelevanceScores(*values)
