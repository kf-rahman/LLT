# IP — Inline "usable" check (eval v1)

- **Slug:** `inline-eval`
- **Status:** planned
- **FEATURES.md row:** #8

## Goal

A single, cheap, deterministic gate: after execution, run the recipe's own
`checks` against the produced output. Pass → allow the commit to the corpus;
fail → discard and log. Keeps garbage out of the corpus. Deliberately tiny — no
scoring, no LLM-judge.

## Data model changes

None. Reads `recipe.checks` and the `ExecutionResult`.

## API contract

- `run_checks(recipe, result) -> CheckResult { passed: bool, failed: list[str] }`.
- Checks are expressed as simple, safe predicates over result facts (e.g.
  `chunks > 0`, `text_nonempty`, `chunks == pages`). A small, closed evaluator —
  **no arbitrary eval of untrusted strings.**

## UI states

- **pass** → proceed to commit; **fail** → list which checks failed (for the trace).

## Acceptance criteria

- [ ] A recipe whose checks pass yields `passed=True`.
- [ ] A result with zero chunks fails a `chunks > 0` check with that check named.
- [ ] Unknown/unsupported check names are rejected safely (not silently passed).
- [ ] The orchestrator commits to the corpus **only** when `passed=True`.

## Open questions

- [ ] Check DSL surface — start with a fixed set of named predicates; expand as
      real tools produce richer result facts.

---

## Changelog

- **2026-07-28** — Created.
