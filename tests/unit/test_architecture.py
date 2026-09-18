"""The boundaries from ADR-0001, enforced rather than described."""

import ast
import subprocess
import sys
from pathlib import Path

import pytest

DOMAIN = Path(__file__).parents[2] / "src" / "agrifm_g" / "domain"
BANNED_IN_DOMAIN = {
    "agrifm_g.adapters",
    "agrifm_g.cli",
    "agrifm_g.pipeline",
    "httpx",
    "pypdf",
    "PIL",
    "huggingface_hub",
    "pyarrow",
    "pathlib",
}


def imported_modules(source: str) -> set[str]:
    tree = ast.parse(source)
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module)
    return names


@pytest.mark.parametrize("module", sorted(DOMAIN.glob("*.py")), ids=lambda p: p.name)
def test_the_domain_imports_no_io(module):
    offenders = {
        name
        for name in imported_modules(module.read_text())
        if any(name == banned or name.startswith(f"{banned}.") for banned in BANNED_IN_DOMAIN)
    }
    assert offenders == set()


def test_the_scanner_would_catch_a_violation():
    assert imported_modules("import httpx") & BANNED_IN_DOMAIN == {"httpx"}


def test_the_declared_contracts_hold():
    result = subprocess.run(
        [sys.executable, "-m", "importlinter.cli", "lint-imports"],
        capture_output=True,
        text=True,
        cwd=Path(__file__).parents[2],
    )
    assert result.returncode == 0, result.stdout + result.stderr
