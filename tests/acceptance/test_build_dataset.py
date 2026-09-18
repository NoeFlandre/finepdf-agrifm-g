import json

from pytest_bdd import given, scenarios, then, when

from agrifm_g.adapters.finepdf import FinePdfRow
from agrifm_g.adapters.storage import existing_files, read_records
from agrifm_g.domain.records import record_from_json
from agrifm_g.domain.verification import verify_records
from agrifm_g.pipeline import build_dataset, build_manifest

scenarios("features/build_dataset.feature")


class FixtureCorpus:
    def __init__(self, pdf_bytes):
        self._rows = [
            FinePdfRow(doc_id=f"<urn:uuid:{i}>", url=f"https://example.org/{i}.pdf", text=f"t{i}")
            for i in range(10)
        ]
        self._pdf = pdf_bytes

    def total(self):
        return len(self._rows)

    def rows(self, indices):
        return [self._rows[i] for i in indices]

    def fetch(self, url):
        return self._pdf


@given("a manifest of 3 documents drawn from a local fixture corpus", target_fixture="world")
def _readable(fixtures, tmp_path):
    corpus = FixtureCorpus((fixtures / "two_pages.pdf").read_bytes())
    return {"corpus": corpus, "out": tmp_path / "out", "size": 3}


@given("a manifest of 3 documents whose PDFs are not readable", target_fixture="world")
def _unreadable(tmp_path):
    corpus = FixtureCorpus(b"definitely not a pdf")
    return {"corpus": corpus, "out": tmp_path / "out", "size": 3}


@when("I build the dataset")
def _build(world):
    world["out"].mkdir(parents=True, exist_ok=True)
    manifest = build_manifest(world["corpus"], size=world["size"], seed=11)
    world["records"] = build_dataset(manifest, world["corpus"], world["corpus"], world["out"])


@then("the output contains one PDF per document")
def _pdfs(world):
    assert len(list((world["out"] / "pdfs").glob("*.pdf"))) == world["size"]


@then("metadata.jsonl holds one valid record per document")
def _metadata(world):
    lines = (world["out"] / "metadata.jsonl").read_text().splitlines()
    assert len(lines) == world["size"]
    assert [record_from_json(json.loads(line)) for line in lines] == world["records"]


@then("every referenced image file exists on disk")
def _images(world):
    present = existing_files(world["out"])
    assert world["records"]
    assert all(image.path in present for r in world["records"] for image in r.images)


@then("the dataset verifies clean")
def _verifies(world):
    assert verify_records(read_records(world["out"]), existing_files(world["out"])) == []


@then("the dataset is empty but still verifies clean")
def _empty(world):
    assert world["records"] == []
    assert verify_records(read_records(world["out"]), existing_files(world["out"])) == []
