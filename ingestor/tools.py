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
from html.parser import HTMLParser

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


# Bounded chunking. Embedding models silently truncate past their context window,
# so a chunk MUST never exceed the hard cap or its tail is lost from the index.
# Chars are a cheap token proxy (~4 chars/token), matching the target window.
CHUNK_TARGET_CHARS = 800   # ~200 tokens — the window we aim for
CHUNK_MAX_CHARS = 1024     # ~256 tokens — the embedding model's hard context

_SENTENCE = re.compile(r"(?<=[.!?])\s+")


def _sentences(text: str):
    for para in re.split(r"\n\s*\n", text):
        para = para.strip()
        if not para:
            continue
        for sent in _SENTENCE.split(para):
            sent = sent.strip()
            if sent:
                yield sent


def _windows(text: str) -> list[str]:
    """Greedy ~target-sized, sentence-aligned windows; hard-split any sentence
    longer than the cap so no window ever exceeds CHUNK_MAX_CHARS."""
    out: list[str] = []
    cur = ""
    for sent in _sentences(text):
        while len(sent) > CHUNK_MAX_CHARS:
            if cur:
                out.append(cur)
                cur = ""
            out.append(sent[:CHUNK_MAX_CHARS])
            sent = sent[CHUNK_MAX_CHARS:].strip()
        if cur and len(cur) + 1 + len(sent) > CHUNK_TARGET_CHARS:
            out.append(cur)
            cur = sent
        else:
            cur = f"{cur} {sent}".strip() if cur else sent
    if cur:
        out.append(cur)
    return out


def extract_text(ctx: ExecutionContext) -> None:
    """Real text extraction: pypdf for PDFs, decode otherwise."""
    if _is_pdf(ctx.data):
        ctx.text, _ = extract_pdf_text(ctx.data)
    else:
        ctx.text = _decode(ctx.data)
    ctx.facts["pages"] = max(1, ctx.text.count("\f") + 1)


class _HTMLToText(HTMLParser):
    """Strip tags to readable text; drop script/style; break on block elements."""

    _DROP = {"script", "style", "noscript", "head"}
    _BREAK = {"p", "br", "div", "li", "tr", "h1", "h2", "h3", "h4", "h5", "h6", "section"}

    def __init__(self) -> None:
        super().__init__()
        self._parts: list[str] = []
        self._skip = 0

    def handle_starttag(self, tag, attrs):
        if tag in self._DROP:
            self._skip += 1
        elif tag in self._BREAK:
            self._parts.append("\n")

    def handle_endtag(self, tag):
        if tag in self._DROP and self._skip:
            self._skip -= 1
        elif tag in ("p", "div", "section", "li"):
            self._parts.append("\n")

    def handle_data(self, data):
        if not self._skip and data.strip():
            self._parts.append(data)

    def text(self) -> str:
        return re.sub(r"\n{3,}", "\n\n", "".join(self._parts)).strip()


def extract_html(ctx: ExecutionContext) -> None:
    """Real HTML → clean text (stdlib html.parser). Used for Readwise Reader
    documents (html_content) and any text/html item."""
    parser = _HTMLToText()
    parser.feed(_decode(ctx.data))
    ctx.text = parser.text()
    ctx.facts["pages"] = 1


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
    """Bounded, sentence-aligned chunking. `by` is accepted for recipe
    compatibility; windowing supersedes naive page/section splitting so no chunk
    can exceed the embedding model's context (no silent truncation)."""
    content = _active_content(ctx)
    region = ctx.active_region or "text"
    for window in _windows(content):
        ctx.new_chunk(region, window)


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
        "extract_html": extract_html,
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
