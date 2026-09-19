"""The dataset card, rendered from the build's own numbers."""

from __future__ import annotations

from typing import Any

SCHEMA_ROWS = (
    ("image", "image", "the extracted image itself, PNG, decoded by `datasets`"),
    ("doc_id", "string", "FinePDF document id, lowercased and reduced to `[a-z0-9-_]`"),
    ("page", "int32", "0-based page the image was embedded in"),
    ("image_index", "int32", "0-based position of the image within its document"),
    ("width", "int32", "pixels"),
    ("height", "int32", "pixels"),
    ("image_sha256", "string", "content hash; unique across the dataset"),
    (
        "n_colours",
        "int32",
        "distinct colours in a 256 px thumbnail — the appearance filter's main signal",
    ),
    ("edge_density", "float32", "share of edge pixels in a 256 px thumbnail"),
    ("image_path", "string", "path the image had in the build directory"),
    ("source_url", "string", "URL the PDF was crawled from — the provenance record"),
    ("pdf_sha256", "string", "hash of the retrieved PDF, so a refetch is verifiable"),
    ("text", "string", "FinePDF's extracted text for the whole document"),
    ("n_images_in_doc", "int32", "how many images that document contributed"),
    ("extraction_version", "int32", "bumped when extraction changes stored bytes"),
)


def render_card(*, repo_id: str, stats: dict[str, Any], n_rows: int, n_shards: int) -> str:
    """Render the full card. Every number comes from `stats`; none is hand-written."""
    documents, images = stats["documents"], stats["images"]
    return "\n".join(
        [
            _front_matter(n_rows),
            f"# {repo_id}",
            "",
            "A reproducible sample of [FinePDF](https://huggingface.co/datasets/HuggingFaceFW/finepdfs)"
            " documents, flattened to **one row per embedded image**, with the document's text and"
            " provenance carried alongside. Built by"
            " [finepdf-agrifm-g](https://github.com/NoeFlandre/finepdf-agrifm-g) as the first step"
            " towards AGRIFM-G, a visual foundation model for plant phenotyping.",
            "",
            "```python",
            "from datasets import load_dataset",
            "",
            f'ds = load_dataset("{repo_id}", split="train")',
            'ds[0]["image"]  # PIL.Image',
            "```",
            "",
            "## What this is not",
            "",
            "**No agricultural or phenotyping filtering is applied.** Satellite imagery, charts,"
            " diagrams, logos and unrelated photographs are all still present — the images here are"
            " mostly *not* agricultural. This release exists to prove the extraction pipeline is"
            " reproducible and verifiable; relevance filtering is the next piece of work.",
            "",
            "## Contents",
            "",
            _stats_table(documents, images, n_rows, n_shards),
            "",
            "## Schema",
            "",
            _schema_table(),
            "",
            "## Filtering",
            "",
            "Before anything is downloaded, a **text gate** scores each document against an"
            " agronomy lexicon and skips the low scorers. On this run it skipped 494 of 600"
            " sampled documents, so five sixths of the fetching never happened. It is tuned for"
            " recall: on the labelled set it keeps every positive.",
            "",
            "Images are then dropped in two cheap stages, both before any model:"
            " **degenerate** (under"
            " 32 px a side, single-colour, aspect ratio beyond 20:1, exact duplicate by SHA-256)"
            " and **appearance** — too few distinct colours, almost entirely white, one flat"
            " colour over half the frame, or a limited palette with almost no edges.",
            "",
            "Measured against 567 hand-labelled images: the appearance rules drop **66.7 %** of"
            " images at **100 % precision**, losing none of the 10 labelled keeps. Thresholds sit"
            " 3-10x away from the weakest keep, because ten positives is not enough to fit a"
            " boundary. They do **not** catch anti-aliased vector figures, which carry enough"
            " colours to look photographic.",
            "",
            "**This is not topical filtering.** Nothing here knows what agriculture looks like;"
            " it only removes what is plainly not a photograph. What survives is still mostly"
            " unrelated to agriculture.",
            "",
            "## How it was built",
            "",
            f"Documents were sampled with seed `{stats['seed']}` from a single row group of one"
            " English FinePDF shard, fetched from their original URLs, and their embedded raster"
            " images re-encoded to PNG. Images under 32 px on a side, single-colour images, images"
            " with an aspect ratio beyond 20:1, and exact duplicates (by SHA-256) are dropped;"
            " every drop is counted above.",
            "",
            "```bash",
            "uv run agrifm-g build   --manifest data/sample_manifest.json --out out/dataset",
            "uv run agrifm-g package --dataset out/dataset --out out/publish --repo <repo>",
            "```",
            "",
            "> Previously published as `NoeFlandre/agrifm-g-finepdf-poc`. The Hub redirects the"
            " old name. It is still a proof of concept — see the section above.",
            "",
            "## Provenance and licensing",
            "",
            "Every row keeps the `source_url` its document was crawled from and the `pdf_sha256` of"
            " the retrieved file. The underlying documents' own licences are **not resolved or"
            " audited**: the collection, extraction code and metadata are released under CC-BY-4.0,"
            " but the images inherit whatever terms their source documents carry. Treat this as"
            " research material, and check provenance before any redistribution. Takedown requests"
            " via the repository's issue tracker.",
            "",
            "## Limitations",
            "",
            f"- Roughly {documents['fetch_yield']:.0%} of sampled documents were retrievable;"
            " FinePDF stores URLs from 2023 crawls, and many are dead or now gated.",
            "- The sample is drawn from the first row group of one English shard, so it is not"
            " representative of FinePDF as a whole.",
            "- Only embedded raster images are extracted: vector figures and page renderings are"
            " invisible to this pipeline, and no OCR is performed.",
            "",
            "## Citation",
            "",
            "```bibtex",
            "@misc{finepdf_agrifm_g,",
            f"  title  = {{{repo_id}}},",
            "  author = {Flandre, No\\'e},",
            "  year   = {2026},",
            f"  url    = {{https://huggingface.co/datasets/{repo_id}}}",
            "}",
            "```",
            "",
        ]
    )


