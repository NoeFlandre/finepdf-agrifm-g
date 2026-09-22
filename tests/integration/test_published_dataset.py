"""Check the live published dataset the way a user would load it.

Network-gated: AGRIFM_G_INTEGRATION=1. The repo can be overridden with AGRIFM_G_REPO.
"""

import os

import pytest

from agrifm_g.adapters.packaging import features

pytestmark = pytest.mark.integration

REPO = os.environ.get("AGRIFM_G_REPO", "NoeFlandre/finepdf-agrifm-g")


@pytest.fixture(scope="module")
def dataset():
    from datasets import load_dataset

    return load_dataset(REPO)


@pytest.mark.parametrize("split", ("conventional", "sustainable"))
def test_the_published_schema_matches_what_we_declare(dataset, split):
    assert dict(dataset[split].features) == dict(features())


@pytest.mark.parametrize("split", ("conventional", "sustainable"))
def test_the_dataset_is_not_empty(dataset, split):
    assert dataset[split].num_rows > 0


@pytest.mark.parametrize("split", ("conventional", "sustainable"))
def test_a_row_decodes_to_the_stored_dimensions(dataset, split):
    row = dataset[split][0]
    assert row["image"].size == (row["width"], row["height"])
    assert row["source_url"].startswith("http")
    assert row["agriculture_split"] == split


def test_image_hashes_are_unique_across_the_dataset(dataset):
    hashes = dataset["conventional"]["image_sha256"] + dataset["sustainable"]["image_sha256"]
    assert len(set(hashes)) == len(hashes)
