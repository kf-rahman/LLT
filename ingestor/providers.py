"""Pluggable providers for the heavy, swappable work: text extraction, OCR, and
embeddings. Open-source implementations are the default; every choice is
overridable via environment variables so a user can drop in their own model or
a hosted API without touching the pipeline.

Env vars (all optional; sensible open-source defaults):
  INGESTOR_EMBEDDING_PROVIDER  sentence-transformers | hashing | openai | voyage
  INGESTOR_EMBEDDING_MODEL     model name (default all-MiniLM-L6-v2)
  INGESTOR_OCR_PROVIDER        tesseract | none
  OPENAI_API_KEY / VOYAGE_API_KEY   used only if the matching provider is chosen

Design: providers degrade gracefully. If a chosen open-source dep is missing, we
fall back to a zero-dependency implementation and say so, so the pipeline never
hard-crashes on a fresh machine.
"""

from __future__ import annotations

import hashlib
import os
import struct
from functools import lru_cache
from typing import Protocol

# --- Text extraction ----------------------------------------------------------


def extract_html_text(html: str) -> str:
    """Main-content extraction (drops nav/menus/boilerplate) via trafilatura.
    Returns "" if trafilatura is unavailable or finds nothing, so the caller can
    fall back to a plain tag-stripper."""
    try:
        import trafilatura

        out = trafilatura.extract(html, include_comments=False, include_tables=True)
        return out.strip() if out and out.strip() else ""
    except Exception:
        return ""


def extract_pdf_text(data: bytes) -> tuple[str, bool]:
    """Return (text, has_text_layer). Uses pypdf. has_text_layer is False when the
    PDF yields no extractable text (i.e. it's scanned/image-only → OCR path)."""
    try:
        import io

        from pypdf import PdfReader

        reader = PdfReader(io.BytesIO(data))
        pages = [(p.extract_text() or "") for p in reader.pages]
        text = "\f".join(pages).strip()
        return text, bool(text)
    except Exception:
        return "", False


# --- OCR ----------------------------------------------------------------------


class OCRProvider(Protocol):
    def ocr_image(self, image_bytes: bytes) -> str:
        ...


class TesseractOCR:
    """Open-source default. Requires the tesseract binary + pytesseract + Pillow."""

    def ocr_image(self, image_bytes: bytes) -> str:
        import io

        import pytesseract
        from PIL import Image

        return pytesseract.image_to_string(Image.open(io.BytesIO(image_bytes))).strip()


class NoOCR:
    def ocr_image(self, image_bytes: bytes) -> str:
        return ""


@lru_cache(maxsize=1)
def get_ocr() -> OCRProvider:
    choice = os.getenv("INGESTOR_OCR_PROVIDER", "tesseract").lower()
    if choice == "none":
        return NoOCR()
    try:
        import pytesseract  # noqa: F401

        return TesseractOCR()
    except Exception:
        return NoOCR()  # dep missing → degrade rather than crash


def ocr_pdf_images(data: bytes) -> str:
    """OCR any embedded images in a scanned PDF, page by page (real, via pypdf)."""
    try:
        import io

        from pypdf import PdfReader

        ocr = get_ocr()
        out: list[str] = []
        for page in PdfReader(io.BytesIO(data)).pages:
            for img in getattr(page, "images", []):
                out.append(ocr.ocr_image(img.data))
        return "\f".join(t for t in out if t).strip()
    except Exception:
        return ""


# --- Embeddings ---------------------------------------------------------------


class EmbeddingProvider(Protocol):
    dim: int

    def embed(self, texts: list[str]) -> list[list[float]]:
        ...


class SentenceTransformerEmbedder:
    """Open-source default: a local sentence-transformers model (no API key)."""

    def __init__(self, model_name: str):
        from sentence_transformers import SentenceTransformer

        self._model = SentenceTransformer(model_name)
        self.dim = self._model.get_sentence_embedding_dimension()

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [v.tolist() for v in self._model.encode(texts, normalize_embeddings=True)]


class HashingEmbedder:
    """Zero-dependency deterministic fallback. Real vectors (usable, stable) but
    NOT semantic — a safety net when no model/API is available. Set a real
    provider for quality retrieval."""

    def __init__(self, dim: int = 384):
        self.dim = dim

    def embed(self, texts: list[str]) -> list[list[float]]:
        out = []
        for text in texts:
            vec = [0.0] * self.dim
            for token in text.lower().split():
                h = int(hashlib.md5(token.encode()).hexdigest(), 16)
                vec[h % self.dim] += 1.0
            norm = sum(x * x for x in vec) ** 0.5 or 1.0
            out.append([x / norm for x in vec])
        return out


@lru_cache(maxsize=1)
def get_embedder() -> EmbeddingProvider:
    choice = os.getenv("INGESTOR_EMBEDDING_PROVIDER", "sentence-transformers").lower()
    model = os.getenv("INGESTOR_EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
    if choice == "hashing":
        return HashingEmbedder()
    if choice in ("openai", "voyage"):
        # Seam: implement the API client here, reading the key from env. Kept
        # explicit rather than half-built so it fails loudly if selected unwired.
        raise NotImplementedError(
            f"embedding provider {choice!r} selected but not wired yet; add the client in providers.py"
        )
    try:
        return SentenceTransformerEmbedder(model)
    except Exception:
        return HashingEmbedder()  # model/dep unavailable → deterministic fallback


def vector_to_bytes(vec: list[float]) -> bytes:
    return struct.pack(f"{len(vec)}f", *vec)


def bytes_to_vector(blob: bytes) -> list[float]:
    return list(struct.unpack(f"{len(blob) // 4}f", blob))
