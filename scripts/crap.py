"""Fail the build when any function's CRAP score reaches the agreed ceiling.

CRAP(f) = cc(f)^2 * (1 - coverage(f))^3 + cc(f)

Complexity comes from radon, coverage from coverage.json, and a function's line span
from the AST — so a function is scored on its own lines, not on a window around them.
"""

from __future__ import annotations

import ast
import json
import subprocess
import sys
from pathlib import Path

CEILING = 6.0


def radon_complexity() -> dict[tuple[str, int], int]:
    raw = subprocess.run(
        [sys.executable, "-m", "radon", "cc", "-j", "src"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    return {
        (file, block["lineno"]): block["complexity"]
        for file, blocks in json.loads(raw).items()
        for block in blocks
        if block["type"] in {"function", "method"}
    }


def function_spans(file: str) -> dict[int, set[int]]:
    """Map each function's first line to the lines it owns, nested ones excluded."""
    tree = ast.parse(Path(file).read_text())
    functions = [
        node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef)
    ]
    spans = {
        node.lineno: set(range(node.lineno, (node.end_lineno or node.lineno) + 1))
        for node in functions
    }
    for node in functions:
        for other in functions:
            if other is not node and other.lineno in spans[node.lineno]:
                spans[node.lineno] -= spans[other.lineno]
    return spans


def main() -> int:
    report = Path("coverage.json")
    if not report.exists():
        print("coverage.json missing: run pytest --cov --cov-report=json first")
        return 1
    files = json.loads(report.read_text())["files"]
    failures = []
    for (file, line), complexity in radon_complexity().items():
        info = files.get(file)
        if info is None:
            continue
        owned = function_spans(file).get(line, {line})
        executed = owned & set(info["executed_lines"])
        missing = owned & set(info["missing_lines"])
        total = len(executed) + len(missing)
        covered = len(executed) / total if total else 1.0
        score = complexity**2 * (1 - covered) ** 3 + complexity
        if score >= CEILING:
            failures.append(f"{file}:{line} CRAP={score:.1f} (cc={complexity}, cov={covered:.0%})")
    for failure in failures:
        print(failure)
    print("CRAP ok" if not failures else f"{len(failures)} functions at or above CRAP {CEILING}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
