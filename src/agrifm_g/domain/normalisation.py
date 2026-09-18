"""Minimal, idempotent normalisation rules shared by the whole pipeline."""

from __future__ import annotations

MIN_IMAGE_SIDE = 32
"""Images thinner than this on either side are decorations, rules or artefacts."""

_ALLOWED = frozenset("abcdefghijklmnopqrstuvwxyz0123456789-_")


def is_usable_image(*, width: int, height: int, n_bytes: int) -> bool:
    """Reject empty and degenerate images; everything else is kept at this stage."""
    return n_bytes > 0 and width >= MIN_IMAGE_SIDE and height >= MIN_IMAGE_SIDE


def safe_doc_id(raw: str) -> str:
    """Map an arbitrary document id onto a stable, filesystem-safe slug."""
    lowered = (character.lower() for character in raw)
    squashed = "".join(character if character in _ALLOWED else "_" for character in lowered)
    trimmed = squashed.strip("_")
    return trimmed or "doc"
