"""Real provider behaviour: PDF text extraction, OCR, and embedding wiring."""

from __future__ import annotations

from ingestor.providers import bytes_to_vector, extract_pdf_text, get_ocr, vector_to_bytes


def test_extract_real_pdf_text(make_text_pdf):
    text, has_text = extract_pdf_text(make_text_pdf("Hello Invoice 2026"))
    assert has_text is True
    assert "Invoice" in text


def test_scanned_pdf_has_no_text_layer(make_scanned_pdf):
    text, has_text = extract_pdf_text(make_scanned_pdf())
    assert has_text is False and text == ""


def test_real_ocr_reads_image(make_text_image):
    # Real tesseract OCR on a rendered image. Assert it recognizes the word.
    out = get_ocr().ocr_image(make_text_image("INVOICE")).upper()
    assert "INVOICE" in out


def test_vector_roundtrip():
    v = [0.1, -0.2, 0.3, 0.4]
    got = bytes_to_vector(vector_to_bytes(v))
    assert len(got) == len(v)
    assert all(abs(a - b) < 1e-6 for a, b in zip(got, v))  # float32 tolerance


def test_embed_tool_populates_real_vectors(event_factory):
    from ingestor.models import Recipe
    from ingestor.executor import execute
    from ingestor.tools import build_default_registry

    recipe = Recipe("text@1", "text", 1,
                    [{"tool": "chunk"}, {"tool": "embed"}], ["chunks > 0"])
    result = execute(recipe, event_factory("s://a.txt", b"one\n\ntwo"), build_default_registry())
    assert result.chunks and all(c.embedding for c in result.chunks)
    dim = len(bytes_to_vector(result.chunks[0].embedding))
    assert dim == 384  # hashing embedder dimension in tests
