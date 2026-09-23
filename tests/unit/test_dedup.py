from hypothesis import given
from hypothesis import strategies as st

from agrifm_g.domain.dedup import DropReason, deduplicate, keep_reason
from agrifm_g.domain.records import DocumentRecord, ImageRef


def image(
    path="images/d/000.png",
    sha="a" * 64,
    width=100,
    height=100,
    colours=30000,
    greyscale=False,
    document_page_scan=False,
    **extra,
):
    """A photographic image by default, so appearance rules do not fire unless asked."""
    fields: dict[str, float] = {
        "dominant_colour_share": 0.02,
        "near_white_share": 0.02,
        "edge_density": 0.25,
    }
    fields.update(extra)
    return ImageRef(
        path=path,
        page=0,
        width=width,
        height=height,
        format="png",
        sha256=sha,
        n_colours=colours,
        dominant_colour_share=fields["dominant_colour_share"],
        near_white_share=fields["near_white_share"],
        edge_density=fields["edge_density"],
        greyscale=greyscale,
        document_page_scan=document_page_scan,
    )


def record(doc_id="d1", images=()):
    return DocumentRecord(
        doc_id=doc_id,
        source_url="https://example.org/a.pdf",
        pdf_path=f"pdfs/{doc_id}.pdf",
        pdf_sha256="b" * 64,
        text="t",
        images=images,
    )


def test_a_single_colour_image_is_dropped():
    assert keep_reason(image(colours=1)) is DropReason.SINGLE_COLOUR


def test_an_extreme_aspect_ratio_is_dropped():
    assert keep_reason(image(width=2000, height=40)) is DropReason.ASPECT_RATIO


def test_a_normal_image_is_kept():
    assert keep_reason(image()) is None


def test_identical_images_are_kept_once_across_documents():
    shared = image(sha="c" * 64)
    kept, dropped = deduplicate([record("d1", (shared,)), record("d2", (shared,))])
    assert [len(r.images) for r in kept] == [1, 0]
    assert dropped[DropReason.DUPLICATE] == 1


def test_drop_reasons_are_counted_not_silent():
    images = (image(sha="1" * 64, colours=1), image(path="images/d/001.png", sha="2" * 64))
    kept, dropped = deduplicate([record("d1", images)])
    assert len(kept[0].images) == 1
    assert dropped[DropReason.SINGLE_COLOUR] == 1


@given(st.lists(st.integers(min_value=0, max_value=3), min_size=0, max_size=8))
def test_deduplication_is_idempotent_and_hashes_are_unique(shas):
    images = tuple(
        image(path=f"images/d/{i:03d}.png", sha=str(value) * 64) for i, value in enumerate(shas)
    )
    once, _ = deduplicate([record("d1", images)])
    twice, _ = deduplicate(once)
    assert once == twice
    seen = [i.sha256 for r in once for i in r.images]
    assert len(seen) == len(set(seen))


def test_the_aspect_ratio_boundary_is_exact():
    assert keep_reason(image(width=2000, height=100)) is None  # exactly 20:1 is kept
    assert keep_reason(image(width=2001, height=100)) is DropReason.ASPECT_RATIO
    assert keep_reason(image(width=100, height=2001)) is DropReason.ASPECT_RATIO


def test_two_colours_is_enough_to_survive_the_single_colour_rule():
    assert keep_reason(image(colours=2)) is None
    assert keep_reason(image(colours=0)) is DropReason.SINGLE_COLOUR


def test_a_low_colour_graphic_is_not_dropped_without_flatness_evidence():
    assert keep_reason(image(colours=500)) is None


def test_a_flat_colour_image_is_dropped_on_appearance():
    assert keep_reason(image(dominant_colour_share=0.99)) is DropReason.FLAT_BACKGROUND


def test_a_nearly_uniform_placeholder_is_dropped():
    placeholder = image(
        colours=50,
        dominant_colour_share=0.86453,
        near_white_share=0.05765,
        edge_density=0.06195,
        greyscale=True,
    )
    assert keep_reason(placeholder) is DropReason.LOW_INFORMATION


def test_a_document_page_scan_is_dropped():
    assert keep_reason(image(document_page_scan=True)) is DropReason.DOCUMENT_PAGE_SCAN


def test_a_blank_scan_is_dropped_on_appearance():
    assert keep_reason(image(near_white_share=0.99)) is DropReason.MOSTLY_BLANK


def test_a_zero_height_image_is_dropped_rather_than_dividing_by_zero():
    assert keep_reason(image(width=10, height=0)) is DropReason.ASPECT_RATIO


def test_repeated_drops_of_the_same_reason_accumulate():
    images = (
        image(path="images/d/000.png", sha="1" * 64, colours=1),
        image(path="images/d/001.png", sha="2" * 64, colours=1),
        image(path="images/d/002.png", sha="3" * 64, colours=1),
    )
    _, dropped = deduplicate([record("d1", images)])
    assert dropped[DropReason.SINGLE_COLOUR] == 3


def test_every_appearance_rule_has_a_matching_drop_reason():
    """`keep_reason` converts one enum into the other, so the two must stay in step."""
    from agrifm_g.domain.appearance import AppearanceRule

    assert {rule.value for rule in AppearanceRule} <= {reason.value for reason in DropReason}
