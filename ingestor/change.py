"""Change detection — Layer 1 decision.

Given a path and its current content hash, decide new / modified / unchanged by
looking the path up in the DocumentStore. This is what makes ingestion
idempotent: re-syncs skip unchanged items and catch edits.
"""

from __future__ import annotations

import hashlib

from .db import DocumentStore
from .models import Change


def content_hash(data: bytes) -> str:
    """sha256 of the item's bytes. Same bytes -> same hash; any change -> different."""
    return hashlib.sha256(data).hexdigest()


def classify_change(store: DocumentStore, path: str, content_hash: str) -> Change:
    existing = store.get(path)
    if existing is None:
        return Change.NEW
    if existing.content_hash == content_hash:
        return Change.UNCHANGED
    return Change.MODIFIED
