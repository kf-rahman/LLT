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

from .models import IngestEvent, Signature


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


# --- PDF structural probes (STUBS — replace with real detectors) ---------------

def _pdf_has_text_layer(data: bytes) -> bool:
    # Real impl: pdfminer extract_text and check it's non-trivial.
    return b"/Font" in data


def _pdf_has_tables(data: bytes) -> bool:
    # Real impl: camelot/pdfplumber table detection over pages.
    return b"/Table" in data


def _pdf_is_scanned(data: bytes) -> bool:
    # Real impl: pages are images with no/negligible extractable text.
    return b"/Image" in data and not _pdf_has_text_layer(data)


def detect_signature(event: IngestEvent) -> Signature:
    data = event.read()
    kind = _kind(event, data[:5])
    facts: dict[str, object] = {}
    if kind == "pdf":
        facts = {
            "text_layer": _pdf_has_text_layer(data),
            "tables": _pdf_has_tables(data),
            "scanned": _pdf_is_scanned(data),
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
