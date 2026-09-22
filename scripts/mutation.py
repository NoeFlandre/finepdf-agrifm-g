"""Run mutation testing on the domain and enforce a mutation-score floor.

Known survivors are reviewed as equivalent or low-value cases; see
docs/known-limitations.md.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

FLOOR = 0.90
STATS = Path("mutants/mutmut-cicd-stats.json")


def run(*arguments: str) -> None:
    subprocess.run([sys.executable, "-m", "mutmut", *arguments], capture_output=True, text=True)


def main() -> int:
    # mutmut caches results in a working copy; a stale one hides new code.
    # hypothesis writes into it while mutants run, so removal must tolerate that.
    shutil.rmtree("mutants", ignore_errors=True)
    run("run")
    run("export-cicd-stats")
    if not STATS.exists():
        print("mutmut produced no statistics")
        return 1
    stats = json.loads(STATS.read_text())
    total = stats["total"]
    if not total:
        print("no mutants were run")
        return 1
    score = stats["killed"] / total
    print(f"mutation score {score:.1%} ({stats['killed']} killed, {stats['survived']} survived)")
    if score < FLOOR:
        print(f"below the {FLOOR:.0%} floor")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
