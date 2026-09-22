"""Offline smoke test: run the real pipeline end to end against local fixtures."""

from __future__ import annotations

import tempfile
from collections.abc import Sequence
from pathlib import Path

from agrifm_g.adapters.finepdf import FinePdfRow
from agrifm_g.adapters.storage import existing_files, read_records
from agrifm_g.domain.verification import verify_records
from agrifm_g.pipeline import build_dataset, build_manifest

FIXTURE = Path("tests/fixtures/two_pages.pdf")


class FixtureCorpus:
    def total(self) -> int:
        return 5

    def rows(self, indices: Sequence[int]) -> list[FinePdfRow]:
        return [
            FinePdfRow(
                doc_id=f"<urn:uuid:{i}>",
                url=f"https://example.org/{i}.pdf",
                text=f"tractor silo field operation {i}",
            )
            for i in indices
        ]

    def fetch(self, url: str) -> bytes:
        return FIXTURE.read_bytes()


def main() -> int:
    corpus = FixtureCorpus()
    with tempfile.TemporaryDirectory() as directory:
        out = Path(directory)
        manifest = build_manifest(corpus, size=3, seed=1)
        records = build_dataset(
            manifest,
            corpus,
            corpus,
            out,
            terms={"tractor", "silo"},
            conventional_terms={"tractor", "silo"},
            sustainable_terms={"permaculture"},
        )
        problems = verify_records(read_records(out), existing_files(out))
        images = sum(record.n_images for record in records)
        print(f"smoke: {len(records)} documents, {images} images, {len(problems)} problems")
        return 1 if problems or len(records) != 3 or images != 6 else 0


if __name__ == "__main__":
    raise SystemExit(main())
