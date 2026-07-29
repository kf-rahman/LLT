"""Shared test fixtures."""

from __future__ import annotations

import pytest

from ingestor.change import content_hash
from ingestor.models import IngestEvent
from ingestor.orchestrator import Deps


@pytest.fixture
def deps(tmp_path):
    """A fully wired Deps rooted at an isolated temp state dir."""
    return Deps.build(root=tmp_path / "state")


@pytest.fixture
def event_factory():
    """Factory: make_event(path, data, mime) -> IngestEvent with a correct hash."""

    def make_event(path: str, data: bytes, mime: str = "text/plain") -> IngestEvent:
        return IngestEvent(
            path=path,
            content_hash=content_hash(data),
            mime=mime,
            size=len(data),
            read=(lambda d=data: d),
        )

    return make_event
