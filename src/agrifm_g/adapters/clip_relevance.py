"""Batched CPU-only CLIP screening for confidently irrelevant embedded images."""

from __future__ import annotations

import hashlib
import math
from collections.abc import Sequence
from dataclasses import dataclass, replace
from importlib import import_module
from pathlib import Path
from typing import Protocol

from PIL import Image

from agrifm_g.domain.image_relevance import (
    ImageRelevanceScores,
    is_clear_non_agricultural,
)
from agrifm_g.domain.records import DocumentRecord, ImageRef

DEFAULT_MODEL_ID = "openai/clip-vit-base-patch32"
DEFAULT_MODEL_REVISION = "aba0d2990c5c81a51290b5e895dda8237b39e0be"
PROMPT_VERSION = "agriculture-photo-v1"
DEFAULT_BATCH_SIZE = 32

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
        }
        if not _reference_filter_is_healthy(counts):
            raise RuntimeError(f"CLIP reference-image check failed: {counts}")
        return counts

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

        return {
            "method": "zero-shot CLIP class-group probabilities; uncertain images kept",
            "model_id": self.model_id,
            "model_revision": self.revision,
            "prompt_version": PROMPT_VERSION,
            "batch_size": self.batch_size,
            "cpu_threads": getattr(self.scorer, "num_threads", self.num_threads),
            "max_agriculture_probability_to_drop": MAX_AGRICULTURE_PHOTO_PROBABILITY,
            "min_negative_probability_to_drop": MIN_NEGATIVE_CLASS_PROBABILITY,
        }


def _open_rgb(path: Path) -> Image.Image:
    with Image.open(path) as image:
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
        counts["reference_photos"] > 0
        and counts["reference_photos_kept"] == counts["reference_photos"]
        and counts["reference_noise"] > 0
        and counts["reference_noise_rejected"] / counts["reference_noise"] >= 0.5
    )


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
