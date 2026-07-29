"""Classification — Layer 2 signature detection (deterministic, no LLM).

Produces a structural Signature and derives a stable class_key from it. The
class_key is what the recipe lookup uses; a novel class_key (no recipe) is what
triggers the agent.

v1 detects `kind` from MIME/extension/magic bytes (solid) and derives PDF
structural facts (text_layer / tables / scanned) from lightweight byte
heuristics. Those PDF probes are STUBS with a clean seam — replace with real
detectors (pdfminer for text layer, camelot/pdfplumber for tables) without
changing callers or class_key semantics.
"""

from __future__ import annotations

import re

from .models import IngestEvent, Signature
from .providers import extract_pdf_text


def _kind(event: IngestEvent, head: bytes) -> str:
    mime = (event.mime or "").lower()
    name = event.path.lower()
    if head.startswith(b"%PDF") or mime == "application/pdf" or name.endswith(".pdf"):
        return "pdf"
    if mime == "text/csv" or name.endswith(".csv"):
        return "csv"
    if mime.startswith("image/") or name.endswith((".png", ".jpg", ".jpeg", ".tiff", ".gif")):
        return "image"
    if mime.startswith("text/") or name.endswith((".txt", ".md")):
        return "text"
    return "unknown"


# --- PDF structural probes -----------------------------------------------------
# text_layer / scanned are REAL (pypdf). Table detection is a text-shape
# heuristic — good enough to route, and swappable for camelot/unstructured later.

def _looks_tabular(text: str) -> bool:
    """Conservative heuristic: a real table has several rows with a *consistent*
    column count. Require >=4 lines that split into the same number of columns
    (>=3) on tabs / 2+ spaces. Kept strict so ordinary prose isn't misread as a
    table (a false positive used to route docs down the table path)."""
    from collections import Counter

    counts: Counter[int] = Counter()
    for line in text.splitlines():
        cells = [c for c in re.split(r"\t|\s{2,}", line.strip()) if c]
        if len(cells) >= 3:
            counts[len(cells)] += 1
    return any(n >= 4 for n in counts.values())


def detect_signature(event: IngestEvent) -> Signature:
    data = event.read()
    kind = _kind(event, data[:5])
    facts: dict[str, object] = {}
    if kind == "pdf":
        text, has_text = extract_pdf_text(data)
        facts = {
            "text_layer": has_text,                 # real: did pypdf extract text?
            "tables": has_text and _looks_tabular(text),
            "scanned": not has_text,                # no extractable text => image-only
        }
    return Signature(kind=kind, facts=facts)


def class_key_of(sig: Signature) -> str:
    """Stable, filesystem-safe class key. Same signature -> same key."""
    if sig.kind != "pdf":
        return sig.kind

    # A scanned/image-only PDF is its own class regardless of other facts.
    if sig.facts.get("scanned") and not sig.facts.get("text_layer"):
        return "scanned-pdf"

    modalities: list[str] = []
    if sig.facts.get("text_layer"):
        modalities.append("text")
    if sig.facts.get("tables"):
        modalities.append("tables")
    if modalities:
        return "pdf__" + "+".join(modalities)
    return "pdf"
