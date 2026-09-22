import hashlib
import io
import json

from PIL import Image

from agrifm_g.adapters.extraction import ExtractedImage
from agrifm_g.adapters.packaging import package_dataset
from agrifm_g.adapters.storage import DocumentPayload, write_dataset


def png(width: int, height: int, seed: int) -> bytes:
    """A deterministic multi-colour PNG, so counts do not depend on pypdf or PIL."""
    image = Image.new("RGB", (width, height))
    image.putdata(
        [
            ((x * 3 + seed) % 256, (y * 5 + seed) % 256, (x + y + seed) % 256)
            for y in range(height)
            for x in range(width)
        ]
    )
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def an_image(page: int, seed: int) -> ExtractedImage:
    data = png(60, 40, seed)
    return ExtractedImage(
        page=page,
        width=60,
        height=40,
        format="png",
        data=data,
        sha256=hashlib.sha256(data).hexdigest(),
        n_colours=30000,
        dominant_colour_share=0.02,
        near_white_share=0.02,
        edge_density=0.25,
    )


def a_build(tmp_path, n_documents=2, duplicate=False):
    """Two documents with two images each; `duplicate` makes both documents identical."""
    payloads = [
        DocumentPayload(
            raw_doc_id=f"doc-{i}",
            source_url=f"https://example.org/{i}.pdf",
            text="hello",
            pdf_bytes=b"%PDF-1.4 fake",
            agriculture_split="conventional" if i == 0 else "sustainable",
            images=(an_image(0, 1), an_image(1, 2))
            if duplicate
            else (an_image(0, 1 + 10 * i), an_image(1, 2 + 10 * i)),
        )
        for i in range(n_documents)
    ]
    build = tmp_path / "build"
    return build, write_dataset(build, payloads)


def test_packaging_writes_parquet_stats_and_a_card(tmp_path):
    build, records = a_build(tmp_path)
    out = tmp_path / "publish"
    out.mkdir()
    package = package_dataset(build, out, repo_id="me/x", records=records, sampled=10, seed=3)
    assert package.n_rows == 4
    assert list((out / "data").glob("conventional-*.parquet"))
    assert list((out / "data").glob("sustainable-*.parquet"))
    assert not list((out / "data").glob("train-*.parquet"))
    assert json.loads((out / "stats.json").read_text())["documents"]["sampled"] == 10
    assert "me/x" in (out / "README.md").read_text()


def test_the_published_rows_load_back_with_decoded_images(tmp_path):
    from datasets import load_dataset

    build, records = a_build(tmp_path)
    out = tmp_path / "publish"
    out.mkdir()
    package_dataset(build, out, repo_id="me/x", records=records, sampled=2, seed=3)
    dataset = load_dataset(
        "parquet", data_files=str(out / "data" / "conventional-*.parquet"), split="train"
    )
    row = dataset[0]
    assert row["image"].size == (row["width"], row["height"])
    assert row["doc_id"] == "doc-0"
    assert row["agriculture_split"] == "conventional"


def test_duplicate_images_are_dropped_and_counted(tmp_path):
    build, records = a_build(tmp_path, duplicate=True)
    out = tmp_path / "publish"
    out.mkdir()
    package = package_dataset(build, out, repo_id="me/x", records=records, sampled=2, seed=3)
    assert package.n_rows == 2
    assert package.stats["images"]["dropped"]["duplicate"] == 2


def test_packaging_is_reproducible(tmp_path):
    build, records = a_build(tmp_path)
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
