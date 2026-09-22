from pathlib import Path

import pytest
from scripts.build_scaled_sample import (
    _prepare_group_dir,
    group_refs,
    merge_builds,
    require_grid5000_execution,
)

from agrifm_g.adapters.extraction import extract_images
from agrifm_g.adapters.storage import DocumentPayload, read_records, write_dataset


def _payload(fixtures: Path, doc_id: str) -> DocumentPayload:
    pdf = (fixtures / "one_image.pdf").read_bytes()
    return DocumentPayload(
        raw_doc_id=doc_id,
        source_url=f"https://example.org/{doc_id}.pdf",
        text="wheat canopy",
        pdf_bytes=pdf,
        images=extract_images(pdf),
    )


def test_merge_builds_combines_group_directories(fixtures, tmp_path):
    first = tmp_path / "g0"
    second = tmp_path / "g1"
    write_dataset(first, [_payload(fixtures, "first")])
    write_dataset(second, [_payload(fixtures, "second")])

    merged = tmp_path / "dataset"
    records = merge_builds([first, second], merged)

    assert [record.doc_id for record in records] == ["first", "second"]
    assert len(read_records(merged)) == 2
    assert (merged / "pdfs/first.pdf").exists()
    assert (merged / "images/second/000.png").exists()


def test_group_refs_spread_the_sample_across_shards():
    refs = group_refs([0, 7], [0, 1])

    assert [ref.slug for ref in refs] == ["s00000g0", "s00000g1", "s00007g0", "s00007g1"]
    assert refs[-1].shard_name == "000_00007.parquet"
    assert refs[-1].source().row_group == 1


def test_scaled_build_requires_an_oar_job(monkeypatch):
    monkeypatch.delenv("AGRIFM_G_GRID5000_JOB", raising=False)
    monkeypatch.delenv("OAR_JOB_ID", raising=False)
    monkeypatch.delenv("OAR_NODEFILE", raising=False)

    with pytest.raises(SystemExit, match="Grid5000"):
        require_grid5000_execution()


def test_resume_discards_only_an_incomplete_group_part(tmp_path):
    staging = tmp_path / "groups"
    group_dir = staging / "s00000g0"
    partial = staging / ".s00000g0.part"
    partial.mkdir(parents=True)
    (partial / "partial").write_text("incomplete")
    completed = staging / "s00000g1"
    completed.mkdir()
    (completed / "metadata.jsonl").write_text("complete\n")

    prepared = _prepare_group_dir(group_dir, resume=True)

    assert prepared == partial
    assert partial.is_dir()
    assert not (partial / "partial").exists()
    assert (completed / "metadata.jsonl").read_text() == "complete\n"
