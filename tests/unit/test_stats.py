from agrifm_g.domain.dedup import DropReason
from agrifm_g.domain.records import DocumentRecord, ImageRef
from agrifm_g.domain.stats import build_stats


def image(width=100, height=200, sha="a" * 64, path="images/d/000.png"):
    return ImageRef(
        path=path,
        page=0,
        width=width,
        height=height,
        format="png",
        sha256=sha,
        n_colours=5,
        dominant_colour_share=0.02,
        near_white_share=0.02,
        edge_density=0.25,
    )


def record(doc_id="d1", images=(), text="hello"):
    return DocumentRecord(
        doc_id=doc_id,
        source_url="u",
        pdf_path="p",
        pdf_sha256="b" * 64,
        text=text,
        images=images,
    )


def test_the_yield_is_reported_against_what_was_sampled():
    stats = build_stats([record()], sampled=10, dropped={}, seed=1)
    assert stats["documents"]["sampled"] == 10
    assert stats["documents"]["built"] == 1
    assert stats["documents"]["fetch_yield"] == 0.1


def test_image_sizes_are_summarised():
    records = [
        record(
            images=(
                image(width=10, path="images/d/000.png"),
                image(width=200, path="images/d/001.png"),
                image(width=90, path="images/d/002.png"),
            )
        )
    ]
    images = build_stats(records, sampled=1, dropped={}, seed=1)["images"]
    assert images["width"] == {"min": 10, "median": 90, "max": 200, "mean": 100.0}
    assert images["height"] == {"min": 200, "median": 200, "max": 200, "mean": 200.0}


def test_drop_reasons_are_carried_through():
    stats = build_stats([record()], sampled=1, dropped={DropReason.DUPLICATE: 3}, seed=1)
    assert stats["images"]["dropped"]["duplicate"] == 3


def test_stats_are_deterministic():
    records = [record(images=(image(),))]
    assert build_stats(records, sampled=2, dropped={}, seed=7) == build_stats(
        records, sampled=2, dropped={}, seed=7
    )


def test_an_empty_build_does_not_divide_by_zero():
    stats = build_stats([], sampled=0, dropped={}, seed=1)
    assert stats["documents"]["fetch_yield"] == 0.0
    assert stats["images"]["total"] == 0


def test_a_summary_reports_min_median_max_and_mean():
    from agrifm_g.domain.stats import _summarise

    assert _summarise([1, 2, 6]) == {"min": 1, "median": 2, "max": 6, "mean": 3.0}
    assert _summarise([]) == {"min": 0, "median": 0, "max": 0, "mean": 0.0}


def test_megapixels_and_totals_are_exact():
    images = (image(width=1000, height=1000), image(width=500, height=1000, sha="c" * 64))
    images = (
        images[0],
        ImageRef(
            path="images/d/001.png",
            page=1,
            width=500,
            height=1000,
            format="png",
            sha256="c" * 64,
            n_colours=5,
            dominant_colour_share=0.02,
            near_white_share=0.02,
            edge_density=0.25,
        ),
    )
    stats = build_stats([record(images=images)], sampled=1, dropped={}, seed=1)
    assert stats["images"]["megapixels"] == 1.5
    assert stats["images"]["total"] == 2
    assert stats["documents"]["images_per_document"]["max"] == 2


def test_a_document_without_images_is_not_counted_as_having_them():
    stats = build_stats([record(), record("d2", (image(),))], sampled=2, dropped={}, seed=1)
    assert stats["documents"]["with_images"] == 1
    assert stats["documents"]["built"] == 2
