"""The dataset card, rendered from the build's own numbers."""

from __future__ import annotations

from typing import Any

from agrifm_g.domain.textgate import DEFAULT_THRESHOLD

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
    ("image_path", "string", "path the image had in the build directory"),
    ("edge_density", "float32", "share of edge pixels in a 256 px thumbnail"),
    ("caption", "string", "explicit figure caption extracted from the PDF page"),
    ("source_url", "string", "URL the PDF was crawled from — the provenance record"),
    ("pdf_sha256", "string", "hash of the retrieved PDF, so a refetch is verifiable"),
    ("text", "string", "FinePDF's extracted text for the whole document"),
    ("n_images_in_doc", "int32", "how many images that document contributed"),
    ("extraction_version", "int32", "bumped when extraction changes stored bytes"),
)


def render_card(*, repo_id: str, stats: dict[str, Any], n_rows: int, n_shards: int) -> str:
    """Render the compact reader-facing card from the build's own numbers."""
    documents, images = stats["documents"], stats["images"]
    return "\n".join(
        [
            _front_matter(n_rows),
            f"# {repo_id}",
            "",
            "A reproducible [FinePDF](https://huggingface.co/datasets/HuggingFaceFW/finepdfs)"
            " sample flattened to **one row per retained embedded raster image**. Each row keeps"
            " the image caption, document text and provenance for the AGRIFM-G experiment.",
            "",
            "```python",
            "from datasets import load_dataset",
            "",
            f'ds = load_dataset("{repo_id}", split="train")',
            'ds[0]["image"]  # PIL.Image',
            "```",
            "",
            "## Contents",
            "",
            _stats_table(documents, images, n_rows, n_shards),
            "",
            "## Schema",
            "",
            _schema_table(),
            "",
            "## Selection and filtering",
            "",
            f"- **Document gate:** documents below the {DEFAULT_THRESHOLD:.1%} agronomy-lexicon"
            " word-share threshold are not downloaded; the threshold keeps every labelled"
            " positive.",
            "",
            "- **Caption gate:** only a line beginning with a figure label — `Figure`, `Fig.`,"
            " `Photo`, `Plate`, `Image`, `Figura`, `Abb.` — plus an identifier (or, unnumbered, a"
            " colon or dash) is a caption; nearby page prose is ignored. The caption must contain"
            " a whole-word hit from the **phenotype lexicon** (organs, traits, symptoms, crops and"
            " growing scenes) and is published in `caption`. Generic agricultural context words"
            " such as *field*, *soil*, *yield* and *trial* are deliberately excluded there,"
            " because they select charts and maps rather than pictures of plants.",
            "",
            "- **Cheap visual gate:** images must be at least 32 px on each side,"
            " non-single-colour, no wider than 20:1 and unique by SHA-256. A colour image must"
            " then use more than 8,000 colours and have edge density ≥ 0.18; near-white,"
            " flat-background, sparse line-art and low-texture images are dropped. A **greyscale**"
            " image is judged on texture alone (edge density ≥ 0.30), because an 8-bit greyscale"
            " photograph holds at most 256 colours and the colour-count rule would reject every"
            " scanned field photograph and electron micrograph on a technicality.",
            "",
            "On 567 hand-labelled images, the strict appearance rules removed **77.6%** at"
            " **100% precision**, losing none of the 10 labelled keeps. This is not semantic"
            " agricultural filtering; unrelated photographs and vector figures can remain.",
            "",
            "## Reproduce and limitations",
            "",
            f"The bounded run samples {documents['source_shards']} English FinePDF shards with seed"
            f" `{stats['seed']}`, one row group each, so the sample is not an accident of a single"
            " crawl segment. PDFs are fetched from their original URLs and"
            " are not redistributed; `source_url` and `pdf_sha256` preserve provenance, but source"
            " licences are not audited.",
            "",
            "```bash",
            "uv run python -m scripts.grid5000 preflight",
            "uv run python -m scripts.grid5000 submit --repo <repo>",
            "uv run python -m scripts.grid5000 fetch --run-id <run-id>",
            "```",
            "",
            f"- {documents['fetch_yield']:.0%} of sampled documents were retrieved and parsed in"
            " this run; FinePDF URLs date from 2023 and many are unavailable.",
            "- Only embedded raster images are extracted: vector figures, OCR text and page"
            " renderings are out of scope. Caption layouts outside the explicit-label rule are"
            " dropped, and multi-image pages are paired by reading order.",
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
