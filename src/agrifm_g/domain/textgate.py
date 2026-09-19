"""Score a document's text before its PDF is ever fetched.

The cheapest filter in the pipeline: it costs nothing but a regex over text FinePDF has
already extracted, and a document it rejects is never downloaded. It is tuned for **recall**,
because a document rejected here is never seen again.
"""

from __future__ import annotations

import re
from collections.abc import Collection

WORD = re.compile(r"[a-z]+")

DEFAULT_THRESHOLD = 0.003
"""Fitted on 83 labelled documents by `scripts/fit_text_gate.py`.

At this value the gate skips 48 % of fetches and keeps every labelled positive. The lowest
scoring document holding a keep sits at 0.0062, so the threshold carries a 2x margin; 0.005
would save 53 % of fetches but leaves only 1.2x, which is not worth it when a miss is
permanent.
"""


def agronomy_score(text: str, terms: Collection[str]) -> float:
    """Share of a document's words that are agronomy terms; 0.0 for an empty document.

    A share rather than a count, so a long irrelevant document cannot out-score a short
    relevant one.
    """
    words = WORD.findall(text.lower())
    if not words:
        return 0.0
    return sum(1 for word in words if word in terms) / len(words)


def passes_gate(score: float, *, threshold: float = DEFAULT_THRESHOLD) -> bool:
    """Whether a document is worth fetching."""
    return score >= threshold
