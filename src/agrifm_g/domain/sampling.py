"""Deterministic, seeded selection of document indices from a corpus."""

from __future__ import annotations

import random


def select_indices(*, total: int, size: int, seed: int) -> list[int]:
    """Pick `size` distinct indices in `[0, total)`, reproducibly for a given seed.

    The result is sorted, so downstream reads are sequential and diff-friendly.
    """
    if size <= 0:
        raise ValueError(f"size must be positive, got {size}")
    if size > total:
        raise ValueError(f"cannot sample {size} documents from a corpus of {total}")
    return sorted(random.Random(seed).sample(range(total), size))
