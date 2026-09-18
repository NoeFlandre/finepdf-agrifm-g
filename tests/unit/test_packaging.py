import json

from agrifm_g.adapters.extraction import ExtractedImage
from agrifm_g.adapters.packaging import package_dataset
from agrifm_g.adapters.storage import DocumentPayload, write_dataset


def a_build(tmp_path, fixtures, n_documents=2, duplicate=False):
    from agrifm_g.adapters.extraction import extract_images

    images = extract_images((fixtures / "two_pages.pdf").read_bytes())
    payloads = [
        DocumentPayload(
            raw_doc_id=f"doc-{i}",
            source_url=f"https://example.org/{i}.pdf",
            text="hello",
            pdf_bytes=b"%PDF-1.4 fake" + (b"" if duplicate else bytes([i])),
            images=images
            if duplicate or i == 0
            else tuple(
                ExtractedImage(
                    page=image.page,
                    width=image.width,
                    height=image.height,
                    format=image.format,
                    data=image.data + bytes([i]),
                    sha256=f"{i}{image.sha256[1:]}",
                    n_colours=image.n_colours,
                )
                for image in images
            ),
        )
        for i in range(n_documents)
    ]
    build = tmp_path / "build"
    return build, write_dataset(build, payloads)


def test_packaging_writes_parquet_stats_and_a_card(tmp_path, fixtures):
    build, records = a_build(tmp_path, fixtures)
    out = tmp_path / "publish"
    out.mkdir()
    package = package_dataset(build, out, repo_id="me/x", records=records, sampled=10, seed=3)
    assert package.n_rows == 4
    assert list((out / "data").glob("train-*.parquet"))
    assert json.loads((out / "stats.json").read_text())["documents"]["sampled"] == 10
    assert "me/x" in (out / "README.md").read_text()


def test_the_published_rows_load_back_with_decoded_images(tmp_path, fixtures):
    from datasets import load_dataset

    build, records = a_build(tmp_path, fixtures)
    out = tmp_path / "publish"
    out.mkdir()
    package_dataset(build, out, repo_id="me/x", records=records, sampled=2, seed=3)
    dataset = load_dataset("parquet", data_files=str(out / "data" / "*.parquet"), split="train")
    row = dataset[0]
    assert row["image"].size == (row["width"], row["height"])
    assert row["doc_id"] == "doc-0"


def test_duplicate_images_are_dropped_and_counted(tmp_path, fixtures):
    build, records = a_build(tmp_path, fixtures, duplicate=True)
    out = tmp_path / "publish"
    out.mkdir()
    package = package_dataset(build, out, repo_id="me/x", records=records, sampled=2, seed=3)
    assert package.n_rows == 2
    assert package.stats["images"]["dropped"]["duplicate"] == 2


def test_packaging_is_reproducible(tmp_path, fixtures):
    build, records = a_build(tmp_path, fixtures)
    first, second = tmp_path / "a", tmp_path / "b"
    first.mkdir()
    second.mkdir()
    package_dataset(build, first, repo_id="me/x", records=records, sampled=2, seed=3)
    package_dataset(build, second, repo_id="me/x", records=records, sampled=2, seed=3)
    assert (first / "stats.json").read_text() == (second / "stats.json").read_text()
    assert (first / "README.md").read_text() == (second / "README.md").read_text()
    assert [p.name for p in sorted((first / "data").iterdir())] == [
        p.name for p in sorted((second / "data").iterdir())
    ]
