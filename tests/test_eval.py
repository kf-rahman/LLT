"""Feature #8 acceptance: the inline usable-check."""

from __future__ import annotations

from ingestor.eval import run_checks
from ingestor.models import ExecutionResult, Recipe


def _recipe(checks):
    return Recipe("x@1", "x", 1, [{"tool": "chunk"}], checks)


def test_passing_checks():
    result = ExecutionResult(facts={"chunks": 3, "pages": 3, "text_nonempty": True})
    assert run_checks(_recipe(["chunks > 0", "text_nonempty", "chunks == pages"]), result).passed


def test_zero_chunks_fails_and_names_the_check():
    result = ExecutionResult(facts={"chunks": 0, "text_nonempty": False})
    r = run_checks(_recipe(["chunks > 0"]), result)
    assert not r.passed and r.failed == ["chunks > 0"]


def test_unknown_check_is_rejected_not_passed():
    result = ExecutionResult(facts={"chunks": 1})
    r = run_checks(_recipe(["mystery_fact", "chunks !! 0"]), result)
    assert not r.passed
    assert set(r.failed) == {"mystery_fact", "chunks !! 0"}
