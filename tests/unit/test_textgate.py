from hypothesis import given
from hypothesis import strategies as st

from agrifm_g.domain.textgate import (
    DEFAULT_THRESHOLD,
    agronomy_score,
    contains_lexicon_word,
    passes_gate,
)

TERMS = frozenset({"wheat", "canopy", "harvest", "leaf"})


def test_a_document_full_of_agronomy_scores_high():
    assert agronomy_score("wheat canopy harvest leaf", TERMS) == 1.0


def test_a_document_with_none_scores_zero():
    assert agronomy_score("the quick brown fox", TERMS) == 0.0


def test_the_score_is_a_share_not_a_count():
    assert agronomy_score("wheat and rain", TERMS) == 1 / 3


def test_matching_ignores_case_and_punctuation():
    assert agronomy_score("Wheat, canopy! (harvest) leaf.", TERMS) == 1.0


def test_matching_is_whole_word():
    assert agronomy_score("wheatgrass leafy", TERMS) == 0.0


def test_caption_matching_is_whole_word():
    assert contains_lexicon_word("Figure 1. Wheat canopy", TERMS)
    assert not contains_lexicon_word("Figure 1. wheaten material", TERMS)
    assert not contains_lexicon_word("Figure 1. unrelated image", TERMS)


def test_an_empty_document_scores_zero():
    assert agronomy_score("", TERMS) == 0.0
    assert agronomy_score("12345 ...", TERMS) == 0.0


def test_the_gate_is_a_threshold():
    assert passes_gate(0.02, threshold=0.01)
    assert passes_gate(0.01, threshold=0.01)
    assert not passes_gate(0.009, threshold=0.01)


def test_the_default_threshold_is_the_validated_conservative_bump():
    assert DEFAULT_THRESHOLD == 0.005


@given(st.text(max_size=300), st.integers(min_value=1, max_value=20))
def test_the_score_is_length_invariant_under_repetition(text, repeats):
    once = agronomy_score(text, TERMS)
    many = agronomy_score(" ".join([text] * repeats), TERMS)
    assert abs(once - many) < 1e-9


@given(st.text(max_size=300))
def test_the_score_is_always_a_share(text):
    assert 0.0 <= agronomy_score(text, TERMS) <= 1.0
