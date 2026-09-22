from pathlib import Path

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


def test_the_cache_entry_appears_atomically(tmp_path, monkeypatch):
    """A partly written PDF must never be visible to a concurrent reader."""
    fetcher = CachingPdfFetcher(cache_dir=tmp_path)
    seen: list[list[str]] = []

    real_replace = Path.replace

    def spy(self, target):
        seen.append(sorted(p.suffix for p in tmp_path.iterdir()))
        return real_replace(self, target)

    monkeypatch.setattr(Path, "replace", spy)
    monkeypatch.setattr(httpx, "get", lambda url, **kwargs: FakeResponse(b"%PDF-1.4 body"))

    assert fetcher.fetch("https://example.org/a.pdf") == b"%PDF-1.4 body"
    assert seen == [[".part"]], "the final name must not exist before the rename"
    assert [p.suffix for p in tmp_path.iterdir()] == [".pdf"]


def test_a_dead_url_is_not_retried_on_a_later_run(tmp_path, get):
    """96% of FinePDF URLs are dead; re-timing-out on them is what makes rebuilds cost hours."""
    fake_get, calls = get
    fake_get.response = FakeResponse(error=httpx.HTTPError("410 gone"))
    fetcher = CachingPdfFetcher(cache_dir=tmp_path)

    with pytest.raises(FetchError):
        fetcher.fetch("https://example.org/dead.pdf")
    with pytest.raises(FetchError, match="earlier run"):
        fetcher.fetch("https://example.org/dead.pdf")

    assert calls == ["https://example.org/dead.pdf"], "the dead URL was fetched twice"


def test_remembering_failures_can_be_turned_off(tmp_path, get):
    fake_get, calls = get
    fake_get.response = FakeResponse(error=httpx.HTTPError("timeout"))
    fetcher = CachingPdfFetcher(cache_dir=tmp_path, remember_failures=False)

    for _ in range(2):
        with pytest.raises(FetchError):
            fetcher.fetch("https://example.org/flaky.pdf")

    assert len(calls) == 2


def test_a_failure_marker_never_shadows_a_real_download(tmp_path, get):
    _, calls = get
    fetcher = CachingPdfFetcher(cache_dir=tmp_path)

    assert fetcher.fetch("https://example.org/ok.pdf") == b"%PDF-1.4 ok"
    assert not list(tmp_path.glob("*.gone"))
