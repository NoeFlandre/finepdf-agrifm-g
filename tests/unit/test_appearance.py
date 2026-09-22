from hypothesis import given
from hypothesis import strategies as st

from agrifm_g.domain.appearance import (
    GREYSCALE_MIN_EDGE_DENSITY,
    MAX_DOMINANT_COLOUR_SHARE,
    MAX_NEAR_WHITE_SHARE,
    MIN_COLOURS,
    AppearanceRule,
    ImageMetrics,
    rejection_rule,
)


def metrics(
    n_colours: int = 30000,
    dominant_colour_share: float = 0.2,
    near_white_share: float = 0.1,
    edge_density: float = 0.25,
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
    assert rejection_rule(metrics(n_colours=20000, edge_density=0.01)) is AppearanceRule.LOW_TEXTURE


def test_thresholds_are_boundaries_not_ranges():
    assert rejection_rule(metrics(n_colours=8000)) is AppearanceRule.FEW_COLOURS
    assert rejection_rule(metrics(n_colours=8001, edge_density=0.18)) is None
    assert rejection_rule(metrics(n_colours=8001, edge_density=0.179)) is AppearanceRule.LOW_TEXTURE
    assert rejection_rule(metrics(near_white_share=0.80)) is None
    assert rejection_rule(metrics(near_white_share=0.801)) is AppearanceRule.MOSTLY_BLANK


def test_every_threshold_is_exact():
    assert rejection_rule(metrics(dominant_colour_share=0.55)) is None
    assert rejection_rule(metrics(dominant_colour_share=0.551)) is AppearanceRule.FLAT_BACKGROUND
    assert rejection_rule(metrics(n_colours=16384, edge_density=0.18)) is None
    assert (
        rejection_rule(metrics(n_colours=16384, edge_density=0.179)) is AppearanceRule.LOW_TEXTURE
    )
    assert rejection_rule(metrics(n_colours=16384, edge_density=0.079)) is AppearanceRule.LINE_ART
    assert (
        rejection_rule(metrics(n_colours=16385, edge_density=0.079)) is AppearanceRule.LOW_TEXTURE
    )


def test_line_art_needs_both_a_small_palette_and_few_edges():
    """Either condition alone must not reject: a colourful photograph can be edgeless."""
    assert rejection_rule(metrics(n_colours=30000, edge_density=0.18)) is None
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


def a_greyscale(edge_density, *, n_colours=256, near_white=0.1, dominant=0.1):
    return ImageMetrics(
        n_colours=n_colours,
        dominant_colour_share=dominant,
        near_white_share=near_white,
        edge_density=edge_density,
        greyscale=True,
    )


def test_a_greyscale_photograph_is_not_rejected_for_its_colour_count():
    """8-bit greyscale tops out at 256 colours, so MIN_COLOURS would reject every photo."""
    photograph = a_greyscale(0.34)

    assert photograph.n_colours <= MIN_COLOURS
    assert rejection_rule(photograph) is None


def test_a_flat_greyscale_chart_is_rejected_on_texture():
    assert rejection_rule(a_greyscale(0.18)) is AppearanceRule.FLAT_GREYSCALE
    assert rejection_rule(a_greyscale(GREYSCALE_MIN_EDGE_DENSITY)) is None


def test_greyscale_images_still_face_the_blank_and_flat_background_rules():
    assert rejection_rule(a_greyscale(0.34, near_white=0.95)) is AppearanceRule.MOSTLY_BLANK
    assert rejection_rule(a_greyscale(0.34, dominant=0.9)) is AppearanceRule.FLAT_BACKGROUND


def test_a_colourful_image_is_unaffected_by_the_greyscale_branch():
    colourful = ImageMetrics(
        n_colours=200, dominant_colour_share=0.1, near_white_share=0.1, edge_density=0.34
    )

    assert rejection_rule(colourful) is AppearanceRule.FEW_COLOURS


def test_a_greyscale_scan_is_detected_through_its_colour_histogram():
    from agrifm_g.adapters.appearance import _is_greyscale

    grey_pixels = [(90, (10, 12, 11)), (10, (200, 203, 201))]
    assert _is_greyscale(grey_pixels, 100)
    assert not _is_greyscale([(90, (10, 200, 11)), (10, (5, 5, 5))], 100)
    assert _is_greyscale([(100, 128)], 100), "a single-band palette is neutral by definition"


def test_the_greyscale_blankness_boundaries_are_inclusive_keeps():
    """Exactly at a threshold the image is kept; only strictly beyond it is rejected."""
    assert rejection_rule(a_greyscale(0.34, near_white=MAX_NEAR_WHITE_SHARE)) is None
    assert rejection_rule(a_greyscale(0.34, dominant=MAX_DOMINANT_COLOUR_SHARE)) is None
