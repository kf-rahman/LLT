"""Built-in tools (v1 stubs).

Each tool is a deterministic function ``fn(ctx, **params)`` that mutates the
ExecutionContext. These are intentionally simple placeholders with the right
interfaces — real OCR (tesseract), table extraction (camelot), and embeddings
(voyage/anthropic) drop in under the same names later (feature #14). No LLM.

Note: `store` is a plan marker only. Actual corpus writes are done by the
orchestrator *after* the inline check passes.
"""

from __future__ import annotations

import re

from .executor import ExecutionContext, ToolRegistry
from .providers import (
    extract_pdf_text,
    get_embedder,
    get_ocr,
    ocr_pdf_images,
    vector_to_bytes,
)

def _decode(data: bytes) -> str:
    return data.decode("utf-8", errors="ignore")


def _is_pdf(data: bytes) -> bool:
    return data[:5].startswith(b"%PDF")


def _line_is_tabular(line: str) -> bool:
    return len([c for c in re.split(r"\t|\s{2,}", line.strip()) if c]) >= 3


def extract_text(ctx: ExecutionContext) -> None:
    """Real text extraction: pypdf for PDFs, decode otherwise."""
    if _is_pdf(ctx.data):
        ctx.text, _ = extract_pdf_text(ctx.data)
    else:
        ctx.text = _decode(ctx.data)
    ctx.facts["pages"] = max(1, ctx.text.count("\f") + 1)


def ocr(ctx: ExecutionContext) -> None:
    """Real OCR: tesseract on image bytes, or on the embedded images of a scanned
    PDF. Provider is env-selectable (INGESTOR_OCR_PROVIDER)."""
    if _is_pdf(ctx.data):
        ctx.text = ocr_pdf_images(ctx.data)
    else:
        ctx.text = get_ocr().ocr_image(ctx.data)
    ctx.facts["pages"] = max(1, ctx.text.count("\f") + 1)


def layout(ctx: ExecutionContext) -> None:
    """Segment a document into regions. Real text first (pypdf for PDFs), then
    split off table-looking lines as a bonus 'table' region. The full text is
    always kept in the 'text' region so nothing is lost if the table heuristic
    is wrong. (Real layout/table extraction — camelot/unstructured — slots in
    here later without changing the recipe.)"""
    if _is_pdf(ctx.data):
        ctx.text, _ = extract_pdf_text(ctx.data)
    elif not ctx.text:
        ctx.text = _decode(ctx.data)
    ctx.regions = {"text": ctx.text}
    table_lines = [ln for ln in ctx.text.splitlines() if _line_is_tabular(ln)]
    if len(table_lines) >= 4:
        ctx.regions["table"] = "\n".join(table_lines)


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
    """Real embeddings via the configured provider (sentence-transformers by
    default; env-selectable). Stored as packed float32 bytes."""
    pending = [c for c in ctx.chunks if c.embedding is None]
    if not pending:
        return
    vectors = get_embedder().embed([c.content for c in pending])
    for chunk_obj, vec in zip(pending, vectors):
        chunk_obj.embedding = vector_to_bytes(vec)


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
