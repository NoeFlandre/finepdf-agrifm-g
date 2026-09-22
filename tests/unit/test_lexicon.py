from pathlib import Path

import pytest

from agrifm_g.adapters.lexicon import (
    AGRICULTURE_PATH,
    CONVENTIONAL_PATH,
    SUSTAINABLE_PATH,
    load_lexicon,
)


@pytest.mark.parametrize(
    "path",
    (AGRICULTURE_PATH, CONVENTIONAL_PATH, SUSTAINABLE_PATH),
)
def test_committed_lexicons_are_extended_english_lists(path: Path):
    terms = load_lexicon(path)
    assert len(terms) >= 100
    assert all(term == term.lower() for term in terms)
    assert any(" " in term for term in terms)
    assert any(" " not in term for term in terms)


def test_broad_lexicon_covers_general_agriculture():
    terms = load_lexicon(AGRICULTURE_PATH)
    assert {"agriculture", "farm", "crop", "soil", "livestock", "harvest"} <= terms


def test_conventional_lexicon_covers_farm_operations():
    terms = load_lexicon(CONVENTIONAL_PATH)
    assert {
        "tractor",
        "combine harvester",
        "silo",
        "farm machinery",
        "chemical fertilizer",
        "industrial agriculture",
    } <= terms


def test_sustainable_lexicon_covers_requested_practices():
    terms = load_lexicon(SUSTAINABLE_PATH)
    assert {
        "permaculture",
        "hydroponics",
        "agroforestry",
        "agroecology",
        "food forest",
        "regenerative agriculture",
        "organic farming",
    } <= terms
