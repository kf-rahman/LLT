"""Feature #4 acceptance: signature detection and class keys."""

from __future__ import annotations

from ingestor.classify import class_key_of, detect_signature


def _key(event_factory, path, data, mime="application/octet-stream"):
    return class_key_of(detect_signature(event_factory(path, data, mime)))


def test_non_pdf_kinds(event_factory):
    assert _key(event_factory, "s://d.csv", b"a,b\n1,2\n", "text/csv") == "csv"
    assert _key(event_factory, "s://i.png", b"\x89PNG...", "image/png") == "image"
    assert _key(event_factory, "s://n.txt", b"hello", "text/plain") == "text"


def test_scanned_vs_text_pdf_differ(event_factory):
    scanned = _key(event_factory, "s://scan.pdf", b"%PDF-1.4\n/Image xyz", "application/pdf")
    text = _key(event_factory, "s://text.pdf", b"%PDF-1.4\n/Font xyz", "application/pdf")
    assert scanned == "scanned-pdf"
    assert text == "pdf__text"
    assert scanned != text


def test_text_plus_tables_pdf_is_distinct_class(event_factory):
    key = _key(event_factory, "s://mix.pdf", b"%PDF-1.4\n/Font /Table", "application/pdf")
    assert key == "pdf__text+tables"


def test_class_key_is_deterministic_and_fs_safe(event_factory):
    data = b"%PDF-1.4\n/Font /Table"
    k1 = _key(event_factory, "s://a.pdf", data, "application/pdf")
    k2 = _key(event_factory, "s://a.pdf", data, "application/pdf")
    assert k1 == k2
    assert "/" not in k1  # usable as a recipe filename component
