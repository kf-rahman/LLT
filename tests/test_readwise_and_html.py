"""Demo path: HTML extraction and the Readwise connector (mocked HTTP)."""

from __future__ import annotations

from ingestor.classify import class_key_of, detect_signature
from ingestor.executor import execute
from ingestor.models import Recipe
from ingestor.orchestrator import ingest_event
from ingestor.readwise import ReadwiseConnector
from ingestor.tools import build_default_registry

HTML = (b"<html><head><style>.x{}</style></head><body>"
        b"<h1>Heading</h1><p>First paragraph.</p>"
        b"<script>tracker()</script><p>Second paragraph.</p></body></html>")


def test_html_classifies_as_html(event_factory):
    assert class_key_of(detect_signature(event_factory("s://a.html", HTML, "text/html"))) == "html"


def test_extract_html_cleans_tags_and_scripts(event_factory):
    recipe = Recipe("html@1", "html", 1, [{"tool": "extract_html"}, {"tool": "chunk"}], ["chunks > 0"])
    result = execute(recipe, event_factory("s://a.html", HTML, "text/html"), build_default_registry())
    joined = " ".join(c.content for c in result.chunks)
    assert "First paragraph." in joined and "Second paragraph." in joined
    assert "tracker()" not in joined  # script dropped


def test_extract_html_drops_boilerplate(event_factory):
    # A page with nav/header/footer chrome around a real article body.
    page = (b"<html><body><nav>Skip to content</nav>"
            b"<header>Using Gmail with screen readers - Upgrade for more</header>"
            b"<article><h1>The RAISE Act</h1>"
            b"<p>New York's RAISE Act proposes a framework for building public trust in "
            b"artificial intelligence through transparency and accountability measures.</p>"
            b"<p>Proponents argue it sets a national precedent for responsible AI oversight "
            b"without stifling innovation across the technology sector.</p></article>"
            b"<footer>Unsubscribe - Privacy Policy</footer></body></html>")
    recipe = Recipe("html@1", "html", 1, [{"tool": "extract_html"}, {"tool": "chunk"}], ["chunks > 0"])
    result = execute(recipe, event_factory("s://a.html", page, "text/html"), build_default_registry())
    joined = " ".join(c.content for c in result.chunks)
    assert "RAISE Act" in joined and "public trust" in joined   # main content kept
    assert "Skip to content" not in joined                       # nav dropped
    assert "Unsubscribe" not in joined                           # footer dropped


def _fake_page(results, cursor=None):
    return {"results": results, "nextPageCursor": cursor}


def test_readwise_connector_yields_events(monkeypatch):
    conn = ReadwiseConnector(token="fake")
    pages = iter([
        _fake_page([{"id": "doc1", "html_content": "<p>Alpha</p>"},
                    {"id": "doc2", "html_content": ""}],           # empty -> skipped
                   cursor="c2"),
        _fake_page([{"id": "doc3", "html_content": "<p>Bravo</p>"}], cursor=None),
    ])
    monkeypatch.setattr(conn, "_get", lambda cursor: next(pages))

    events = list(conn.list_events())
    assert [e.path for e in events] == ["readwise://doc1", "readwise://doc3"]  # doc2 skipped
    assert all(e.mime == "text/html" and e.content_hash for e in events)


def test_readwise_carries_metadata_for_provenance(monkeypatch, deps):
    conn = ReadwiseConnector(token="fake")
    page = _fake_page([{"id": "d1", "html_content": "<p>Body text here.</p>",
                        "title": "The Future Worth Building", "category": "article",
                        "url": "https://example.com/a"}])
    monkeypatch.setattr(conn, "_get", lambda cursor: page)

    ev = next(iter(conn.list_events()))
    assert ev.meta["title"] == "The Future Worth Building" and ev.meta["category"] == "article"
    # and it lands on the document row (readable provenance)
    ingest_event(ev, deps)
    assert deps.documents.get("readwise://d1").meta["title"] == "The Future Worth Building"


def test_readwise_requires_token(monkeypatch):
    monkeypatch.delenv("READWISE_TOKEN", raising=False)
    import pytest

    with pytest.raises(RuntimeError, match="READWISE_TOKEN"):
        ReadwiseConnector(token=None)


def test_readwise_event_ingests_through_pipeline(deps, event_factory):
    # A Readwise-shaped event flows through the full loop -> html recipe -> corpus.
    ev = event_factory("readwise://42", HTML, "text/html")
    outcome = ingest_event(ev, deps)
    assert outcome.committed and outcome.class_key == "html"
    assert deps.corpus.get_by_path("readwise://42")
