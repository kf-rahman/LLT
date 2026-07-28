"""Orchestrator — the core loop.

For one event: change detection -> classification -> recipe lookup/authoring ->
memory write-back -> execute -> inline check -> corpus commit -> trace. This is
the flow described in PROJECT.md. The steady-state (recipe-hit) path performs no
LLM call; the agent (author) runs only on a novel class.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from .classify import class_key_of, detect_signature
from .change import classify_change
from .config import Paths
from .connector import Connector
from .corpus import CorpusStore
from .db import DocumentStore
from .eval import run_checks
from .executor import ToolRegistry, execute
from .models import Change, Document, IngestEvent, Status
from .recipe_store import RecipeStore
from .recipes import DefaultRecipeAuthor, RecipeAuthor, get_or_author
from .tools import build_default_registry
from .trace import Tracer


@dataclass
class Deps:
    documents: DocumentStore
    recipes: RecipeStore
    corpus: CorpusStore
    tracer: Tracer
    registry: ToolRegistry
    author: RecipeAuthor

    @classmethod
    def build(cls, root: Path | str = Paths.under().root) -> "Deps":
        paths = Paths.under(root).ensure()
        return cls(
            documents=DocumentStore(paths.documents_db),
            recipes=RecipeStore(paths.recipes_dir),
            corpus=CorpusStore(paths.corpus_db),
            tracer=Tracer(paths.trace_log),
            registry=build_default_registry(),
            author=DefaultRecipeAuthor(),
        )


@dataclass
class IngestOutcome:
    path: str
    change: Change
    doc_status: Status
    committed: bool = False
    trace_id: str | None = None
    recipe_id: str | None = None
    class_key: str | None = None
    checks_failed: list[str] = field(default_factory=list)
    error: str | None = None


def ingest_event(event: IngestEvent, deps: Deps) -> IngestOutcome:
    existing = deps.documents.get(event.path)
    change = classify_change(deps.documents, event.path, event.content_hash)
    tid = deps.tracer.new_trace(event.path)

    # Layer 1: unchanged -> skip entirely (idempotent). Leave the row as-is.
    if change is Change.UNCHANGED:
        deps.tracer.event(tid, event.path, ok=True, action="skipped", change=change.value)
        return IngestOutcome(event.path, change, existing.status, trace_id=tid,
                             recipe_id=existing.recipe_id, class_key=existing.class_key)

    # Layer 2: classify (no LLM) and get/author the recipe.
    signature = detect_signature(event)
    class_key = class_key_of(signature)
    recipe, authored = get_or_author(deps.recipes, class_key, signature, deps.author)
    if authored:
        deps.tracer.decision(tid, event.path,
                             why=f"novel class {class_key!r}: authored {recipe.recipe_id}",
                             class_key=class_key, recipe_id=recipe.recipe_id)
    else:
        deps.tracer.event(tid, event.path, ok=True, action="recipe_hit",
                          class_key=class_key, recipe_id=recipe.recipe_id)

    # Modified: delete the prior version's chunks before re-adding (no duplicates).
    if change is Change.MODIFIED:
        removed = deps.corpus.delete_by_path(event.path)
        deps.tracer.event(tid, event.path, ok=True, action="deleted_old_chunks", removed=removed)

    # Memory write-back: upsert the documents row (processing), preserving acl.
    deps.documents.upsert(Document(
        path=event.path, content_hash=event.content_hash, class_key=class_key,
        recipe_id=recipe.recipe_id, trace_id=tid, status=Status.PROCESSING,
        acl=existing.acl if existing else None,
    ))

    # Execute the plan (deterministic).
    result = execute(recipe, event, deps.registry)
    if result.error is not None:
        deps.documents.set_status(event.path, Status.FAILED)
        deps.tracer.event(tid, event.path, ok=False, action="execution_error", error=result.error)
        return IngestOutcome(event.path, change, Status.FAILED, trace_id=tid,
                             recipe_id=recipe.recipe_id, class_key=class_key, error=result.error)

    # Inline check gates the corpus.
    check = run_checks(recipe, result)
    if check.passed:
        deps.corpus.add_chunks(event.path, result.chunks)
        deps.documents.set_status(event.path, Status.COMPLETE)
        deps.tracer.event(tid, event.path, ok=True, action="committed", chunks=len(result.chunks))
        return IngestOutcome(event.path, change, Status.COMPLETE, committed=True, trace_id=tid,
                             recipe_id=recipe.recipe_id, class_key=class_key)

    deps.documents.set_status(event.path, Status.FAILED)
    deps.tracer.event(tid, event.path, ok=False, action="check_failed", failed=check.failed)
    return IngestOutcome(event.path, change, Status.FAILED, trace_id=tid,
                         recipe_id=recipe.recipe_id, class_key=class_key,
                         checks_failed=check.failed)


def ingest_source(connector: Connector, deps: Deps) -> list[IngestOutcome]:
    return [ingest_event(event, deps) for event in connector.list_events()]
