import pytest
from hypothesis import given
from hypothesis import strategies as st

from agrifm_g.domain.sampling import select_indices


def test_selection_is_deterministic_for_a_seed():
    assert select_indices(total=1000, size=10, seed=7) == select_indices(
        total=1000, size=10, seed=7
    )


def test_selection_honours_size():
    assert len(select_indices(total=1000, size=10, seed=7)) == 10


def test_selection_is_sorted_and_unique():
    indices = select_indices(total=1000, size=25, seed=1)
    assert indices == sorted(set(indices))


def test_a_different_seed_gives_a_different_sample():
    assert select_indices(total=1000, size=10, seed=1) != select_indices(
        total=1000, size=10, seed=2
    )


def test_size_larger_than_total_is_rejected():
    with pytest.raises(ValueError):
        select_indices(total=5, size=6, seed=1)


@pytest.mark.parametrize("size", [0, -1])
def test_non_positive_size_is_rejected(size):
    with pytest.raises(ValueError):
        select_indices(total=10, size=size, seed=1)


@given(
    total=st.integers(min_value=1, max_value=10_000),
    seed=st.integers(min_value=0, max_value=2**32 - 1),
    data=st.data(),
)
def test_indices_always_fall_inside_the_corpus(total, seed, data):
    size = data.draw(st.integers(min_value=1, max_value=total))
    indices = select_indices(total=total, size=size, seed=seed)
    assert len(indices) == size
    assert all(0 <= i < total for i in indices)
    assert indices == sorted(set(indices))
