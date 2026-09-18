import json

from agrifm_g.adapters.finepdf import FinePdfRow
from agrifm_g.adapters.storage import read_records
from agrifm_g.pipeline import Manifest, build_dataset, build_manifest


class FakeRowSource:
    def __init__(self, rows):
        self._rows = rows

    def total(self):
        return len(self._rows)

    def rows(self, indices):
        return [self._rows[i] for i in indices]


class FakeFetcher:
    def __init__(self, fixture_bytes):
        self._bytes = fixture_bytes
        self.calls = []

    def fetch(self, url):
        self.calls.append(url)
        return self._bytes


def rows(n=5):
    return [
        FinePdfRow(doc_id=f"doc-{i}", url=f"https://example.org/{i}.pdf", text=f"text {i}")
        for i in range(n)
    ]


def test_manifest_records_the_seed_and_resolved_ids():
    manifest = build_manifest(FakeRowSource(rows()), size=2, seed=42)
    assert manifest.size == 2
    assert manifest.seed == 42
    assert len(manifest.doc_ids) == 2
    assert manifest.doc_ids == ("doc-0", "doc-4")


def test_manifest_is_reproducible():
    assert build_manifest(FakeRowSource(rows()), size=3, seed=1) == build_manifest(
        FakeRowSource(rows()), size=3, seed=1
    )


def test_manifest_round_trips_through_json():
    manifest = build_manifest(FakeRowSource(rows()), size=2, seed=7)
    assert Manifest.from_json(json.loads(manifest.to_json())) == manifest


def test_build_produces_one_record_per_manifest_entry(tmp_path, fixtures):
    manifest = build_manifest(FakeRowSource(rows()), size=3, seed=5)
    fetcher = FakeFetcher((fixtures / "one_image.pdf").read_bytes())
    records = build_dataset(manifest, FakeRowSource(rows()), fetcher, tmp_path)
    assert len(records) == 3
    assert read_records(tmp_path) == records
    assert all(record.n_images == 1 for record in records)


def test_build_skips_documents_whose_pdf_cannot_be_read(tmp_path):
    manifest = build_manifest(FakeRowSource(rows()), size=2, seed=5)
    records = build_dataset(manifest, FakeRowSource(rows()), FakeFetcher(b"not a pdf"), tmp_path)
    assert records == []
