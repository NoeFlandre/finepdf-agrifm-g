"""Batched CPU-only CLIP screening for confidently irrelevant embedded images."""

from __future__ import annotations

import hashlib
import math
from collections.abc import Sequence
from dataclasses import dataclass, replace
from importlib import import_module
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Protocol

from PIL import Image, ImageDraw

from agrifm_g.domain.image_relevance import (
    ImageRelevanceScores,
    is_clear_non_agricultural,
)
from agrifm_g.domain.records import DocumentRecord, ImageRef

DEFAULT_MODEL_ID = "openai/clip-vit-base-patch32"
DEFAULT_MODEL_REVISION = "aba0d2990c5c81a51290b5e895dda8237b39e0be"
PROMPT_VERSION = "agriculture-photo-v1"
PREPROCESS_VERSION = "bicubic-edge-448-v1"
DEFAULT_BATCH_SIZE = 32
CLIP_CROP_EDGE = 224
MAX_CLIP_PREPROCESS_EDGE = 2 * CLIP_CROP_EDGE
SYNTHETIC_DOCUMENT_TYPES = ("chart", "table", "map")

AGRICULTURE_PROMPTS = (
    "a photograph of a tractor, tiller, combine, or other farm machine at work",
    "a photograph of farmers working in a crop field",
    "a photograph of crop rows, an orchard, vineyard, or pasture",
    "a photograph of farm buildings, barns, silos, or agricultural equipment",
    "a photograph of livestock, poultry, or aquaculture on a farm",
    "a photograph of permaculture, agroforestry, or regenerative agriculture",
    "a photograph of a greenhouse, hydroponic farm, or aquaponics system",
    "a close-up photograph of crops, leaves, fruit, or harvested produce",
    "a photograph of irrigation, planting, soil preparation, or harvesting",
)
DOCUMENT_PROMPTS = (
    "a scanned page of text from a scientific paper or report",
    "a scientific chart, graph, plot, or numerical table",
    "a data table with rows, columns, and written values",
    "a map, schematic, or technical diagram in a document",
    "an infographic, labelled figure, or line drawing",
    "a screenshot of a computer or mobile phone display",
    "a page of text, forms, or printed paperwork",
    "a document page photographed or scanned as one image",
    "a logo, icon, symbol, or decorative graphic",
)
UNRELATED_PROMPTS = (
    "a photograph of a scene unrelated to farming or agriculture",
    "a portrait photograph of a person not doing farm work",
    "a photograph of machinery or vehicles unrelated to a farm",
    "a photograph of a city street or indoor office",
    "a plain colour swatch, blank image, or empty placeholder",
    "a signature or handwritten mark on a blank page",
    "a photograph of a household object unrelated to agriculture",
    "a photograph of a generic landscape without agricultural activity",
    "an abstract shape or nearly single-colour image",
)
PROMPTS = (*AGRICULTURE_PROMPTS, *DOCUMENT_PROMPTS, *UNRELATED_PROMPTS)
_GROUP_SLICES = (
    slice(0, len(AGRICULTURE_PROMPTS)),
    slice(len(AGRICULTURE_PROMPTS), len(AGRICULTURE_PROMPTS) + len(DOCUMENT_PROMPTS)),
    slice(len(AGRICULTURE_PROMPTS) + len(DOCUMENT_PROMPTS), len(PROMPTS)),
)


class ImageScorer(Protocol):
    """Model boundary; tests can inject deterministic scores without loading a model."""

    def score(self, images: Sequence[Image.Image]) -> Sequence[ImageRelevanceScores]: ...


@dataclass(frozen=True, slots=True)
class FilterResult:
    records: list[DocumentRecord]
    dropped: int
    metadata: dict[str, object]


