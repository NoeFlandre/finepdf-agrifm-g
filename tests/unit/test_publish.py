import pytest

from agrifm_g.adapters.publish import PublishError, publish_dataset


def test_a_dry_run_reports_the_target_and_uploads_nothing(tmp_path):
    assert publish_dataset(tmp_path, "me/thing") == "https://huggingface.co/datasets/me/thing"


def test_publishing_without_a_token_fails_before_any_upload(tmp_path, monkeypatch):
    monkeypatch.delenv("HF_TOKEN", raising=False)
    with pytest.raises(PublishError):
        publish_dataset(tmp_path, "me/thing", dry_run=False)


def test_the_card_states_the_size_and_the_poc_caveat(tmp_path):
    from agrifm_g.adapters.publish import write_dataset_card
    from agrifm_g.domain.records import DocumentRecord

    records = [
        DocumentRecord(doc_id="d1", source_url="u", pdf_path="p", text="t", images=()),
    ]
    card = write_dataset_card(tmp_path, "me/thing", records, manifest_seed=7)
    assert card.exists()
    text = card.read_text()
    assert "1 documents" in text
    assert "proof of concept" in text.lower()
    assert "seed 7" in text
