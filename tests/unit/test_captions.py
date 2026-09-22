from agrifm_g.domain.captions import captions_for_images, extract_caption_blocks


def test_extract_caption_blocks_keeps_only_explicit_figure_labels():
    text = """
    The results are shown in Figure 2 in the discussion.
    Figure 1. Wheat canopy under drought stress.
    This continuation names the leaf treatment.

    The next paragraph is not a caption.
    """

    assert extract_caption_blocks(text) == (
        "Figure 1. Wheat canopy under drought stress. This continuation names the leaf treatment.",
    )


def test_caption_blocks_accept_fig_plate_and_image_labels():
    text = "Fig. 1: Maize leaf disease\nPlate 2 - harvested grain\nImage 3 Tomato plants"

    assert extract_caption_blocks(text) == (
        "Fig. 1: Maize leaf disease",
        "Plate 2 - harvested grain",
        "Image 3 Tomato plants",
    )


def test_captions_are_assigned_in_page_order():
    captions = ("Figure 1 text", "Figure 2 text")

    assert captions_for_images(captions, 2) == captions
    assert captions_for_images(("Figure 1 text",), 2) == (
        "Figure 1 text",
        "Figure 1 text",
    )
    assert captions_for_images(captions, 3) == ("Figure 1 text", "Figure 2 text", "")


def test_caption_blocks_accept_photograph_and_non_english_labels():
    text = (
        "Photo 4. Rust lesions on the flag leaf\n"
        "Abb. 2: Weizen im Feld\n"
        "Figura 5. Hojas de maiz\n"
        "Pl. 3 Seedlings at emergence"
    )

    assert extract_caption_blocks(text) == (
        "Photo 4. Rust lesions on the flag leaf",
        "Abb. 2: Weizen im Feld",
        "Figura 5. Hojas de maiz",
        "Pl. 3 Seedlings at emergence",
    )


def test_unnumbered_caption_needs_a_separator_so_prose_cannot_open_one():
    assert extract_caption_blocks("Photograph: a wheat field at harvest") == (
        "Photograph: a wheat field at harvest",
    )
    assert extract_caption_blocks("Figure \u2014 cassava roots") == ("Figure \u2014 cassava roots",)
    for prose in (
        "Figures were prepared in R",
        "Images of the crop were taken weekly",
        "Figure out which cultivar yielded most",
    ):
        assert extract_caption_blocks(prose) == ()
