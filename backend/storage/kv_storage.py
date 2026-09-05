"""
Key-value storage abstractions and JSON-backed implementation.
"""
import os
from dataclasses import dataclass
from typing import Generic, TypedDict, TypeVar

from ..config import settings as parameter
from ..utils.base import load_json, logger, write_json


class TextChunkSchema(TypedDict):
    tokens: int
    content: str
    full_doc_id: str
    chunk_order_index: int
    file_name: str  # original source document name — e.g. "Q3_report.pdf"

T = TypeVar("T")


@dataclass
class StorageNameSpace:
    namespace: str
    storage_dir: str = None

    async def index_done_callback(self):
        pass

    async def query_done_callback(self):
        pass


@dataclass
class BaseKVStorage(Generic[T], StorageNameSpace):

    async def all_keys(self) -> list[str]:
        raise NotImplementedError

    async def get_by_id(self, id: str) -> T | None:
        raise NotImplementedError

    async def get_by_ids(
        self, ids: list[str], fields: set[str] | None = None
    ) -> list[T | None]:
        raise NotImplementedError

    async def filter_keys(self, data: list[str]) -> set[str]:
        raise NotImplementedError

    async def upsert(self, data: dict[str, T]):
        raise NotImplementedError

    async def drop(self):
        raise NotImplementedError


@dataclass
class JsonKVStorage(BaseKVStorage):

    def __post_init__(self):
        working_dir = self.storage_dir or parameter.WORKING_DIR
        self._file_name = os.path.join(working_dir, f"kv_store_{self.namespace}.json")
        self._data = load_json(self._file_name) or {}
        logger.info(f"💾 Loaded {self.namespace}: {len(self._data)} entries")

    async def all_keys(self) -> list[str]:
        return list(self._data.keys())

    async def index_done_callback(self):
        write_json(self._data, self._file_name)

    async def get_by_id(self, id: str):
        return self._data.get(id, None)

    async def get_by_ids(self, ids: list[str], fields: set[str] | None = None):
        if fields is None:
            return [self._data.get(id) for id in ids]
        return [
            {k: v for k, v in self._data[id].items() if k in fields}
            if id in self._data else None
            for id in ids
        ]

    async def filter_keys(self, data: list[str]) -> set[str]:
        return {key for key in data if key not in self._data}

    async def upsert(self, data: dict[str, dict]):
        self._data.update(data)

    async def drop(self):
        self._data = {}