"""Inline "usable" check (eval v1) — the gate on the corpus.

Runs a recipe's own `checks` against the ExecutionResult's facts. Pass -> the
orchestrator may commit chunks; fail -> discard + log. Deliberately tiny: a small
CLOSED set of named predicates, evaluated safely (NO eval() of untrusted strings).

Supported check forms:
  - "text_nonempty"                 (a boolean fact must be truthy)
  - "chunks > 0"                    (<fact> <op> <int-literal>)
  - "chunks == pages"               (<fact> <op> <fact>)
ops: > >= < <= == !=
Unknown facts/ops are rejected (the check fails and is reported) — never silently
passed.
"""

from __future__ import annotations

import operator
from typing import Any

from .models import CheckResult, Recipe

_OPS = {
    ">": operator.gt, ">=": operator.ge,
    "<": operator.lt, "<=": operator.le,
    "==": operator.eq, "!=": operator.ne,
}


def _resolve(token: str, facts: dict[str, Any]) -> tuple[bool, Any]:
    """Return (ok, value). A bare integer literal resolves to itself; otherwise
    the token must be a known fact."""
    if token.lstrip("-").isdigit():
        return True, int(token)
    if token in facts:
        return True, facts[token]
    return False, None


def _eval_check(check: str, facts: dict[str, Any]) -> bool:
    parts = check.split()
    if len(parts) == 1:  # boolean fact
        return bool(facts.get(parts[0])) if parts[0] in facts else False
    if len(parts) == 3:
        left_tok, op, right_tok = parts
        if op not in _OPS:
            return False
        lok, lval = _resolve(left_tok, facts)
        rok, rval = _resolve(right_tok, facts)
        if not (lok and rok):
            return False
        try:
            return bool(_OPS[op](lval, rval))
        except TypeError:
            return False
    return False


def run_checks(recipe: Recipe, result) -> CheckResult:
    failed = [c for c in recipe.checks if not _eval_check(c, result.facts)]
    return CheckResult(passed=(len(failed) == 0), failed=failed)
