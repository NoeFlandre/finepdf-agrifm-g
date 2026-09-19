import json

import pytest

from agrifm_g.adapters.extraction import ExtractedImage
from agrifm_g.adapters.storage import DocumentPayload, write_dataset
from agrifm_g.cli import main


def a_dataset(path):
    write_dataset(
        path,
        [
            DocumentPayload(
                raw_doc_id="doc-1",
                source_url="https://example.org/a.pdf",
                text="hello",
                pdf_bytes=b"%PDF-1.4",
                images=(
                    ExtractedImage(
                        page=0,
                        width=50,
                        height=50,
                        format="png",
                        dominant_colour_share=0.02,
                        near_white_share=0.02,
                        edge_density=0.25,
                        data=b"\x89PNG",
                        sha256="a" * 64,
                        n_colours=6,
                    ),
                ),
            )
        ],
    )


def test_verify_accepts_a_complete_dataset(tmp_path, capsys):
    a_dataset(tmp_path)
    assert main(["verify", "--dataset", str(tmp_path)]) == 0
    assert "ok" in capsys.readouterr().out


def test_verify_rejects_a_dataset_with_a_missing_file(tmp_path, capsys):
    a_dataset(tmp_path)
    (tmp_path / "pdfs" / "doc-1.pdf").unlink()
    assert main(["verify", "--dataset", str(tmp_path)]) == 1
    assert "missing pdf" in capsys.readouterr().out


def test_publish_dry_run_touches_nothing(tmp_path, capsys):
    a_dataset(tmp_path)
    code = main(["publish", "--dataset", str(tmp_path), "--repo", "me/x", "--dry-run"])
    assert code == 0
    assert "dry run" in capsys.readouterr().out


def test_unknown_command_is_an_error():
    with pytest.raises(SystemExit):
        main(["nonsense"])


def test_help_lists_every_command(capsys):
    with pytest.raises(SystemExit):
        main(["--help"])
    out = capsys.readouterr().out
    assert {"sample", "build", "package", "verify", "publish"} <= set(out.split())


def test_sample_writes_a_manifest(tmp_path, monkeypatch):
    from agrifm_g import cli
    from agrifm_g.adapters.finepdf import FinePdfRow

    class FakeSource:
        def total(self):
            return 10

        def rows(self, indices):
            return [FinePdfRow(doc_id=f"d{i}", url=f"u{i}", text="t") for i in indices]

    monkeypatch.setattr(cli, "_row_source", lambda _args: FakeSource())
    manifest_path = tmp_path / "m.json"
    assert main(["sample", "--size", "2", "--seed", "3", "--out", str(manifest_path)]) == 0
    assert len(json.loads(manifest_path.read_text())["doc_ids"]) == 2


def test_build_writes_a_dataset_from_a_manifest(tmp_path, monkeypatch, fixtures):
    from agrifm_g import cli
    from agrifm_g.adapters.finepdf import FinePdfRow
    from agrifm_g.pipeline import build_manifest

    class FakeSource:
        def total(self):
            return 4

        def rows(self, indices):
            return [
                FinePdfRow(doc_id=f"d{i}", url=f"https://example.org/{i}.pdf", text="t")
                for i in indices
            ]

    pdf = (fixtures / "one_image.pdf").read_bytes()
    monkeypatch.setattr(cli, "ParquetRowSource", lambda **kwargs: FakeSource())
    monkeypatch.setattr(
        cli, "CachingPdfFetcher", lambda **kwargs: type("F", (), {"fetch": lambda self, url: pdf})()
    )
    manifest = tmp_path / "m.json"
    manifest.write_text(build_manifest(FakeSource(), size=2, seed=1).to_json())
    out = tmp_path / "out"
    argv = ["build", "--manifest", str(manifest), "--out", str(out), "--cache", str(tmp_path / "c")]
    # the rows carry no agronomy vocabulary, so the gate is off for this check
    assert main([*argv, "--min-text-score", "0"]) == 0
    assert len(read_records_from(out)) == 2


def test_build_applies_the_text_gate_by_default(tmp_path, monkeypatch, fixtures, capsys):
    """The same rows, with the gate at its default: nothing agricultural, nothing fetched."""
    from agrifm_g import cli
    from agrifm_g.adapters.finepdf import FinePdfRow
    from agrifm_g.pipeline import Manifest

    class FakeSource:
        def total(self):
            return 4

        def rows(self, indices):
            return [
                FinePdfRow(
                    doc_id=f"d{i}", url=f"https://example.org/{i}.pdf", text="quarterly report"
                )
                for i in indices
            ]

    monkeypatch.setattr(cli, "ParquetRowSource", lambda **kwargs: FakeSource())
    monkeypatch.setattr(
        cli,
        "CachingPdfFetcher",
        lambda **kwargs: type("F", (), {"fetch": lambda self, url: pytest.fail("fetched")})(),
    )
    manifest = tmp_path / "m.json"
    manifest.write_text(
        Manifest(
            dataset="d",
            config="c",
            split="train",
            seed=3,
            size=2,
            indices=(0, 1),
            doc_ids=("d0", "d1"),
        ).to_json()
    )
    out = tmp_path / "out"
    assert (
        main(
            [
                "build",
                "--manifest",
                str(manifest),
                "--out",
                str(out),
                "--cache",
                str(tmp_path / "c"),
            ]
        )
        == 0
    )
    assert "skipped 2/2" in capsys.readouterr().out


def read_records_from(path):
    from agrifm_g.adapters.storage import read_records

    return read_records(path)


def test_package_writes_parquet_and_a_card(tmp_path, fixtures):
    from agrifm_g.adapters.extraction import extract_images
    from agrifm_g.adapters.storage import DocumentPayload, write_dataset
    from agrifm_g.pipeline import Manifest

    build = tmp_path / "build"
    write_dataset(
        build,
        [
            DocumentPayload(
                raw_doc_id="doc-1",
                source_url="https://example.org/a.pdf",
                text="hello",
                pdf_bytes=(fixtures / "one_image.pdf").read_bytes(),
                images=extract_images((fixtures / "one_image.pdf").read_bytes()),
            )
        ],
    )
    manifest = tmp_path / "m.json"
    manifest.write_text(
        Manifest(
            dataset="d", config="c", split="train", seed=3, size=1, indices=(0,), doc_ids=("doc-1",)
        ).to_json()
    )
    out = tmp_path / "publish"
    code = main(
        [
            "package",
            "--dataset",
            str(build),
            "--out",
            str(out),
            "--repo",
            "me/x",
            "--manifest",
            str(manifest),
        ]
    )
    assert code == 0
    assert list((out / "data").glob("train-*.parquet"))
    assert (out / "README.md").exists()
