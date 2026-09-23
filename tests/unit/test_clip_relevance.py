import io
from contextlib import nullcontext
from dataclasses import replace
from types import SimpleNamespace
from unittest.mock import MagicMock, Mock

import pytest
from PIL import Image

from agrifm_g.adapters import clip_relevance
from agrifm_g.adapters.clip_relevance import PROMPTS, ClipImageRelevanceFilter
from agrifm_g.domain.image_relevance import ImageRelevanceScores
from agrifm_g.domain.records import DocumentRecord, ImageRef


class FakeScorer:
    def __init__(self, scores):
        self.scores = iter(scores)
        self.batch_sizes = []

    def score(self, images):
        self.batch_sizes.append(len(images))
        return [next(self.scores) for _ in images]


class ShortScorer:
    def score(self, images):
        del images
        return []


def a_record(image_paths):
    return DocumentRecord(
        doc_id="doc-1",
        source_url="https://example.org/a.pdf",
        pdf_path="pdfs/doc-1.pdf",
        pdf_sha256="a" * 64,
        text="tractor",
        agriculture_split="conventional",
        images=tuple(
            ImageRef(
                path=path,
                page=0,
                width=8,
                height=8,
                format="png",
                sha256=str(index) * 64,
                n_colours=64,
                dominant_colour_share=0.02,
                near_white_share=0.02,
                edge_density=0.2,
            )
            for index, path in enumerate(image_paths, 1)
        ),
    )


def write_image(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    buffer = io.BytesIO()
    Image.new("RGB", (8, 8), (index_colour(path), 100, 120)).save(buffer, format="PNG")
    path.write_bytes(buffer.getvalue())


def index_colour(path):
    return sum(path.name.encode("utf-8")) % 256


def test_filter_scores_in_batches_drops_clear_negatives_and_keeps_uncertain_images(tmp_path):
    build = tmp_path / "build"
    paths = ("images/doc-1/001.png", "images/doc-1/002.png")
    for relative in paths:
        write_image(build / relative)
    record = a_record(paths)
    scorer = FakeScorer(
        [
            ImageRelevanceScores(0.03, 0.85, 0.12),
            ImageRelevanceScores(0.18, 0.72, 0.10),
        ]
    )
    image_filter = ClipImageRelevanceFilter(scorer=scorer, batch_size=1)

    result = image_filter.apply([record], build)

    assert result.dropped == 1
    assert len(result.records[0].images) == 1
    kept = result.records[0].images[0]
    assert kept.agriculture_photo_score == 0.18
    assert kept.document_figure_score == 0.72
    assert kept.unrelated_photo_score == 0.1
    assert scorer.batch_sizes == [1, 1]
    assert result.metadata["prompt_version"] == "agriculture-photo-v1"


def test_filter_fails_if_scorer_loses_an_image(tmp_path):
    relative = "images/doc-1/001.png"
    write_image(tmp_path / relative)
    image_filter = ClipImageRelevanceFilter(scorer=ShortScorer())

    with pytest.raises(RuntimeError, match="wrong number"):
        image_filter.apply([a_record((relative,))], tmp_path)


def test_model_loader_pins_safe_weights_and_runs_on_cpu(monkeypatch):
    model = Mock()
    model.to.return_value = model
    processor = Mock()
    torch = Mock()
    torch.get_num_threads.return_value = 4
    model_factory = Mock(return_value=model)
    processor_factory = Mock(return_value=processor)
    modules = {
        "torch": torch,
        "transformers": SimpleNamespace(
            CLIPModel=SimpleNamespace(from_pretrained=model_factory),
            CLIPProcessor=SimpleNamespace(from_pretrained=processor_factory),
        ),
    }
    monkeypatch.setattr(clip_relevance, "import_module", lambda name: modules[name])

    scorer = clip_relevance._load_scorer("org/model", "a" * 40, 4)

    assert isinstance(scorer, clip_relevance._ClipScorer)
    torch.set_num_threads.assert_called_once_with(4)
    model_factory.assert_called_once_with("org/model", revision="a" * 40, use_safetensors=True)
    processor_factory.assert_called_once_with("org/model", revision="a" * 40)
    model.to.assert_called_once_with("cpu")
    model.eval.assert_called_once_with()


def test_clip_scorer_batches_prompt_groups_into_three_probabilities():
    model = MagicMock()
    model.return_value = SimpleNamespace(logits_per_image=MagicMock())
    processor = MagicMock(return_value={"pixel_values": "batch"})
    probabilities = MagicMock()
    probabilities.tolist.return_value = [[0.8, 0.1, 0.1], [0.03, 0.85, 0.12]]
    torch = MagicMock()
    torch.inference_mode.return_value = nullcontext()
    torch.softmax.return_value = probabilities
    images = [MagicMock(spec=Image.Image), MagicMock(spec=Image.Image)]
    scorer = clip_relevance._ClipScorer(model, processor, torch)

    scores = scorer.score(images)

    processor.assert_called_once_with(
        text=list(PROMPTS), images=images, return_tensors="pt", padding=True
    )
    assert torch.logsumexp.call_count == 3
    stack_args, stack_kwargs = torch.stack.call_args
    assert len(stack_args[0]) == 3
    assert stack_kwargs == {"dim": 1}
    torch.softmax.assert_called_once_with(torch.stack.return_value, dim=1)
    assert scores == [ImageRelevanceScores(0.8, 0.1, 0.1), ImageRelevanceScores(0.03, 0.85, 0.12)]


def test_filter_does_not_change_caption_or_document_split(tmp_path):
    relative = "images/doc-1/001.png"
    write_image(tmp_path / relative)
    record = replace(
        a_record((relative,)),
        images=(replace(a_record((relative,)).images[0], caption="Figure 1. tractor"),),
    )
    image_filter = ClipImageRelevanceFilter(
        scorer=FakeScorer([ImageRelevanceScores(0.8, 0.1, 0.1)])
    )

    result = image_filter.apply([record], tmp_path)

    assert result.records[0].agriculture_split == "conventional"
    assert result.records[0].images[0].caption == "Figure 1. tractor"


def test_reference_audit_requires_photo_recall_and_basic_noise_rejection(tmp_path):
    for label in ("keep", "reject"):
        for index in range(2):
            write_image(tmp_path / label / f"{index}.png")
    photo = ImageRelevanceScores(0.9, 0.05, 0.05)
    noise = ImageRelevanceScores(0.03, 0.85, 0.12)
    image_filter = ClipImageRelevanceFilter(scorer=FakeScorer([photo, photo, noise, noise]))

    counts = image_filter.audit_reference_examples(tmp_path)

    assert counts == {
        "reference_photos": 2,
        "reference_photos_kept": 2,
        "reference_noise": 2,
        "reference_noise_rejected": 2,
    }


def test_reference_audit_fails_before_build_when_it_loses_a_known_photo(tmp_path):
    for label in ("keep", "reject"):
        for index in range(2):
            write_image(tmp_path / label / f"{index}.png")
    noise = ImageRelevanceScores(0.03, 0.85, 0.12)
    photo = ImageRelevanceScores(0.9, 0.05, 0.05)
    image_filter = ClipImageRelevanceFilter(scorer=FakeScorer([noise, photo, noise, noise]))

    with pytest.raises(RuntimeError, match="reference-image check failed"):
        image_filter.audit_reference_examples(tmp_path)
