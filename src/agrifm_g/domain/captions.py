"""Recognise explicit figure-caption blocks in extracted PDF text."""

from __future__ import annotations

import re
from collections.abc import Sequence

_LABEL = (
    r"(?:figures?|figs?\.?|figuras?|abb\.?|"
    r"photographs?|photos?\.?|plates?|pl\.|images?)"
)
"""The words a caption may open with.

English first, then the two abbreviations that dominate the non-English scientific PDFs in
the corpus (`Figura`, `Abb.`). `Photo`/`Photograph` matter disproportionately here: a
photograph is exactly the kind of image this dataset wants, and it is rarely labelled `Figure`.
"""

_IDENTIFIER = r"[A-Za-z]?\d+(?:[-./]\d+)*(?:[A-Za-z])?"

_CAPTION_START = re.compile(
    rf"^\s*{_LABEL}"
    rf"(?:\s+{_IDENTIFIER}\s*(?:(?:[:.)-])\s*|\s+)"
    rf"|\s*[:\u2013\u2014-]\s+)"
    r"(?P<body>\S.*)$",
    re.IGNORECASE,
)
"""A label plus either a figure number, or — for a page's only figure — a bare separator.

The unnumbered form demands a colon or a dash so that prose such as "Figures were prepared
in R" cannot open a caption; a bare label followed by a space is not enough.
"""
_MAX_CAPTION_LINES = 4


def extract_caption_blocks(text: str) -> tuple[str, ...]:
    """Return only explicitly labelled caption blocks, including short continuations."""
    captions: list[str] = []
    current: list[str] = []
    for raw_line in text.splitlines():
        current = _consume_line(raw_line, captions, current)
    _append_caption(captions, current)
    return tuple(captions)


def captions_for_images(captions: Sequence[str], n_images: int) -> tuple[str, ...]:
    """Assign page captions to page images in reading order.

    A single caption can describe a multi-panel image, so it is shared across the page's
    images. When counts differ, unmatched images receive no caption rather than nearby prose.
    """
    count = max(n_images, 0)
    if count == 0:
        return ()
    if not captions:
        return ("",) * count
    if len(captions) == 1:
        return (captions[0],) * count
    return tuple(_caption_at(captions, index) for index in range(count))


def _consume_line(raw_line: str, captions: list[str], current: list[str]) -> list[str]:
    line = " ".join(raw_line.split())
    if not line:
        _append_caption(captions, current)
        return []
    if _CAPTION_START.match(line):
        _append_caption(captions, current)
        return [line]
    return _continue_caption(current, line)


def _continue_caption(current: list[str], line: str) -> list[str]:
    if current and len(current) < _MAX_CAPTION_LINES:
        return [*current, line]
    return current


def _caption_at(captions: Sequence[str], index: int) -> str:
    if index < len(captions):
        return captions[index]
    return ""


def _append_caption(captions: list[str], current: list[str]) -> None:
    if current:
        captions.append(" ".join(current))
