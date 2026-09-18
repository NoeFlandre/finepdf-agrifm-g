"""Network-touching checks. Run with AGRIFM_G_INTEGRATION=1."""

import pytest

from agrifm_g.adapters.finepdf import ParquetRowSource
from agrifm_g.adapters.pdfsource import CachingPdfFetcher, FetchError

pytestmark = pytest.mark.integration


def test_a_real_finepdf_row_has_the_fields_we_rely_on():
    row = ParquetRowSource().rows([0])[0]
    assert row.doc_id and row.url.startswith("http") and row.text


def test_fetching_caches_the_document(tmp_path):
    fetcher = CachingPdfFetcher(cache_dir=tmp_path)
    url = ParquetRowSource().rows([0])[0].url
    first = fetcher.fetch(url)
    assert len(list(tmp_path.glob("*.pdf"))) == 1
    assert fetcher.fetch(url) == first


def test_a_missing_document_raises_a_typed_error(tmp_path):
    fetcher = CachingPdfFetcher(cache_dir=tmp_path)
    with pytest.raises(FetchError):
        fetcher.fetch("https://huggingface.co/definitely-not-a-real-document.pdf")
