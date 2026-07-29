"""Feature #4 acceptance: signature detection and class keys (now on real PDFs)."""

from __future__ import annotations

from ingestor.classify import _looks_tabular, class_key_of, detect_signature


def _key(event_factory, path, data, mime="application/octet-stream"):
    return class_key_of(detect_signature(event_factory(path, data, mime)))


def test_non_pdf_kinds(event_factory):
    assert _key(event_factory, "s://d.csv", b"a,b\n1,2\n", "text/csv") == "csv"
    assert _key(event_factory, "s://i.png", b"\x89PNG...", "image/png") == "image"
    assert _key(event_factory, "s://n.txt", b"hello", "text/plain") == "text"


def test_real_text_pdf_is_pdf_text(event_factory, make_text_pdf):
    key = _key(event_factory, "s://text.pdf", make_text_pdf("A normal narrative invoice."),
               "application/pdf")
    assert key == "pdf__text"


def test_real_scanned_pdf_is_scanned(event_factory, make_scanned_pdf):
    key = _key(event_factory, "s://scan.pdf", make_scanned_pdf(), "application/pdf")
    assert key == "scanned-pdf"


def test_scanned_and_text_pdf_differ(event_factory, make_text_pdf, make_scanned_pdf):
    text = _key(event_factory, "s://t.pdf", make_text_pdf(), "application/pdf")
    scanned = _key(event_factory, "s://s.pdf", make_scanned_pdf(), "application/pdf")
    assert text != scanned


def test_class_key_is_deterministic_and_fs_safe(event_factory, make_text_pdf):
    data = make_text_pdf()
    k1 = _key(event_factory, "s://a.pdf", data, "application/pdf")
    k2 = _key(event_factory, "s://a.pdf", data, "application/pdf")
    assert k1 == k2 and "/" not in k1


def test_looks_tabular_heuristic():
    assert _looks_tabular("Item   Qty   Price\nApple   3   1.50\nPear   5   0.75")
    assert not _looks_tabular("This is ordinary prose with no columns at all.")
