import httpx
import pytest

from agrifm_g.adapters.pdfsource import CachingPdfFetcher, FetchError


class FakeResponse:
    def __init__(self, content=b"%PDF-1.4 ok", error=None):
        self.content = content
        self._error = error

    def raise_for_status(self):
        if self._error:
            raise self._error


class FakeGet:
    """A stand-in for `httpx.get` that records calls and returns a scripted response."""

    def __init__(self):
        self.response = FakeResponse()
        self.calls = []

    def __call__(self, url, **kwargs):
        self.calls.append(url)
        return self.response


@pytest.fixture
def get(monkeypatch):
    fake_get = FakeGet()
    monkeypatch.setattr(httpx, "get", fake_get)
    return fake_get, fake_get.calls


def test_a_document_is_downloaded_once_and_then_cached(tmp_path, get):
    fake_get, calls = get
    fetcher = CachingPdfFetcher(cache_dir=tmp_path)
    assert fetcher.fetch("https://example.org/a.pdf") == b"%PDF-1.4 ok"
    assert fetcher.fetch("https://example.org/a.pdf") == b"%PDF-1.4 ok"
    assert len(calls) == 1


def test_different_urls_get_different_cache_entries(tmp_path, get):
    fetcher = CachingPdfFetcher(cache_dir=tmp_path)
    fetcher.fetch("https://example.org/a.pdf")
    fetcher.fetch("https://example.org/b.pdf")
    assert len(list(tmp_path.glob("*.pdf"))) == 2


def test_a_transport_failure_becomes_a_typed_error(tmp_path, get):
    fake_get, _ = get
    fake_get.response = FakeResponse(
        error=httpx.HTTPStatusError(
            "404", request=httpx.Request("GET", "https://example.org"), response=httpx.Response(404)
        )
    )
    with pytest.raises(FetchError):
        CachingPdfFetcher(cache_dir=tmp_path).fetch("https://example.org/missing.pdf")


def test_an_empty_document_is_rejected(tmp_path, get):
    fake_get, _ = get
    fake_get.response = FakeResponse(content=b"")
    with pytest.raises(FetchError):
        CachingPdfFetcher(cache_dir=tmp_path).fetch("https://example.org/empty.pdf")


def test_an_oversized_document_is_rejected(tmp_path, get):
    fake_get, _ = get
    fake_get.response = FakeResponse(content=b"x" * 100)
    with pytest.raises(FetchError):
        CachingPdfFetcher(cache_dir=tmp_path, max_bytes=10).fetch("https://example.org/big.pdf")
