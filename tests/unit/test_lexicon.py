from pathlib import Path

from agrifm_g.adapters.lexicon import (
    DEFAULT_PATH,
    PHENOTYPE_PATH,
    load_lexicon,
    load_phenotype_lexicon,
)


def test_comments_and_blank_lines_are_ignored(tmp_path):
    path = tmp_path / "lexicon.txt"
    path.write_text("# a comment\n\nwheat\n  canopy  \n")
    assert load_lexicon(path) == {"wheat", "canopy"}


def test_the_committed_lexicon_loads_and_is_agricultural():
    terms = load_lexicon(DEFAULT_PATH)
    assert len(terms) > 100
    assert {"wheat", "canopy", "harvest", "irrigation"} <= terms
    assert all(term.islower() for term in terms)


def test_the_phenotype_lexicon_is_narrower_and_names_organs_not_context():
    phenotype = load_phenotype_lexicon(PHENOTYPE_PATH)
    assert {"canopy", "panicle", "chlorosis", "cultivar", "orchard"} <= phenotype
    assert all(term.islower() for term in phenotype)


def test_bare_crop_names_do_not_open_the_caption_gate():
    """A crop name says what a document is about, not what a picture shows.

    Every bare-crop-name match in the 30-shard build was a proper noun: `Apple` the company,
    `Orange` the town, `Oats Street`.
    """
    phenotype = load_phenotype_lexicon(PHENOTYPE_PATH)
    crops = load_lexicon(Path("data/crop_lexicon.txt"))

    assert {"apple", "orange", "oats", "wheat", "maize"} <= crops
    assert not (crops & phenotype)
    staples = {"wheat", "maize", "rice", "barley", "sorghum", "cassava", "apple", "oats"}
    assert staples <= load_lexicon(DEFAULT_PATH), "the pre-fetch text gate still keeps them"


def test_generic_context_terms_are_excluded_from_the_caption_gate():
    """These fire on charts and maps in economics, soil and ecology papers."""
    phenotype = load_phenotype_lexicon(PHENOTYPE_PATH)
    leaky = {"field", "plot", "plots", "trial", "trials", "soil", "yield", "farm", "variety"}
    assert not (leaky & phenotype)
    assert leaky <= load_lexicon(DEFAULT_PATH), "the recall-tuned text gate still keeps them"
