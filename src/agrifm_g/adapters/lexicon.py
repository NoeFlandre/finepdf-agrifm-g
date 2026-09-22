"""Load the term lists from disk, so the domain never reads a file.

Two lists, because the two gates want opposite things. `DEFAULT_PATH` (agronomy) gates
document text *before* a fetch and is tuned for recall: a document it rejects is never
seen again. `PHENOTYPE_PATH` gates an image's caption *after* the fetch and is tuned for
precision: by then the cost is already paid, and what is left is the published row.
"""

from __future__ import annotations

from pathlib import Path

DEFAULT_PATH = Path("data/agronomy_lexicon.txt")
PHENOTYPE_PATH = Path("data/phenotype_lexicon.txt")


def load_lexicon(path: Path = DEFAULT_PATH) -> frozenset[str]:
    """One lowercase term per line; blank lines and `#` comments ignored."""
    lines = path.read_text(encoding="utf-8").splitlines()
    return frozenset(
        stripped for line in lines if (stripped := line.strip()) and not stripped.startswith("#")
    )


def load_phenotype_lexicon(path: Path = PHENOTYPE_PATH) -> frozenset[str]:
    """The precision-tuned caption lexicon: organs, traits, symptoms, crops and scenes."""
    return load_lexicon(path)
