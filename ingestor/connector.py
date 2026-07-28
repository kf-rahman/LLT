"""Connectors — turn a data source into a stream of IngestEvents.

A connector has NO memory: it lists everything currently present and emits one
event per item. Change detection decides what to actually do. This keeps
connectors dumb and swappable — v1 ships a local-filesystem connector; Onyx's
connectors are intended to wrap into this same interface later (see PROJECT.md).
"""

from __future__ import annotations

import mimetypes
from pathlib import Path
from typing import Iterator, Protocol

from .change import content_hash
from .models import IngestEvent


class Connector(Protocol):
    def list_events(self) -> Iterator[IngestEvent]:
        ...


class LocalFSConnector:
    """Walks a local directory and emits an event per file.

    `source` names the source (used to namespace identities); paths are emitted
    as ``<source>://<relative/path>`` so identity is stable regardless of the
    absolute checkout location.
    """

    def __init__(self, root: Path | str, source: str = "local", skip_hidden: bool = True):
        self._root = Path(root)
        self._source = source
        self._skip_hidden = skip_hidden

    def _identity(self, file: Path) -> str:
        rel = file.relative_to(self._root).as_posix()
        return f"{self._source}://{rel}"

    def list_events(self) -> Iterator[IngestEvent]:
        for file in sorted(self._root.rglob("*")):
            if not file.is_file():
                continue
            if self._skip_hidden and any(part.startswith(".") for part in file.relative_to(self._root).parts):
                continue
            data = file.read_bytes()
            mime, _ = mimetypes.guess_type(file.name)
            yield IngestEvent(
                path=self._identity(file),
                content_hash=content_hash(data),
                mime=mime or "application/octet-stream",
                size=len(data),
                read=(lambda d=data: d),
            )
