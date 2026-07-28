---
name: qa
description: Load when the session shifts to writing or reviewing tests / QA for a feature. Ensures tests are written against the feature's IP acceptance criteria (the contract), not the implementation — so a feature can't be marked complete just because unit tests pass.
---

# QA skill

Load this when you're about to write or review tests. It's the one skill in this
workflow, on purpose — loaded only when needed, not as a default layer.

## The rule

Test against the **acceptance criteria in `features/<slug>/IP.md`** — the
observable behavior the feature promised — **not** against the implementation
you just wrote. Tests that mirror the implementation pass even when the feature
is wrong.

## Checklist

1. Open the feature's `IP.md`. Every **acceptance criterion** should map to at
   least one test. If a criterion can't be tested, it was written wrong — fix
   the criterion first.
2. Cover the **UI states** from the IP: loading, empty, error, and success —
   not just the happy path.
3. Test the **behavior at the boundary the user touches** (API responses,
   rendered output) — not private helpers.
4. Include the failure cases the non-negotiables imply (e.g. invalid input is
   rejected *without data loss*).
5. A feature is **complete** only when every acceptance criterion has a passing
   test. "Unit tests pass" is not the bar; "the criteria are met" is.

## Output

- Tests wired into the project's runner (`scripts/run-checks.sh test`).
- If a criterion is untestable or ambiguous, **stop and flag it** — don't invent
  behavior just to make a test go green.
