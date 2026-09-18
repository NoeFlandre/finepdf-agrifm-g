"""Push a built dataset to a Hugging Face dataset repository."""

from __future__ import annotations

import os
from pathlib import Path


class PublishError(RuntimeError):
    """The dataset could not be published."""


def publish_dataset(dataset_dir: Path, repo_id: str, *, dry_run: bool = True) -> str:
    """Upload `dataset_dir` to `repo_id`. Returns the repository URL.

    The token is read from the environment only; nothing is ever written to the repo.
    """
    url = f"https://huggingface.co/datasets/{repo_id}"
    if dry_run:
        return url
    token = os.environ.get("HF_TOKEN")
    if not token:
        raise PublishError("HF_TOKEN is not set")
    from huggingface_hub import HfApi

    api = HfApi(token=token)
    api.create_repo(repo_id=repo_id, repo_type="dataset", private=False, exist_ok=True)
    # delete_patterns makes the repo mirror the folder: an earlier layout is removed
    # rather than left behind alongside the new one.
    api.upload_folder(
        repo_id=repo_id,
        repo_type="dataset",
        folder_path=str(dataset_dir),
        delete_patterns="*",
        ignore_patterns=[".DS_Store", "**/.DS_Store"],
    )
    return url
