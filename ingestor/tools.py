"""Built-in tools (v1 stubs).

Each tool is a deterministic function ``fn(ctx, **params)`` that mutates the
ExecutionContext. These are intentionally simple placeholders with the right
interfaces — real OCR (tesseract), table extraction (camelot), and embeddings
(voyage/anthropic) drop in under the same names later (feature #14). No LLM.

Note: `store` is a plan marker only. Actual corpus writes are done by the
orchestrator *after* the inline check passes.
"""

from __future__ import annotations

from .executor import ExecutionContext, ToolRegistry

_TABLE_MARKER = "TABLE:"


def _decode(data: bytes) -> str:
    return data.decode("utf-8", errors="ignore")


def extract_text(ctx: ExecutionContext) -> None:
    ctx.text = _decode(ctx.data)
    ctx.facts["pages"] = max(1, ctx.text.count("\f") + 1)


def ocr(ctx: ExecutionContext) -> None:
    # Stub OCR: treat decodable bytes as the "recognized" text.
    ctx.text = _decode(ctx.data)
    ctx.facts["pages"] = max(1, ctx.text.count("\f") + 1)


def layout(ctx: ExecutionContext) -> None:
    """Segment into regions. Stub: lines under a TABLE: marker are the table
    region; everything else is text."""
    if not ctx.text:
        ctx.text = _decode(ctx.data)
    table_lines, text_lines = [], []
    for line in ctx.text.splitlines():
        (table_lines if line.strip().startswith(_TABLE_MARKER) else text_lines).append(line)
    ctx.regions = {"text": "\n".join(text_lines)}
    if table_lines:
        ctx.regions["table"] = "\n".join(l.split(_TABLE_MARKER, 1)[-1].strip() for l in table_lines)


def _active_content(ctx: ExecutionContext) -> str:
    if ctx.active_region and ctx.active_region in ctx.regions:
        return ctx.regions[ctx.active_region]
    if not ctx.text:
        ctx.text = _decode(ctx.data)
    return ctx.text


def chunk(ctx: ExecutionContext, by: str = "section") -> None:
    content = _active_content(ctx)
    region = ctx.active_region or "text"
    sep = "\f" if by == "page" else "\n\n"
    pieces = [p.strip() for p in content.split(sep) if p.strip()]
    if not pieces and content.strip():
        pieces = [content.strip()]
    for piece in pieces:
        ctx.new_chunk(region, piece)


def extract_table(ctx: ExecutionContext) -> None:
    content = ctx.regions.get("table", ctx.regions.get(ctx.active_region or "", ""))
    rows = [r.strip() for r in content.splitlines() if r.strip()]
    for row in rows:
        ctx.new_chunk("table", row)
    ctx.facts["tables_extracted"] = ctx.facts.get("tables_extracted", 0) + len(rows)


def parse_csv(ctx: ExecutionContext) -> None:
    rows = [r for r in _decode(ctx.data).splitlines() if r.strip()]
    for row in rows:
        ctx.new_chunk("row", row)
    ctx.facts["rows"] = len(rows)


def embed(ctx: ExecutionContext) -> None:
    # Stub embedding: a fixed placeholder vector so the shape exists.
    for c in ctx.chunks:
        if c.embedding is None:
            c.embedding = b"\x00" * 8


def store(ctx: ExecutionContext) -> None:
    # Marker only; the orchestrator commits chunks to the corpus post-check.
    ctx.facts["store_requested"] = True


def build_default_registry() -> ToolRegistry:
    reg = ToolRegistry()
    for name, fn in {
        "extract_text": extract_text,
        "ocr": ocr,
        "layout": layout,
        "chunk": chunk,
        "extract_table": extract_table,
        "parse_csv": parse_csv,
        "embed": embed,
        "store": store,
    }.items():
        reg.register(name, fn)
    return reg
