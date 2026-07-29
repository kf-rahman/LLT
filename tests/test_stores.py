"""Feature #1 acceptance: documents, recipes, corpus stores."""

from __future__ import annotations

from ingestor.corpus import CorpusStore
from ingestor.db import DocumentStore
from ingestor.models import Chunk, Document, Recipe, Status
from ingestor.recipe_store import RecipeStore


def test_document_roundtrip(tmp_path):
    store = DocumentStore(tmp_path / "d.db")
    doc = Document(path="s://a", content_hash="h1", class_key="text",
                   recipe_id="text@1", trace_id="t1", status=Status.COMPLETE)
    store.upsert(doc)
    got = store.get("s://a")
    assert got is not None
    assert (got.path, got.content_hash, got.recipe_id, got.status) == ("s://a", "h1", "text@1", Status.COMPLETE)


def test_document_get_unknown_is_none(tmp_path):
    assert DocumentStore(tmp_path / "d.db").get("nope") is None


def test_document_acl_defaults_null(tmp_path):
    store = DocumentStore(tmp_path / "d.db")
    store.upsert(Document(path="s://a", content_hash="h"))
    assert store.get("s://a").acl is None


def test_recipe_roundtrip_and_miss(tmp_path):
    store = RecipeStore(tmp_path / "recipes")
    r = Recipe(recipe_id="text@1", class_key="text", version=1,
               plan=[{"tool": "chunk"}], checks=["chunks > 0"])
    store.save(r)
    got = store.get("text")
    assert got is not None and got.recipe_id == "text@1" and got.plan == [{"tool": "chunk"}]
    assert store.get("unknown-class") is None


def test_corpus_add_get_delete(tmp_path):
    corpus = CorpusStore(tmp_path / "c.db")
    corpus.add_chunks("s://a", [Chunk("s://a#1", "s://a", "text", "hello")])
    corpus.add_chunks("s://b", [Chunk("s://b#1", "s://b", "text", "world")])
    assert [c.content for c in corpus.get_by_path("s://a")] == ["hello"]
    corpus.delete_by_path("s://a")
    assert corpus.get_by_path("s://a") == []
    assert [c.content for c in corpus.get_by_path("s://b")] == ["world"]  # only 'a' removed
