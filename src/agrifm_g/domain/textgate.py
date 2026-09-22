"""Score a document's text before its PDF is ever fetched.

The cheapest filter in the pipeline: it costs nothing but a regex over text FinePDF has
already extracted, and a document it rejects is never downloaded. It is tuned for **recall**,
because a document rejected here is never seen again.
"""

from __future__ import annotations

import re
from collections import defaultdict
from collections.abc import Collection

WORD = re.compile(r"[a-z0-9]+")

DEFAULT_THRESHOLD = 0.005
"""A low recall-first threshold for the broad agriculture vocabulary."""


def agronomy_score(text: str, terms: Collection[str]) -> float:
    """Share of a document's words that are agronomy terms; 0.0 for an empty document.

    A share rather than a count, so a long irrelevant document cannot out-score a short
    relevant one.
    """
    words = WORD.findall(text.lower())
    if not words:
        return 0.0
    return lexicon_hits(text, terms) / len(words)


def lexicon_hits(text: str, terms: Collection[str]) -> int:
    """Count exact one- and multi-word lexicon matches in normalized text."""
    tokens = WORD.findall(text.lower())
    by_length: dict[int, set[tuple[str, ...]]] = defaultdict(set)
    for term in terms:
        normalized = tuple(WORD.findall(term.lower()))
        if normalized:
            by_length[len(normalized)].add(normalized)
    return sum(
        1
        for start in range(len(tokens))
        for length, phrases in by_length.items()
        if start + length <= len(tokens) and tuple(tokens[start : start + length]) in phrases
    )


def contains_lexicon_word(text: str, terms: Collection[str]) -> bool:
    """Whether text contains at least one whole word or phrase from the lexicon."""
    return lexicon_hits(text, terms) > 0


def passes_gate(score: float, *, threshold: float = DEFAULT_THRESHOLD) -> bool:
    """Whether a document is worth fetching."""
    return score >= threshold
