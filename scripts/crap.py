"""Fail the build when any function's CRAP score reaches the agreed ceiling.

CRAP(f) = cc(f)^2 * (1 - coverage(f))^3 + cc(f)
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

CEILING = 6.0


def radon_blocks() -> list[dict]:
    raw = subprocess.run(
        [sys.executable, "-m", "radon", "cc", "-j", "src"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    return [
        {"file": file, "name": block["name"], "line": block["lineno"], "cc": block["complexity"]}
        for file, blocks in json.loads(raw).items()
        for block in blocks
        if block["type"] in {"function", "method"}
    ]


def coverage_by_line(report: Path) -> dict[str, tuple[set[int], set[int]]]:
    data = json.loads(report.read_text())
    return {
        file: (set(info["executed_lines"]), set(info["missing_lines"]))
        for file, info in data["files"].items()
    }


def crap(cc: int, covered: float) -> float:
    return cc**2 * (1 - covered) ** 3 + cc


def main() -> int:
    report = Path("coverage.json")
    if not report.exists():
        print("coverage.json missing: run pytest --cov --cov-report=json first")
        return 1
    lines = coverage_by_line(report)
    failures = []
    for block in radon_blocks():
        executed, missing = lines.get(block["file"], (set(), set()))
        body = {line for line in executed | missing if line >= block["line"]}
        relevant = sorted(body)[: block["cc"] * 4] or [block["line"]]
        covered_ratio = sum(1 for line in relevant if line in executed) / len(relevant)
        score = crap(block["cc"], covered_ratio)
        if score >= CEILING:
            failures.append(f"{block['file']}:{block['line']} {block['name']} CRAP={score:.1f}")
    for failure in failures:
        print(failure)
    print("CRAP ok" if not failures else f"{len(failures)} functions at or above CRAP {CEILING}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
