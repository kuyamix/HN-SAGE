# src/ingest/sources/base.py
from dataclasses import dataclass, field
from typing import Protocol

@dataclass
class RawComment:
    id: str
    parent_id: str | None
    by: str
    text: str
    depth: int = 0

@dataclass
class RawDoc:
    source_id: str
    native_id: str
    kind: str
    title: str
    url: str = ""
    author: str = ""
    score: int = 0
    num_comments: int = 0
    published_at: int = 0
    text: str = ""
    extra: dict = field(default_factory=dict)
    comments: list[RawComment] = field(default_factory=list)

class SourceAdapter(Protocol):
    id: str
    def fetch_ids(self, limit: int) -> list[str]: ...
    def fetch_doc(self, native_id: str) -> RawDoc | None: ...