class ClipImageRelevanceFilter:
    """Score unique surviving images in small batches and keep every uncertain result."""

    def __init__(
        self,
        *,
        model_id: str = DEFAULT_MODEL_ID,
        revision: str = DEFAULT_MODEL_REVISION,
        batch_size: int = DEFAULT_BATCH_SIZE,
        num_threads: int = 16,
        scorer: ImageScorer | None = None,
    ) -> None:
        if batch_size < 1 or num_threads < 1:
            raise ValueError("batch_size and num_threads must be positive")
        self.model_id = model_id
        self.revision = revision
        self.batch_size = batch_size
        self.num_threads = num_threads
        self.scorer = scorer
        self.reference_audit: dict[str, int] | None = None

    def apply(self, records: Sequence[DocumentRecord], build_dir: Path) -> FilterResult:
        """Attach model scores and remove only high-confidence negative predictions."""
        images = [image for record in records for image in record.images]
        scores = self._score_images(images, build_dir)
        dropped = 0
        updated = []
        for record in records:
            filtered, rejected = _filter_record(record, scores)
            updated.append(filtered)
            dropped += rejected
        metadata = {
            **self.metadata,
            "scored_images": len(images),
            "dropped_images": dropped,
        }
        return FilterResult(updated, dropped, metadata)

    def audit_reference_examples(self, reference_dir: Path) -> dict[str, int]:
        """Fail early if the filter loses reference photos or cannot reject clear noise."""
        keep_records = _reference_records(reference_dir, "keep")
        reject_records = _reference_records(reference_dir, "reject")
        keep = self.apply(keep_records, reference_dir)
        reject = self.apply(reject_records, reference_dir)
        counts = {
            "reference_photos": sum(record.n_images for record in keep_records),
            "reference_photos_kept": sum(record.n_images for record in keep.records),
            "reference_noise": sum(record.n_images for record in reject_records),
            "reference_noise_rejected": reject.dropped,
            **self._audit_synthetic_documents(),
        }
        if not _reference_filter_is_healthy(counts):
            raise RuntimeError(f"CLIP reference-image check failed: {counts}")
        self.reference_audit = counts
        return counts

    def _audit_synthetic_documents(self) -> dict[str, int]:
        with TemporaryDirectory(prefix="agrifm-g-image-smoke-") as scratch_dir:
            scratch = Path(scratch_dir)
            records = _synthetic_document_records(scratch)
            result = self.apply(records, scratch)
        return {
            f"synthetic_{kind}_rejected": int(record.n_images == 0)
            for kind, record in zip(SYNTHETIC_DOCUMENT_TYPES, result.records, strict=True)
        }

    def _score_images(
        self,
        images: Sequence[ImageRef],
        build_dir: Path,
    ) -> dict[str, ImageRelevanceScores]:
        scores: dict[str, ImageRelevanceScores] = {}
        if not images:
            return scores
        scorer = self._get_scorer()
        for start in range(0, len(images), self.batch_size):
            batch = images[start : start + self.batch_size]
            scores.update(_score_batch(batch, build_dir, scorer))
        return scores

    def _get_scorer(self) -> ImageScorer:
        if self.scorer is None:
            self.scorer = _load_scorer(self.model_id, self.revision, self.num_threads)
        return self.scorer

    @property
    def metadata(self) -> dict[str, object]:
        from agrifm_g.domain.image_relevance import (
            MAX_AGRICULTURE_PHOTO_PROBABILITY,
            MIN_NEGATIVE_CLASS_PROBABILITY,
        )

        metadata = {
            "method": "zero-shot CLIP class-group probabilities; uncertain images kept",
            "model_id": self.model_id,
            "model_revision": self.revision,
            "prompt_version": PROMPT_VERSION,
            "preprocess_version": PREPROCESS_VERSION,
            "max_preprocess_edge": MAX_CLIP_PREPROCESS_EDGE,
            "batch_size": self.batch_size,
            "cpu_threads": getattr(self.scorer, "num_threads", self.num_threads),
            "max_agriculture_probability_to_drop": MAX_AGRICULTURE_PHOTO_PROBABILITY,
            "min_negative_probability_to_drop": MIN_NEGATIVE_CLASS_PROBABILITY,
        }
        if self.reference_audit is not None:
            metadata["reference_audit"] = dict(self.reference_audit)
        return metadata


def _open_rgb(path: Path) -> Image.Image:
    with Image.open(path) as image:
        image.thumbnail(
            (MAX_CLIP_PREPROCESS_EDGE, MAX_CLIP_PREPROCESS_EDGE),
            Image.Resampling.BICUBIC,
        )
        return image.convert("RGB")


