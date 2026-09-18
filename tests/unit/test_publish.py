import pytest

from agrifm_g.adapters.publish import PublishError, publish_dataset


def test_a_dry_run_reports_the_target_and_uploads_nothing(tmp_path):
    assert publish_dataset(tmp_path, "me/thing") == "https://huggingface.co/datasets/me/thing"


def test_publishing_without_a_token_fails_before_any_upload(tmp_path, monkeypatch):
    monkeypatch.delenv("HF_TOKEN", raising=False)
    with pytest.raises(PublishError):
        publish_dataset(tmp_path, "me/thing", dry_run=False)
