"""The dataset card, rendered from the build's own numbers."""

from __future__ import annotations

from typing import Any

SCHEMA_ROWS = (
    ("image", "image", "the extracted embedded raster image, decoded by `datasets`"),
    ("doc_id", "string", "FinePDF document id, lowercased and made filesystem-safe"),
    ("agriculture_split", "string", "the mutually exclusive conventional or sustainable split"),
    ("page", "int32", "0-based page where the image was embedded"),
    ("image_index", "int32", "0-based image position within its document"),
    ("width", "int32", "image width in pixels"),
    ("height", "int32", "image height in pixels"),
    ("image_sha256", "string", "content hash, unique across the published rows"),
    ("image_path", "string", "path in the temporary build directory"),
    ("n_colours", "int32", "distinct colours measured on a thumbnail"),
    ("edge_density", "float32", "thumbnail edge share, used only by narrow noise checks"),
    ("agriculture_photo_score", "float32", "CLIP class preference for agricultural photography"),
    ("document_figure_score", "float32", "CLIP class preference for document figures and graphics"),
    ("unrelated_photo_score", "float32", "CLIP class preference for unrelated photographs"),
    ("caption", "string", "optional PDF caption when one was detected"),
    ("source_url", "string", "original PDF URL for provenance"),
    ("pdf_sha256", "string", "hash of the retrieved PDF"),
    ("text", "string", "FinePDF English document text used for classification"),
    ("n_images_in_doc", "int32", "number of retained images from the document"),
    ("extraction_version", "int32", "version of the stored extraction contract"),
)


def render_card(*, repo_id: str, stats: dict[str, Any], n_rows: int, n_shards: int) -> str:
    """Render the reader-facing card from the finished build's own numbers."""
    documents, images = stats["documents"], stats["images"]
    return "\n".join(
        [
            _front_matter(n_rows),
            f"# {repo_id}",
            "",
            "An English-only [FinePDF](https://huggingface.co/datasets/HuggingFaceFW/finepdfs)"
            " image dataset for general agricultural scenes and operations. Each row is one"
            " retained embedded raster image with document text, optional caption, and provenance.",
            "",
            "## Load the splits",
            "",
            "~~~python",
            "from datasets import load_dataset",
            "",
            f'dataset = load_dataset("{repo_id}")',
            'dataset["conventional"][0]["image"]  # PIL.Image',
            'dataset["sustainable"][0]["image"]  # PIL.Image',
            "~~~",
            "",
            "## Contents",
            "",
            _stats_table(documents, images, stats["splits"], n_rows, n_shards),
            "",
            "## Schema",
            "",
            _schema_table(),
            "",
            "## Selection and filtering",
            "",
            "- The input is FinePDF's English `eng_Latn` text. A broad agriculture lexicon"
            " keeps documents worth downloading.",
            "- Each passing document is assigned to the category with more exact matches from"
            " the extended conventional and sustainable agriculture lexicons. Ties and documents"
            " without category evidence are discarded. An image is never duplicated across splits.",
            "- All usable embedded raster images from an accepted document are considered;"
            " captions are optional metadata and never a filter.",
            "- Cheap sanity filters remove invalid, tiny, single-colour, nearly blank,"
            " overwhelmingly flat-colour, extreme-aspect-ratio, and duplicate images."
            " Page-shaped grayscale scans with paper-like backgrounds and dense edges,"
            " plus nearly uniform low-colour placeholders, are also removed.",
            *_visual_filter_description(stats.get("visual_filter")),
            "",
            "## Reproduce and limitations",
            "",
            f"The build sampled {documents['source_shards']} English FinePDF shards with seed"
            f" `{stats['seed']}`. PDFs are fetched from their original URLs and are not"
            " redistributed; `source_url` and `pdf_sha256` preserve provenance, but source"
            " licences are not audited.",
            "",
            "~~~bash",
            "uv run python -m scripts.grid5000 preflight",
            "uv run python -m scripts.grid5000 submit --repo <repo>",
            "uv run python -m scripts.grid5000 fetch --run-id <run-id>",
            "~~~",
            "",
            f"- {documents['fetch_yield']:.0%} of sampled documents were retrieved and parsed in"
            " this run; FinePDF URLs date from 2023 and many are unavailable.",
            "- Only embedded raster images are extracted. Vector figures, OCR-only figures and"
            " linked images are out of scope. The image-level model is a conservative screen, not"
            " a calibrated guarantee; uncertain images are retained, so some irrelevant figures"
            " can remain.",
            "",
            "## Citation",
            "",
            "~~~bibtex",
            "@misc{finepdf_agrifm_g,",
            f"  title  = {{{repo_id}}},",
            "  author = {Flandre, No\\'e},",
            "  year   = {2026},",
            f"  url    = {{https://huggingface.co/datasets/{repo_id}}}",
            "}",
            "~~~",
            "",
        ]
    )


