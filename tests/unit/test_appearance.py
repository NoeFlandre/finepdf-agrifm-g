import io

from hypothesis import given
from hypothesis import strategies as st
from PIL import Image, ImageDraw

from agrifm_g.adapters.appearance import measure
from agrifm_g.domain.appearance import (
    DOCUMENT_PAGE_ASPECT_TOLERANCE,
    MAX_DOMINANT_COLOUR_SHARE,
    MAX_LOW_INFORMATION_COLOURS,
    MAX_LOW_INFORMATION_EDGE_DENSITY,
    MAX_NEAR_WHITE_SHARE,
    MIN_DOCUMENT_PAGE_EDGE_DENSITY,
    MIN_DOCUMENT_PAGE_NEAR_WHITE_SHARE,
    MIN_LOW_INFORMATION_DOMINANT_SHARE,
    AppearanceRule,
    ImageMetrics,
    _has_positive_dimensions,
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


def test_antialiased_two_tone_placeholder_is_rejected():
    placeholder = ImageMetrics(
        n_colours=180,
        dominant_colour_share=0.04,
        near_white_share=0.08,
        edge_density=0.035,
        coarse_colour_bins=8,
        coarse_dominant_share=0.91,
    )
    assert rejection_rule(placeholder) is AppearanceRule.LOW_INFORMATION


def test_real_antialiased_placeholder_is_detected_from_coarse_histogram():
    image = Image.new("RGB", (1024, 1024), "white")
    ImageDraw.Draw(image).rounded_rectangle((8, 8, 1016, 952), radius=96, fill="black")
    image = image.resize((256, 256), Image.Resampling.LANCZOS)
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")

    measured = measure(buffer.getvalue())

    assert measured.n_colours > MAX_LOW_INFORMATION_COLOURS
    assert measured.coarse_colour_bins <= 16
    assert rejection_rule(measured) is AppearanceRule.LOW_INFORMATION


def test_low_information_boundaries_are_inclusive():
    boundary = metrics(
        n_colours=MAX_LOW_INFORMATION_COLOURS,
        dominant_colour_share=MIN_LOW_INFORMATION_DOMINANT_SHARE,
        edge_density=MAX_LOW_INFORMATION_EDGE_DENSITY,
    )
    assert rejection_rule(boundary) is AppearanceRule.LOW_INFORMATION


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


def test_page_scan_detector_rejects_invalid_geometry_without_dividing():
    scan = ImageMetrics(2_416, 0.5, 0.71, 0.26, True)
    assert not looks_like_document_page_scan(
        scan,
        image_width=0,
        image_height=2338,
        page_width=595,
        page_height=842,
        page_image_count=1,
    )


def test_page_scan_dimensions_must_all_be_positive():
    assert _has_positive_dimensions(1, 1, 1, 1)
    for dimensions in (
        (0, 1, 1, 1),
        (1, 0, 1, 1),
        (1, 1, 0, 1),
        (1, 1, 1, 0),
    ):
        assert not _has_positive_dimensions(*dimensions)


def test_page_scan_appearance_requires_all_inclusive_thresholds():
    page = {
        "image_width": 100,
        "image_height": 100,
        "page_width": 100,
        "page_height": 100,
        "page_image_count": 1,
    }
    too_few_edges = ImageMetrics(2_416, 0.5, MIN_DOCUMENT_PAGE_NEAR_WHITE_SHARE, 0.0, True)
    colour_page = ImageMetrics(2_416, 0.5, 0.9, 0.3, False)
    white_boundary = ImageMetrics(2_416, 0.5, MIN_DOCUMENT_PAGE_NEAR_WHITE_SHARE, 0.3, True)
    edge_boundary = ImageMetrics(2_416, 0.5, 0.9, MIN_DOCUMENT_PAGE_EDGE_DENSITY, True)

    assert not looks_like_document_page_scan(too_few_edges, **page)
    assert not looks_like_document_page_scan(colour_page, **page)
    assert looks_like_document_page_scan(white_boundary, **page)
    assert looks_like_document_page_scan(edge_boundary, **page)


def test_page_scan_rule_catches_a_dense_scan_just_below_the_old_edge_cutoff():
    scan = ImageMetrics(117, 0.08, 0.8, 0.17, True)
    assert looks_like_document_page_scan(
        scan,
        image_width=1654,
        image_height=2338,
        page_width=595,
        page_height=842,
        page_image_count=1,
    )


def test_page_scan_aspect_tolerance_boundary_is_inclusive():
    scan = ImageMetrics(2_416, 0.5, 0.71, 0.26, True)
    assert looks_like_document_page_scan(
        scan,
        image_width=97,
        image_height=100,
        page_width=100,
        page_height=100,
        page_image_count=1,
    )
    assert 1 - DOCUMENT_PAGE_ASPECT_TOLERANCE == 97 / 100
