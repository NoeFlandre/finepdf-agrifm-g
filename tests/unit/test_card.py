from pathlib import Path

from agrifm_g.domain.card import render_card
from agrifm_g.domain.stats import build_stats


def a_card(**kwargs):
    stats = build_stats([], sampled=10, dropped={}, seed=42, source_shards=3)
    stats["documents"]["built"] = 4
    stats["documents"]["fetch_yield"] = 0.4
    return render_card(repo_id="me/thing", stats=stats, n_rows=12, n_shards=1, **kwargs)


def test_the_front_matter_declares_the_parquet_config():
    card = a_card()
    assert card.startswith("---\n")
    assert "path: data/conventional-*.parquet" in card
    assert "path: data/sustainable-*.parquet" in card
    assert "path: data/train-*.parquet" not in card
    assert "license: cc-by-4.0" in card


def test_every_number_comes_from_the_build():
    card = a_card()
    assert "| rows (images) | 12 |" in card
    assert "| documents sampled | 10 |" in card
    assert "40%" in card
    assert "seed `42`" in card
    assert "sampled 3 English FinePDF shards" in card


def test_the_caveat_is_stated_plainly():
    assert "captions are optional metadata and never a filter" in a_card()


def test_the_card_prominently_marks_this_as_a_prototype():
    card = a_card()
    assert "pretty_name: FinePDF Agriculture Images (Prototype)" in card
    assert "  - prototype\n" in card
    assert "  - work-in-progress\n" in card
    assert "Work in progress — prototype only, not a final dataset." in card
    assert "Its contents, labels, splits, and filters are provisional and may change." in card


def test_the_schema_table_lists_every_published_column():
    from agrifm_g.domain.rows import COLUMNS

    card = a_card()
    assert all(f"`{column}`" in card for column in COLUMNS)


GOLDEN_CARD = Path(__file__).parents[1] / "fixtures" / "golden_card.md"


def test_the_rendered_card_matches_the_golden_copy():
    """Prose is part of the deliverable: a wording change must be deliberate."""
    if not GOLDEN_CARD.exists():  # pragma: no cover - only on first generation
        GOLDEN_CARD.write_text(a_card(), encoding="utf-8")
    assert a_card() == GOLDEN_CARD.read_text(encoding="utf-8")


def test_the_size_category_follows_the_row_count():
    stats = build_stats([], sampled=1, dropped={}, seed=1)
    assert "n<1K" in render_card(repo_id="r", stats=stats, n_rows=999, n_shards=1)
    assert "1K<n<10K" in render_card(repo_id="r", stats=stats, n_rows=1000, n_shards=1)
    assert "10K<n<100K" in render_card(repo_id="r", stats=stats, n_rows=10_000, n_shards=1)
    assert "100K<n<1M" in render_card(repo_id="r", stats=stats, n_rows=100_000, n_shards=1)


def test_the_card_states_when_no_visual_filter_was_applied():
    card = a_card()
    assert "- This packaging run did not apply an image-level semantic filter.\n" in card
    assert "zero-shot CLIP" not in card


def test_the_card_describes_the_visual_filter_exactly():
    stats = build_stats(
        [],
        sampled=10,
        dropped={},
        seed=42,
        source_shards=3,
        visual_filter={
            "model_id": "org/clip",
            "model_revision": "abc123",
            "prompt_version": "p-v9",
            "max_agriculture_probability_to_drop": 0.05,
            "min_negative_probability_to_drop": 0.8,
        },
    )
    card = render_card(repo_id="me/thing", stats=stats, n_rows=12, n_shards=1)

    assert "did not apply" not in card
    assert (
        "- A pinned, zero-shot CLIP screen compares agricultural photos with document figures"
        " and unrelated photos. It does not read captions or document text.\n"
    ) in card
    assert "- Model: `org/clip` at revision `abc123`; prompt set `p-v9`.\n" in card
    assert (
        "- Only high-confidence negatives are removed: agricultural-photo score at or below"
        " 0.05 and a negative-class score at or above 0.80. Borderline"
        " predictions stay in the dataset to preserve diversity.\n"
    ) in card


def test_the_size_category_changes_exactly_at_each_ceiling():
    from agrifm_g.domain.card import _size_category

    assert _size_category(0) == "n<1K"
    assert _size_category(999) == "n<1K"
    assert _size_category(1_000) == "1K<n<10K"
    assert _size_category(9_999) == "1K<n<10K"
    assert _size_category(10_000) == "10K<n<100K"
    assert _size_category(99_999) == "10K<n<100K"
    assert _size_category(100_000) == "100K<n<1M"
