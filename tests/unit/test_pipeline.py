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


TERMS = frozenset({"wheat", "canopy"})


def agricultural_rows():
    return [
        FinePdfRow(doc_id="keep-me", url="https://example.org/0.pdf", text="wheat canopy trial"),
        FinePdfRow(doc_id="skip-me", url="https://example.org/1.pdf", text="quarterly finance"),
    ]


def test_the_text_gate_skips_documents_before_they_are_fetched(tmp_path, fixtures):
    from agrifm_g.pipeline import build_with_outcome

    source = FakeRowSource(agricultural_rows())
    fetcher = FakeFetcher((fixtures / "one_image.pdf").read_bytes())
    manifest = build_manifest(source, size=2, seed=1)
    outcome = build_with_outcome(manifest, source, fetcher, tmp_path, terms=TERMS, threshold=0.05)
    assert [record.doc_id for record in outcome.records] == ["keep-me"]
    assert outcome.gated_out == 1
    assert fetcher.calls == ["https://example.org/0.pdf"]


def test_an_empty_lexicon_means_no_gate_rather_than_no_documents(tmp_path, fixtures):
    from agrifm_g.pipeline import build_with_outcome

    source = FakeRowSource(agricultural_rows())
    fetcher = FakeFetcher((fixtures / "one_image.pdf").read_bytes())
    manifest = build_manifest(source, size=2, seed=1)
    outcome = build_with_outcome(manifest, source, fetcher, tmp_path, terms=())
    assert len(outcome.records) == 2
    assert outcome.gated_out == 0


def test_the_outcome_reports_what_was_sampled(tmp_path, fixtures):
    from agrifm_g.pipeline import build_with_outcome

    source = FakeRowSource(agricultural_rows())
    manifest = build_manifest(source, size=2, seed=1)
    outcome = build_with_outcome(
        manifest,
        source,
        FakeFetcher((fixtures / "one_image.pdf").read_bytes()),
        tmp_path,
        terms=TERMS,
        threshold=0.05,
    )
    assert outcome.sampled == 2


def test_category_text_assigns_documents_and_drops_ambiguous_ones(tmp_path, fixtures):
    from agrifm_g.pipeline import build_with_outcome

    source = FakeRowSource(
        [
            FinePdfRow("conventional", "https://example.org/c.pdf", "agriculture tractor silo"),
            FinePdfRow("sustainable", "https://example.org/s.pdf", "agriculture permaculture"),
            FinePdfRow(
                "ambiguous",
                "https://example.org/a.pdf",
                "agriculture tractor permaculture",
            ),
        ]
    )
    fetcher = FakeFetcher((fixtures / "one_image.pdf").read_bytes())
    manifest = build_manifest(source, size=3, seed=1)

    outcome = build_with_outcome(
        manifest,
        source,
        fetcher,
        tmp_path,
        terms={"agriculture"},
        threshold=0.05,
        conventional_terms={"tractor", "silo"},
        sustainable_terms={"permaculture"},
    )

    assert [(record.doc_id, record.agriculture_split) for record in outcome.records] == [
        ("conventional", "conventional"),
        ("sustainable", "sustainable"),
    ]
    assert outcome.ambiguous_out == 1
    assert fetcher.calls == ["https://example.org/c.pdf", "https://example.org/s.pdf"]


def test_concurrent_retrieval_preserves_manifest_order(tmp_path, fixtures):
    """Threads overlap the waiting; they must not reorder the build."""
    manifest = build_manifest(FakeRowSource(rows(8)), size=8, seed=5)
    fetcher = FakeFetcher((fixtures / "one_image.pdf").read_bytes())

    records = build_dataset(manifest, FakeRowSource(rows(8)), fetcher, tmp_path, workers=4)

    assert [record.doc_id for record in records] == sorted(record.doc_id for record in records)
    assert sorted(fetcher.calls) == sorted(manifest_urls(manifest))


def manifest_urls(manifest):
    return [f"https://example.org/{index}.pdf" for index in manifest.indices]


def test_a_single_worker_still_builds_the_same_dataset(tmp_path, fixtures):
    manifest = build_manifest(FakeRowSource(rows(4)), size=4, seed=5)
    payload = (fixtures / "one_image.pdf").read_bytes()

    serial = build_dataset(
        manifest, FakeRowSource(rows(4)), FakeFetcher(payload), tmp_path / "serial", workers=1
    )
    threaded = build_dataset(
        manifest, FakeRowSource(rows(4)), FakeFetcher(payload), tmp_path / "threaded", workers=8
    )

    assert [record.doc_id for record in serial] == [record.doc_id for record in threaded]
