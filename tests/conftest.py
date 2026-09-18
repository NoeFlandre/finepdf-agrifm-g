import os
from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"


def pytest_collection_modifyitems(config, items):
    if os.environ.get("AGRIFM_G_INTEGRATION") == "1":
        return
    skip = pytest.mark.skip(reason="set AGRIFM_G_INTEGRATION=1 to run network tests")
    for item in items:
        if "integration" in item.keywords:
            item.add_marker(skip)


@pytest.fixture
def fixtures() -> Path:
    return FIXTURES
