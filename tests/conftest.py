"""Shared test fixtures.

Tests default to the zero-dependency hashing embedder so the suite is fast,
offline, and deterministic (real sentence-transformers embeddings are verified
via a separate smoke run, not the unit suite). OCR tests use the real tesseract
binary, which is local and offline.
"""

from __future__ import annotations

import io
import os

os.environ.setdefault("INGESTOR_EMBEDDING_PROVIDER", "hashing")

import pytest

from ingestor.change import content_hash
from ingestor.models import IngestEvent
from ingestor.orchestrator import Deps


@pytest.fixture
def deps(tmp_path):
    """A fully wired Deps rooted at an isolated temp state dir."""
    return Deps.build(root=tmp_path / "state")


@pytest.fixture
def event_factory():
    """Factory: make_event(path, data, mime) -> IngestEvent with a correct hash."""

    def make_event(path: str, data: bytes, mime: str = "text/plain") -> IngestEvent:
        return IngestEvent(
            path=path,
            content_hash=content_hash(data),
            mime=mime,
            size=len(data),
            read=(lambda d=data: d),
        )

    return make_event


@pytest.fixture
def make_text_pdf():
    """Real PDF with an extractable text layer."""

    def _make(text: str = "Invoice 2026\n\nAmount due: 100 USD") -> bytes:
        from fpdf import FPDF

        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Helvetica", size=12)
        pdf.multi_cell(0, 10, text)
        return bytes(pdf.output())

    return _make


@pytest.fixture
def make_scanned_pdf():
    """Real image-only PDF (a rendered-text image, no text layer -> 'scanned')."""

    def _make(text: str = "SCANNED INVOICE") -> bytes:
        from fpdf import FPDF
        from PIL import Image, ImageDraw, ImageFont

        img = Image.new("RGB", (600, 200), "white")
        ImageDraw.Draw(img).text((20, 80), text, fill="black", font=ImageFont.load_default(size=40))
        buf = io.BytesIO()
        img.save(buf, "PNG")
        buf.seek(0)

        pdf = FPDF()
        pdf.add_page()
        pdf.image(buf, x=10, y=10, w=150)
        return bytes(pdf.output())

    return _make


@pytest.fixture
def make_text_image():
    """Real PNG with rendered text, for OCR."""

    def _make(text: str = "INVOICE 2026") -> bytes:
        from PIL import Image, ImageDraw, ImageFont

        img = Image.new("RGB", (600, 160), "white")
        ImageDraw.Draw(img).text((20, 60), text, fill="black", font=ImageFont.load_default(size=48))
        buf = io.BytesIO()
        img.save(buf, "PNG")
        return buf.getvalue()

    return _make
