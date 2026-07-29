"""Feature #2 & #3 acceptance: change detection and the local-FS connector."""

from __future__ import annotations

from ingestor.change import classify_change, content_hash
from ingestor.connector import LocalFSConnector
from ingestor.db import DocumentStore
from ingestor.models import Change, Document


def test_hash_is_content_based():
    assert content_hash(b"abc") == content_hash(b"abc")
    assert content_hash(b"abc") != content_hash(b"abd")


def test_classify_change(tmp_path):
    store = DocumentStore(tmp_path / "d.db")
    assert classify_change(store, "s://a", "h1") is Change.NEW
    store.upsert(Document(path="s://a", content_hash="h1"))
    assert classify_change(store, "s://a", "h1") is Change.UNCHANGED
    assert classify_change(store, "s://a", "h2") is Change.MODIFIED


def test_connector_emits_event_per_file_and_walks_nested(tmp_path):
    (tmp_path / "sub").mkdir()
    (tmp_path / "a.txt").write_text("A")
    (tmp_path / "sub" / "b.txt").write_text("B")
    (tmp_path / ".hidden").write_text("secret")  # dotfile skipped by default

    events = list(LocalFSConnector(tmp_path, source="src").list_events())
    paths = sorted(e.path for e in events)
    assert paths == ["src://a.txt", "src://sub/b.txt"]
    assert all(e.content_hash and e.size > 0 for e in events)


def test_connector_is_deterministic(tmp_path):
    (tmp_path / "a.txt").write_text("hello")
    first = [(e.path, e.content_hash) for e in LocalFSConnector(tmp_path).list_events()]
    second = [(e.path, e.content_hash) for e in LocalFSConnector(tmp_path).list_events()]
    assert first == second
