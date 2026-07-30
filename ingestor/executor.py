"""Executor — run a recipe's plan deterministically.

Walks the plan; each step is either a tool step ``{"tool": name, ...params}`` or
a route step ``{"route": {region: [steps...]}}``. Tools thread a mutable
ExecutionContext and produce chunks. NO LLM runs here — this is the steady-state
path.

Corpus writes are NOT done here: execution only *produces* chunks. The
orchestrator commits them to the corpus only after the inline check passes, so
the check stays the true gate (see PROJECT.md non-negotiable #1).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from .models import Chunk, ExecutionResult, IngestEvent


class UnknownToolError(KeyError):
    pass


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, Callable[..., None]] = {}

    def register(self, name: str, fn: Callable[..., None]) -> None:
        self._tools[name] = fn

    def get(self, name: str) -> Callable[..., None]:
        try:
            return self._tools[name]
        except KeyError as e:
            raise UnknownToolError(f"no tool registered named {name!r}") from e


@dataclass
class ExecutionContext:
    event: IngestEvent
    data: bytes
    text: str = ""
    regions: dict[str, str] = field(default_factory=dict)
    active_region: str | None = None
    extracted: bool = False  # True once an extraction tool has run (even if it found nothing)
    chunks: list[Chunk] = field(default_factory=list)
    facts: dict[str, Any] = field(default_factory=dict)
    _seq: int = 0

    def new_chunk(self, region: str, content: str) -> Chunk:
        self._seq += 1
        chunk = Chunk(chunk_id=f"{self.event.path}#{self._seq}", path=self.event.path,
                      region=region, content=content)
        self.chunks.append(chunk)
        return chunk


def _run_step(step: dict[str, Any], ctx: ExecutionContext, registry: ToolRegistry) -> None:
    if "route" in step:
        for region_type, substeps in step["route"].items():
            ctx.active_region = region_type
            for sub in substeps:
                _run_step(sub, ctx, registry)
            ctx.active_region = None
        return
    if "tool" in step:
        name = step["tool"]
        params = {k: v for k, v in step.items() if k != "tool"}
        registry.get(name)(ctx, **params)
        return
    raise ValueError(f"malformed plan step (no 'tool' or 'route'): {step!r}")


def execute(recipe, event: IngestEvent, registry: ToolRegistry) -> ExecutionResult:
    ctx = ExecutionContext(event=event, data=event.read())
    try:
        for step in recipe.plan:
            _run_step(step, ctx, registry)
    except Exception as e:  # a tool failed — surface it, don't crash the whole run
        return ExecutionResult(chunks=ctx.chunks, facts=_standard_facts(ctx), error=repr(e))
    return ExecutionResult(chunks=ctx.chunks, facts=_standard_facts(ctx))


def _standard_facts(ctx: ExecutionContext) -> dict[str, Any]:
    """The observable facts the inline check reads. Tool-supplied facts win."""
    facts = dict(ctx.facts)
    facts["chunks"] = len(ctx.chunks)
    facts["text_nonempty"] = any(c.content.strip() for c in ctx.chunks)
    facts.setdefault("pages", ctx.facts.get("pages", 1))
    facts.setdefault("tables_extracted", ctx.facts.get("tables_extracted", 0))
    return facts