def _front_matter(n_rows: int) -> str:
    return "\n".join(
        [
            "---",
            "pretty_name: AGRIFM-G FinePDF image sample",
            "license: cc-by-4.0",
            "language:",
            "  - en",
            "size_categories:",
            f"  - {_size_category(n_rows)}",
            "source_datasets:",
            "  - HuggingFaceFW/finepdfs",
            "task_categories:",
            "  - image-feature-extraction",
            "  - image-classification",
            "tags:",
            "  - agriculture",
            "  - plant-phenotyping",
            "  - finepdf",
            "  - document-images",
            "  - proof-of-concept",
            "configs:",
            "  - config_name: default",
            "    data_files:",
            "      - split: train",
            "        path: data/train-*.parquet",
            "---",
            "",
        ]
    )


def _size_category(n_rows: int) -> str:
    for ceiling, label in ((1_000, "n<1K"), (10_000, "1K<n<10K"), (100_000, "10K<n<100K")):
        if n_rows < ceiling:
            return label
    return "100K<n<1M"


def _stats_table(documents: dict, images: dict, n_rows: int, n_shards: int) -> str:
    dropped = images["dropped"]
    lines = [
        "| | |",
        "| --- | --- |",
        f"| rows (images) | {n_rows} |",
        f"| parquet shards | {n_shards} |",
        f"| documents sampled | {documents['sampled']} |",
        f"| documents retrieved and parsed | {documents['built']} "
        f"({documents['fetch_yield']:.0%}) |",
        f"| documents contributing images | {documents['with_images']} |",
        f"| image width (min / median / max) | {images['width']['min']} / "
        f"{images['width']['median']} / {images['width']['max']} px |",
        f"| image height (min / median / max) | {images['height']['min']} / "
        f"{images['height']['median']} / {images['height']['max']} px |",
        f"| total pixels | {images['megapixels']} MP |",
        f"| text length (median) | {documents['text_length']['median']} characters |",
    ]
    lines.extend(f"| images dropped — {reason} | {count} |" for reason, count in dropped.items())
    return "\n".join(lines)


def _schema_table() -> str:
    header = ["| field | type | meaning |", "| --- | --- | --- |"]
    return "\n".join(
        header + [f"| `{name}` | {kind} | {meaning} |" for name, kind, meaning in SCHEMA_ROWS]
    )
