from agrifm_g.domain.agriculture import AgricultureSplit, classify_document
from agrifm_g.domain.textgate import lexicon_hits


def test_phrase_terms_match_as_whole_phrases():
    assert lexicon_hits("A combine harvester crossed the field", {"combine harvester"}) == 1
    assert lexicon_hits("a harvester", {"combine harvester"}) == 0


def test_category_classifier_returns_only_the_stronger_category():
    assert classify_document(
        "tractor combine harvester silo",
        conventional_terms={"tractor", "combine harvester", "silo"},
        sustainable_terms={"permaculture"},
    ) is AgricultureSplit.CONVENTIONAL


def test_category_classifier_discards_ties_and_missing_evidence():
    assert classify_document(
        "tractor permaculture", {"tractor"}, {"permaculture"}
    ) is None
    assert classify_document("farm report", {"tractor"}, {"permaculture"}) is None


def test_category_matching_is_case_insensitive_and_whole_word():
    assert classify_document(
        "ORGANIC FARMING", {"tractor"}, {"organic farming"}
    ) is AgricultureSplit.SUSTAINABLE
    assert classify_document("organic farmer", {"tractor"}, {"organic farming"}) is None
