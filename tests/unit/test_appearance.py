from hypothesis import given
from hypothesis import strategies as st

from agrifm_g.domain.appearance import (
    AppearanceRule,
    ImageMetrics,
    rejection_rule,
)


def metrics(
    n_colours: int = 30000,
    dominant_colour_share: float = 0.2,
    near_white_share: float = 0.1,
    edge_density: float = 0.15,
) -> ImageMetrics:
    return ImageMetrics(
        n_colours=n_colours,
        dominant_colour_share=dominant_colour_share,
        near_white_share=near_white_share,
        edge_density=edge_density,
    )


def test_a_photograph_survives():
    assert rejection_rule(metrics()) is None


def test_a_flat_graphic_is_rejected():
    assert rejection_rule(metrics(n_colours=12)) is AppearanceRule.FEW_COLOURS
    assert rejection_rule(metrics(n_colours=2000)) is AppearanceRule.FEW_COLOURS


def test_a_mostly_blank_scan_is_rejected():
    assert rejection_rule(metrics(near_white_share=0.97)) is AppearanceRule.MOSTLY_BLANK
    assert rejection_rule(metrics(near_white_share=0.85)) is AppearanceRule.MOSTLY_BLANK


def test_an_image_dominated_by_one_colour_is_rejected():
    assert rejection_rule(metrics(dominant_colour_share=0.9)) is AppearanceRule.FLAT_BACKGROUND
    assert rejection_rule(metrics(dominant_colour_share=0.6)) is AppearanceRule.FLAT_BACKGROUND


def test_line_art_is_rejected_when_it_is_flat_and_sparse():
    assert rejection_rule(metrics(n_colours=9000, edge_density=0.01)) is AppearanceRule.LINE_ART


def test_a_photograph_with_few_edges_is_kept_when_it_is_colourful():
    assert rejection_rule(metrics(n_colours=20000, edge_density=0.01)) is None


def test_thresholds_are_boundaries_not_ranges():
    assert rejection_rule(metrics(n_colours=4096)) is AppearanceRule.FEW_COLOURS
    assert rejection_rule(metrics(n_colours=4097)) is None
    assert rejection_rule(metrics(near_white_share=0.80)) is None
    assert rejection_rule(metrics(near_white_share=0.801)) is AppearanceRule.MOSTLY_BLANK


def test_every_threshold_is_exact():
    assert rejection_rule(metrics(dominant_colour_share=0.55)) is None
    assert rejection_rule(metrics(dominant_colour_share=0.551)) is AppearanceRule.FLAT_BACKGROUND
    assert rejection_rule(metrics(n_colours=16384, edge_density=0.08)) is None
    assert rejection_rule(metrics(n_colours=16384, edge_density=0.079)) is AppearanceRule.LINE_ART
    assert rejection_rule(metrics(n_colours=16385, edge_density=0.079)) is None


def test_line_art_needs_both_a_small_palette_and_few_edges():
    """Either condition alone must not reject: a colourful photograph can be edgeless."""
    assert rejection_rule(metrics(n_colours=30000, edge_density=0.001)) is None
    assert rejection_rule(metrics(n_colours=9000, edge_density=0.5)) is None


def test_the_weakest_labelled_keep_still_survives():
    """The margins exist because the label set holds only ten positives."""
    weakest = ImageMetrics(
        n_colours=12483,
        dominant_colour_share=0.05,
        near_white_share=0.10,
        edge_density=0.22,
    )
    assert rejection_rule(weakest) is None


@given(
    n_colours=st.integers(min_value=0, max_value=100_000),
    dominant=st.floats(min_value=0, max_value=1),
    white=st.floats(min_value=0, max_value=1),
    edges=st.floats(min_value=0, max_value=1),
)
def test_the_rule_is_total_and_stable(n_colours, dominant, white, edges):
    sample = metrics(
        n_colours=n_colours,
        dominant_colour_share=dominant,
        near_white_share=white,
        edge_density=edges,
    )
    first = rejection_rule(sample)
    assert first is rejection_rule(sample)
    assert first is None or isinstance(first, AppearanceRule)
