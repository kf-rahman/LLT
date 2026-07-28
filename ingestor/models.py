"""Core dataclasses shared across the pipeline.

These are plain, dependency-free value types. The two hot-path stores key on:
  - Document.path   (Layer 1 — identity)
  - Recipe.class_key (Layer 2 — type/class)
See PROJECT.md for how they relate (documents reference recipes by recipe_id).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable


def utcnow_iso() -> str:
    """UTC timestamp, ISO-8601, second precision — our one time convention."""
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


class Change(str, Enum):
    """Layer 1 outcome: is this item new, modified, or unchanged?"""

    NEW = "new"
    MODIFIED = "modified"
    UNCHANGED = "unchanged"


class Status(str, Enum):
    """Lifecycle of a document row."""

    PROCESSING = "processing"
    COMPLETE = "complete"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class IngestEvent:
    """One item surfaced by a connector. `read` yields the raw bytes lazily."""

    path: str
    content_hash: str
    mime: str
    size: int
    read: Callable[[], bytes]


@dataclass
class Signature:
    """Cheap, deterministic structural facts about an item (no LLM)."""

    kind: str  # "pdf" | "csv" | "image" | "text" | "unknown"
    facts: dict[str, Any] = field(default_factory=dict)


@dataclass
class Recipe:
    """Procedural memory: how to process a class. A plan + its own checks."""

    recipe_id: str  # "<class_key>@<version>", e.g. "scanned-pdf@1"
    class_key: str
    version: int
    plan: list[dict[str, Any]]
    checks: list[str]
    history: list[dict[str, Any]] = field(default_factory=list)

    @staticmethod
    def make_id(class_key: str, version: int) -> str:
        return f"{class_key}@{version}"


@dataclass
class Document:
    """Layer 1 row: one per item, keyed by path. `acl` is reserved for future
    retrieval-time permissions (unused in v1)."""

    path: str
    content_hash: str
    class_key: str | None = None
    recipe_id: str | None = None
    trace_id: str | None = None
    status: Status = Status.PROCESSING
    acl: str | None = None
    updated_at: str = field(default_factory=utcnow_iso)


@dataclass
class Chunk:
    """A unit of the searchable corpus (semantic memory). `acl` reserved."""

    chunk_id: str
    path: str
    region: str  # "text" | "table" | ...
    content: str
    embedding: bytes | None = None
    acl: str | None = None


@dataclass
class ExecutionResult:
    """What running a recipe produced: chunks + observable facts the checks read."""

    chunks: list[Chunk] = field(default_factory=list)
    facts: dict[str, Any] = field(default_factory=dict)
    error: str | None = None


@dataclass
class CheckResult:
    passed: bool
    failed: list[str] = field(default_factory=list)
