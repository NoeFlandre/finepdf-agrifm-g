"""Fetch PDF bytes over HTTP, with a content-addressed local cache."""

from __future__ import annotations

import hashlib
import os
import threading
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
    """Downloads once per URL; later runs read from `cache_dir`.

    Failures are remembered too, in a `.gone` marker beside where the PDF would sit. FinePDF
    URLs were crawled in 2023 and about 96% of them no longer answer, so without this a
    rebuild spends hours re-timing-out on the same dead hosts — which is most of what a
    rebuild did before this existed. A marker records only that the URL failed, never why,
    and deleting `cache_dir` restores the old behaviour.

    Safe to share across threads: entries are written to a per-process temporary file and
    renamed into place, so a concurrent reader never sees a half-written PDF.
    """

    cache_dir: Path
    timeout: float = 60.0
    max_bytes: int = 32 * 1024 * 1024
    remember_failures: bool = True

    def fetch(self, url: str) -> bytes:
        remembered = self._remembered(url)
        if remembered is not None:
            return remembered
        try:
            payload = self._download(url)
        except FetchError:
            if self.remember_failures:
                self._write(self._entry(url, ".gone"), b"")
            raise
        self._write(self._entry(url, ".pdf"), payload)
        return payload

    def _remembered(self, url: str) -> bytes | None:
        """What an earlier run already learned about this URL, if anything."""
        cached = self._entry(url, ".pdf")
        if cached.exists():
            return cached.read_bytes()
        if self.remember_failures and self._entry(url, ".gone").exists():
            raise FetchError(f"{url} failed on an earlier run (cached)")
        return None

    def _entry(self, url: str, suffix: str) -> Path:
        return self.cache_dir / f"{hashlib.sha256(url.encode()).hexdigest()}{suffix}"

    def _write(self, target: Path, payload: bytes) -> None:
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        pending = target.with_suffix(f".{os.getpid()}.{threading.get_ident()}.part")
        pending.write_bytes(payload)
        pending.replace(target)

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