def _filter_record(
    record: DocumentRecord,
    scores: dict[str, ImageRelevanceScores],
) -> tuple[DocumentRecord, int]:
    kept = []
    dropped = 0
    for image in record.images:
        score = scores[image.path]
        if is_clear_non_agricultural(score):
            dropped += 1
            continue
        kept.append(
            replace(
                image,
                agriculture_photo_score=round(score.agriculture_photo, 6),
                document_figure_score=round(score.document_figure, 6),
                unrelated_photo_score=round(score.unrelated_photo, 6),
            )
        )
    return replace(record, images=tuple(kept)), dropped


def _score_batch(
    batch: Sequence[ImageRef],
    build_dir: Path,
    scorer: ImageScorer,
) -> dict[str, ImageRelevanceScores]:
    pictures = [_open_rgb(build_dir / image.path) for image in batch]
    try:
        batch_scores = scorer.score(pictures)
    finally:
        for picture in pictures:
            picture.close()
    if len(batch_scores) != len(batch):
        raise RuntimeError("image scorer returned the wrong number of results")
    return dict((image.path, score) for image, score in zip(batch, batch_scores, strict=True))


def _reference_filter_is_healthy(counts: dict[str, int]) -> bool:
    return (
        _reference_photos_are_healthy(counts)
        and _reference_noise_is_healthy(counts)
        and _synthetic_document_types_are_rejected(counts)
    )


def _reference_photos_are_healthy(counts: dict[str, int]) -> bool:
    return (
        counts["reference_photos"] > 0
        and counts["reference_photos_kept"] == counts["reference_photos"]
    )


def _reference_noise_is_healthy(counts: dict[str, int]) -> bool:
    return (
        counts["reference_noise"] > 0
        and counts["reference_noise_rejected"] / counts["reference_noise"] >= 0.5
    )


def _synthetic_document_types_are_rejected(counts: dict[str, int]) -> bool:
    return all(counts[f"synthetic_{kind}_rejected"] == 1 for kind in SYNTHETIC_DOCUMENT_TYPES)


def _synthetic_document_records(directory: Path) -> list[DocumentRecord]:
    draw_examples = (
        ("chart", _draw_synthetic_chart),
        ("table", _draw_synthetic_table),
        ("map", _draw_synthetic_map),
    )
    records = []
    for kind, draw_example in draw_examples:
        image = Image.new("RGB", (448, 448), "white")
        draw_example(ImageDraw.Draw(image))
        path = directory / f"{kind}.png"
        image.save(path)
        image.close()
        image_ref = ImageRef(
            path=path.name,
            page=0,
            width=448,
            height=448,
            format="png",
            sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
            n_colours=30000,
            dominant_colour_share=0.0,
            near_white_share=0.0,
            edge_density=0.2,
        )
        records.append(
            DocumentRecord(
                doc_id=f"reference-synthetic-{kind}",
                source_url=f"reference://synthetic/{kind}",
                pdf_path=f"reference-{kind}.pdf",
                pdf_sha256="0" * 64,
                text="",
                images=(image_ref,),
                agriculture_split="conventional",
            )
        )
    return records


def _draw_synthetic_chart(draw: ImageDraw.ImageDraw) -> None:
    for coordinate in range(80, 401, 64):
        draw.line((coordinate, 72, coordinate, 368), fill=(215, 215, 215), width=1)
        draw.line((72, coordinate, 400, coordinate), fill=(215, 215, 215), width=1)
    draw.line((72, 72, 72, 368, 400, 368), fill=(20, 20, 20), width=3)
    points = [(96, 320), (160, 280), (224, 298), (288, 190), (352, 120)]
    draw.line(points, fill=(25, 90, 180), width=6)
    for x, y in points:
        draw.ellipse((x - 7, y - 7, x + 7, y + 7), fill=(25, 90, 180))
    draw.text((150, 28), "CHART", fill=(20, 20, 20))


