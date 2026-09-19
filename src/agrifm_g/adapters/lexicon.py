"""Load the agronomy lexicon from disk, so the domain never reads a file."""

from __future__ import annotations

from pathlib import Path

DEFAULT_PATH = Path("data/agronomy_lexicon.txt")


def load_lexicon(path: Path = DEFAULT_PATH) -> frozenset[str]:
    """One lowercase term per line; blank lines and `#` comments ignored."""
    lines = path.read_text(encoding="utf-8").splitlines()
    return frozenset(
        stripped for line in lines if (stripped := line.strip()) and not stripped.startswith("#")
    )
