"""Deterministic document-level agriculture split classification."""

from __future__ import annotations

from collections.abc import Collection
from enum import StrEnum

from agrifm_g.domain.textgate import lexicon_hits


class AgricultureSplit(StrEnum):
    """The mutually exclusive agriculture categories published by the dataset."""

    CONVENTIONAL = "conventional"
    SUSTAINABLE = "sustainable"


def classify_document(
    text: str,
    conventional_terms: Collection[str],
    sustainable_terms: Collection[str],
) -> AgricultureSplit | None:
    """Return the stronger category, dropping ties and documents without evidence."""
    conventional_hits = lexicon_hits(text, conventional_terms)
    sustainable_hits = lexicon_hits(text, sustainable_terms)
    if conventional_hits == sustainable_hits:
        return None
    return (
        AgricultureSplit.CONVENTIONAL
        if conventional_hits > sustainable_hits
        else AgricultureSplit.SUSTAINABLE
    )
