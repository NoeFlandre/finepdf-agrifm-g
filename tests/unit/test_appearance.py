from hypothesis import given
from hypothesis import strategies as st

from agrifm_g.domain.appearance import (
    MAX_DOMINANT_COLOUR_SHARE,
    MAX_NEAR_WHITE_SHARE,
    AppearanceRule,
    ImageMetrics,
    looks_like_document_page_scan,
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


def test_a_normal_colourful_image_survives():
    assert rejection_rule(metrics()) is None


def test_single_colour_images_are_rejected():
    assert rejection_rule(metrics(n_colours=1)) is AppearanceRule.FEW_COLOURS


def test_nearly_blank_images_are_rejected():
    assert rejection_rule(metrics(near_white_share=0.99)) is AppearanceRule.MOSTLY_BLANK
    assert rejection_rule(metrics(near_white_share=MAX_NEAR_WHITE_SHARE)) is None


def test_flat_colour_images_are_rejected():
    assert rejection_rule(metrics(dominant_colour_share=0.99)) is AppearanceRule.FLAT_BACKGROUND
    assert rejection_rule(metrics(dominant_colour_share=MAX_DOMINANT_COLOUR_SHARE)) is None


def test_nearly_uniform_black_placeholder_is_rejected():
    placeholder = metrics(
        n_colours=50,
        dominant_colour_share=0.86453,
        near_white_share=0.05765,
        edge_density=0.06195,
    )
    assert rejection_rule(placeholder) is AppearanceRule.LOW_INFORMATION


def test_low_texture_images_are_not_rejected():
    assert rejection_rule(metrics(n_colours=2, edge_density=0.0)) is None
    assert rejection_rule(metrics(n_colours=30000, edge_density=0.0)) is None
    assert rejection_rule(metrics(n_colours=4, dominant_colour_share=0.8, edge_density=0.2)) is None


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


def test_greyscale_images_use_the_same_obvious_degenerate_rules():
    grey = ImageMetrics(
        n_colours=256,
        dominant_colour_share=0.1,
        near_white_share=0.1,
        edge_density=0.0,
        greyscale=True,
    )
    assert rejection_rule(grey) is None
    blank = ImageMetrics(256, 0.1, 0.99, 0.0, True)
    assert rejection_rule(blank) is AppearanceRule.MOSTLY_BLANK


def test_page_sized_grayscale_document_scan_is_detected():
    scan = ImageMetrics(2_416, 0.49961, 0.71148, 0.26334, True)
    assert looks_like_document_page_scan(
        scan,
        image_width=1654,
        image_height=2338,
        page_width=595,
        page_height=842,
        page_image_count=1,
    )


def test_page_scan_detector_preserves_photos_and_non_page_figures():
    photo = ImageMetrics(20_000, 0.04, 0.15, 0.12, False)
    assert not looks_like_document_page_scan(
        photo,
        image_width=1654,
        image_height=2338,
        page_width=595,
        page_height=842,
        page_image_count=1,
    )
    scan = ImageMetrics(2_416, 0.5, 0.71, 0.26, True)
    assert not looks_like_document_page_scan(
        scan,
        image_width=500,
        image_height=300,
        page_width=595,
        page_height=842,
        page_image_count=1,
    )
    assert not looks_like_document_page_scan(
        scan,
        image_width=1654,
        image_height=2338,
        page_width=595,
        page_height=842,
        page_image_count=2,
    )
