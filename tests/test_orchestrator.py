"""Feature #7 acceptance: the orchestrator wires the full flow correctly."""

from __future__ import annotations

from ingestor.models import Change, Status
from ingestor.orchestrator import ingest_event


class RaisingAuthor:
    """Fails if asked to author — used to prove the hit path never reasons."""

    def author(self, *a, **k):  # noqa: ANN002, ANN003
        raise AssertionError("recipe author was called on a class HIT")


def test_new_file_completes_with_row_trace_and_chunks(deps, event_factory):
    ev = event_factory("src://n.txt", b"para one\n\npara two")
    outcome = ingest_event(ev, deps)

    assert outcome.change is Change.NEW and outcome.committed
    assert outcome.doc_status is Status.COMPLETE

    row = deps.documents.get("src://n.txt")
    assert row.recipe_id == "text@1" and row.trace_id and row.status is Status.COMPLETE
    chunks = deps.corpus.get_by_path("src://n.txt")
    joined = " ".join(c.content for c in chunks)
    assert chunks and "para one" in joined and "para two" in joined  # content preserved

    traces = [t for t in deps.tracer.read_all() if t["path"] == "src://n.txt"]
    assert any(t.get("action") == "committed" for t in traces)


def test_rerun_unchanged_skips_without_reprocessing(deps, event_factory):
    ev = event_factory("src://n.txt", b"stable content here")
    ingest_event(ev, deps)
    before = deps.corpus.count()

    outcome = ingest_event(ev, deps)  # identical bytes
    assert outcome.change is Change.UNCHANGED and not outcome.committed
    assert deps.corpus.count() == before  # no new chunks


def test_modified_replaces_old_chunks(deps, event_factory):
    ingest_event(event_factory("src://n.txt", b"Alpha one. Alpha two."), deps)
    outcome = ingest_event(event_factory("src://n.txt", b"Xray. Yankee. Zulu."), deps)

    assert outcome.change is Change.MODIFIED and outcome.committed
    joined = " ".join(c.content for c in deps.corpus.get_by_path("src://n.txt"))
    assert "Xray" in joined and "Zulu" in joined  # new version present
    assert "Alpha" not in joined                   # old version fully replaced
    assert deps.corpus.count() == len(deps.corpus.get_by_path("src://n.txt"))  # no leftovers


def test_failing_check_commits_nothing(deps, event_factory):
    outcome = ingest_event(event_factory("src://empty.txt", b"   "), deps)  # yields 0 chunks
    assert not outcome.committed
    assert outcome.doc_status is Status.FAILED
    assert "chunks > 0" in outcome.checks_failed
    assert deps.corpus.get_by_path("src://empty.txt") == []  # corpus untouched


def test_recipe_hit_makes_no_author_call(deps, event_factory):
    ingest_event(event_factory("src://a.txt", b"first\n\nfile"), deps)  # authors text@1
    deps.author = RaisingAuthor()  # any further authoring would raise

    outcome = ingest_event(event_factory("src://b.txt", b"second\n\nfile"), deps)
    assert outcome.committed and outcome.recipe_id == "text@1"  # reused, no reasoning
