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
    assert "path: data/train-*.parquet" in card
    assert "license: cc-by-4.0" in card


def test_every_number_comes_from_the_build():
    card = a_card()
    assert "| rows (images) | 12 |" in card
    assert "| documents sampled | 10 |" in card
    assert "40%" in card
    assert "seed `42`" in card
    assert "samples 3 English FinePDF shards" in card


def test_the_caveat_is_stated_plainly():
    assert "not semantic agricultural filtering" in a_card()


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
