"""Fetch PDF bytes over HTTP, with a content-addressed local cache."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

import httpx


class FetchError(RuntimeError):
    """The document could not be retrieved."""


class PdfFetcher(Protocol):
    def fetch(self, url: str) -> bytes: ...


@dataclass(frozen=True, slots=True)
class CachingPdfFetcher:
    """Downloads once per URL; later runs read from `cache_dir`."""

    cache_dir: Path
    timeout: float = 60.0
    max_bytes: int = 32 * 1024 * 1024

    def fetch(self, url: str) -> bytes:
        cached = self.cache_dir / f"{hashlib.sha256(url.encode()).hexdigest()}.pdf"
        if cached.exists():
            return cached.read_bytes()
        payload = self._download(url)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        cached.write_bytes(payload)
        return payload

    def _download(self, url: str) -> bytes:
        try:
            response = httpx.get(url, timeout=self.timeout, follow_redirects=True)
            response.raise_for_status()
        except httpx.HTTPError as error:
            raise FetchError(f"could not fetch {url}: {error}") from error
        payload = response.content
        if not payload:
            raise FetchError(f"empty document at {url}")
        if len(payload) > self.max_bytes:
            raise FetchError(f"document at {url} exceeds {self.max_bytes} bytes")
        return payload
