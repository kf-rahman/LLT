"""The query harness ranks relevant chunks and resolves provenance."""

from __future__ import annotations

from ingestor.orchestrator import ingest_event
from ingestor.query import search


def test_search_ranks_relevant_doc_top(deps, event_factory):
    ingest_event(event_factory("s://cooking.txt",
                               b"Roast the chicken with garlic and rosemary in the oven."), deps)
    ingest_event(event_factory("s://finance.txt",
                               b"The hedge fund reported quarterly returns and portfolio gains."), deps)

    hits = search(deps, "garlic rosemary chicken", k=3)
    assert hits
    assert hits[0].path == "s://cooking.txt"  # token overlap -> ranked top


def test_search_empty_corpus(deps):
    assert search(deps, "anything") == []