def _draw_synthetic_table(draw: ImageDraw.ImageDraw) -> None:
    left, top, cell_width, cell_height = 48, 64, 88, 48
    for row in range(7):
        for column in range(4):
            x = left + column * cell_width
            y = top + row * cell_height
            draw.rectangle((x, y, x + cell_width, y + cell_height), outline=(30, 30, 30))
            if row and column:
                draw.text((x + 25, y + 17), str(row * column * 3), fill=(20, 20, 20))
    draw.text((170, 28), "DATA TABLE", fill=(20, 20, 20))


def _draw_synthetic_map(draw: ImageDraw.ImageDraw) -> None:
    outline = [
        (84, 112),
        (170, 72),
        (230, 105),
        (316, 82),
        (376, 154),
        (348, 246),
        (384, 316),
        (292, 368),
        (220, 340),
        (142, 382),
        (76, 300),
        (96, 212),
        (64, 168),
        (84, 112),
    ]
    draw.line(outline, fill=(30, 30, 30), width=4)
    draw.line([(170, 72), (186, 162), (142, 212), (220, 340)], fill=(90, 90, 90), width=3)
    draw.line([(230, 105), (252, 184), (348, 246)], fill=(90, 90, 90), width=3)
    draw.line([(96, 212), (186, 162), (252, 184), (316, 82)], fill=(90, 90, 90), width=3)
    draw.rectangle((288, 312, 380, 384), outline=(30, 30, 30), width=2)
    draw.text((308, 322), "LEGEND", fill=(20, 20, 20))
    draw.text((196, 28), "MAP", fill=(20, 20, 20))


def _reference_records(reference_dir: Path, label: str) -> list[DocumentRecord]:
    paths = sorted(
        path
        for path in (reference_dir / label).iterdir()
        if path.is_file() and path.suffix.lower() in {".jpg", ".jpeg", ".png"}
    )
    records = []
    for path in paths:
        with Image.open(path) as image:
            width, height = image.size
        relative = path.relative_to(reference_dir).as_posix()
        sha256 = hashlib.sha256(path.read_bytes()).hexdigest()
        image_ref = ImageRef(
            path=relative,
            page=0,
            width=width,
            height=height,
            format=path.suffix.lstrip("."),
            sha256=sha256,
            n_colours=30000,
            dominant_colour_share=0.0,
            near_white_share=0.0,
            edge_density=0.2,
        )
        records.append(
            DocumentRecord(
                doc_id=f"reference-{label}-{path.stem}",
                source_url="reference://docs/images",
                pdf_path="reference.pdf",
                pdf_sha256="0" * 64,
                text="",
                images=(image_ref,),
                agriculture_split="conventional",
            )
        )
    return records


def _load_scorer(model_id: str, revision: str, num_threads: int) -> ImageScorer:
    try:
        torch = import_module("torch")
        transformers = import_module("transformers")
    except ImportError as error:
        raise RuntimeError(
            "visual relevance filtering requires the locked 'vision' dependencies"
        ) from error
    torch.set_num_threads(num_threads)
    model = transformers.CLIPModel.from_pretrained(
        model_id,
        revision=revision,
        use_safetensors=True,
    ).to("cpu")
    model.eval()
    processor = transformers.CLIPProcessor.from_pretrained(model_id, revision=revision)
    return _ClipScorer(model, processor, torch)


class _ClipScorer:
    def __init__(self, model, processor, torch) -> None:  # noqa: ANN001
        self.model = model
        self.processor = processor
        self.torch = torch
        self.num_threads = torch.get_num_threads()

    def score(self, images: Sequence[Image.Image]) -> list[ImageRelevanceScores]:
        inputs = self.processor(
            text=list(PROMPTS),
            images=list(images),
            return_tensors="pt",
            padding=True,
        )
        with self.torch.inference_mode():
            logits = self.model(**inputs).logits_per_image
            group_logits = self.torch.stack(
                [
                    self.torch.logsumexp(logits[:, group], dim=1)
                    - math.log(group.stop - group.start)
                    for group in _GROUP_SLICES
                ],
                dim=1,
            )
            probabilities = self.torch.softmax(group_logits, dim=1).tolist()
        return [ImageRelevanceScores(*map(float, row)) for row in probabilities]
