from hypothesis import given
from hypothesis import strategies as st

from agrifm_g.domain.normalisation import MIN_IMAGE_SIDE, is_usable_image, safe_doc_id


def test_degenerate_images_are_dropped():
    assert not is_usable_image(width=8, height=800, n_bytes=5000)
    assert not is_usable_image(width=800, height=800, n_bytes=0)


def test_normal_images_are_kept():
    assert is_usable_image(width=MIN_IMAGE_SIDE, height=MIN_IMAGE_SIDE, n_bytes=1)


def test_doc_id_is_made_filesystem_safe():
    assert safe_doc_id("<urn:uuid:becf8a10-92d9>") == "urn_uuid_becf8a10-92d9"


@given(st.text(min_size=1))
def test_safe_doc_id_is_idempotent_and_safe(raw):
    once = safe_doc_id(raw)
    assert once == safe_doc_id(once)
    assert once
    assert set(once) <= set("abcdefghijklmnopqrstuvwxyz0123456789-_")
    assert once not in {".", ".."}
