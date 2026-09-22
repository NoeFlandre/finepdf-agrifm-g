"""Load the agriculture term lists from disk, so the domain never reads a file."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

AGRICULTURE_PATH = Path("data/agriculture_lexicon.txt")
CONVENTIONAL_PATH = Path("data/conventional_agriculture_lexicon.txt")
SUSTAINABLE_PATH = Path("data/sustainable_agriculture_lexicon.txt")
DEFAULT_PATH = AGRICULTURE_PATH


@dataclass(frozen=True, slots=True)
class AgricultureLexicons:
    """The broad pre-fetch vocabulary and the two mutually exclusive categories."""

    broad: frozenset[str]
    conventional: frozenset[str]
    sustainable: frozenset[str]

    @property
    def prefetch_terms(self) -> frozenset[str]:
        return self.broad | self.conventional | self.sustainable


def load_lexicon(path: Path = DEFAULT_PATH) -> frozenset[str]:
    """One lowercase term per line; blank lines and `#` comments ignored."""
    lines = path.read_text(encoding="utf-8").splitlines()
    return frozenset(
        stripped for line in lines if (stripped := line.strip()) and not stripped.startswith("#")
    )


def load_agriculture_lexicons() -> AgricultureLexicons:
    """Load the broad and category-specific vocabularies used by the scaled build."""
    return AgricultureLexicons(
        broad=load_lexicon(AGRICULTURE_PATH),
        conventional=load_lexicon(CONVENTIONAL_PATH),
        sustainable=load_lexicon(SUSTAINABLE_PATH),
    )
