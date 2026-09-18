"""Read document rows from the FinePDF dataset on the Hugging Face Hub.

FinePDF ships as multi-gigabyte parquet shards. The POC reads a single row group
of a single shard with column projection, so a run costs a few tens of megabytes
of range requests instead of a full download.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any, Protocol

DEFAULT_DATASET = "HuggingFaceFW/finepdfs"
DEFAULT_CONFIG = "eng_Latn"
DEFAULT_SPLIT = "train"
DEFAULT_SHARD = "000_00000.parquet"
DEFAULT_ROW_GROUP = 0
COLUMNS = ("id", "url", "text")


@dataclass(frozen=True, slots=True)
class FinePdfRow:
    """The three FinePDF fields the POC needs."""

    doc_id: str
    url: str
    text: str


class RowSource(Protocol):
    """The corpus, seen as an addressable sequence of rows."""

    def total(self) -> int: ...

    def rows(self, indices: Sequence[int]) -> list[FinePdfRow]: ...


@dataclass(eq=False)
class ParquetRowSource:
    """Live FinePDF access, scoped to one row group (the POC's sampling window)."""

    dataset: str = DEFAULT_DATASET
    config: str = DEFAULT_CONFIG
    split: str = DEFAULT_SPLIT
    shard: str = DEFAULT_SHARD
    row_group: int = DEFAULT_ROW_GROUP
    _cache: list[FinePdfRow] = field(default_factory=list, repr=False)

    @property
    def path(self) -> str:
        return f"datasets/{self.dataset}/data/{self.config}/{self.split}/{self.shard}"

    def total(self) -> int:
        return len(self._window())

    def rows(self, indices: Sequence[int]) -> list[FinePdfRow]:
        window = self._window()
        return [window[index] for index in indices]

    def _window(self) -> list[FinePdfRow]:
        if not self._cache:
            self._cache = [_to_row(item) for item in self._read_row_group()]
        return self._cache

    def _read_row_group(self) -> list[dict[str, Any]]:
        import pyarrow.parquet as pq
        from huggingface_hub import HfFileSystem

        with HfFileSystem().open(self.path, "rb") as handle:
            table = pq.ParquetFile(handle).read_row_group(self.row_group, columns=list(COLUMNS))
        return table.to_pylist()


def _to_row(item: dict[str, Any]) -> FinePdfRow:
    return FinePdfRow(doc_id=item["id"], url=item["url"], text=item["text"])