def _front_matter(n_rows: int) -> str:
    return "\n".join(
        [
            "---",
            "pretty_name: FinePDF Agriculture Images",
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
            "  - conventional-agriculture",
            "  - sustainable-agriculture",
            "  - finepdf",
            "  - document-images",
            "configs:",
            "  - config_name: default",
            "    data_files:",
            "      - split: conventional",
            "        path: data/conventional-*.parquet",
            "      - split: sustainable",
            "        path: data/sustainable-*.parquet",
            "---",
            "",
        ]
    )


def _visual_filter_description(visual_filter: dict[str, Any] | None) -> list[str]:
    if not visual_filter:
        return ["- This packaging run did not apply an image-level semantic filter."]
    return [
        "- A pinned, zero-shot CLIP screen compares agricultural photos with document figures"
        " and unrelated photos. It does not read captions or document text.",
        f"- Model: `{visual_filter['model_id']}` at revision"
        f" `{visual_filter['model_revision']}`; prompt set `{visual_filter['prompt_version']}`.",
        "- Only high-confidence negatives are removed: agricultural-photo score at or below"
        f" {visual_filter['max_agriculture_probability_to_drop']:.2f} and a negative-class score"
        f" at or above {visual_filter['min_negative_probability_to_drop']:.2f}. Borderline"
        " predictions stay in the dataset to preserve diversity.",
    ]


def _size_category(n_rows: int) -> str:
    for ceiling, label in ((1_000, "n<1K"), (10_000, "1K<n<10K"), (100_000, "10K<n<100K")):
        if n_rows < ceiling:
            return label
    return "100K<n<1M"


def _stats_table(
    documents: dict,
    images: dict,
    splits: dict[str, dict[str, int]],
    n_rows: int,
    n_shards: int,
) -> str:
    lines = [
        "| | |",
        "| --- | --- |",
        f"| rows (images) | {n_rows} |",
        f"| parquet shards | {n_shards} |",
        f"| documents sampled | {documents['sampled']} |",
        f"| documents retrieved and parsed | {documents['built']} "
        f"({documents['fetch_yield']:.0%}) |",
        f"| documents skipped by broad text gate | {documents['text_gated']} |",
        f"| ambiguous documents skipped | {documents['ambiguous']} |",
        f"| documents contributing images | {documents['with_images']} |",
        f"| image width (min / median / max) | {images['width']['min']} / "
        f"{images['width']['median']} / {images['width']['max']} px |",
        f"| image height (min / median / max) | {images['height']['min']} / "
        f"{images['height']['median']} / {images['height']['max']} px |",
        f"| total pixels | {images['megapixels']} MP |",
        f"| text length (median) | {documents['text_length']['median']} characters |",
    ]
    for split in ("conventional", "sustainable"):
        counts = splits[split]
        lines.append(f"| {split} documents / images | {counts['documents']} / {counts['images']} |")
    lines.extend(
        f"| images dropped — {reason} | {count} |" for reason, count in images["dropped"].items()
    )
    return "\n".join(lines)


def _schema_table() -> str:
    header = ["| field | type | meaning |", "| --- | --- | --- |"]
    return "\n".join(
        header + [f"| `{name}` | {kind} | {meaning} |" for name, kind, meaning in SCHEMA_ROWS]
    )
