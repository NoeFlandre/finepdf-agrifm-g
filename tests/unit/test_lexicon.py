from agrifm_g.adapters.lexicon import DEFAULT_PATH, load_lexicon


def test_comments_and_blank_lines_are_ignored(tmp_path):
    path = tmp_path / "lexicon.txt"
    path.write_text("# a comment\n\nwheat\n  canopy  \n")
    assert load_lexicon(path) == {"wheat", "canopy"}


def test_the_committed_lexicon_loads_and_is_agricultural():
    terms = load_lexicon(DEFAULT_PATH)
    assert len(terms) > 100
    assert {"wheat", "canopy", "harvest", "irrigation"} <= terms
    assert all(term.islower() for term in terms)
