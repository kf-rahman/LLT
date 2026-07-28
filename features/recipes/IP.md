# IP — Recipe lookup & authoring

- **Slug:** `recipes`
- **Status:** planned
- **FEATURES.md row:** #5

## Goal

Given a class key: return the existing recipe (HIT → run deterministically), or
on a MISS, have the sub-agent author a recipe **once**, save it, and use it. The
agent is stubbed first (returns a sensible default recipe per known kind) with a
clean seam to wire a real LLM later.

## Data model changes

Uses the recipe store (feature #1). A recipe: `recipe_id`, `class_key`,
`version`, `plan`, `checks`, `history`.

## API contract

- `get_recipe(store, class_key) -> Recipe | None` (exact keyed lookup — the hot path).
- `author_recipe(class_key, signature, similar) -> Recipe` — the miss path.
  - v1: **stub** that maps known kinds → a default plan+checks (deterministic).
  - Seam: `RecipeAuthor` interface so an LLM author drops in without changing callers.
- `similar_recipes(store, signature, k) -> list[Recipe]` — for future LLM few-shot
  (may return [] in v1).

## UI states

N/A. Outcomes: hit / miss→authored.

## Acceptance criteria

- [ ] `get_recipe` on a known class returns the saved recipe; unknown → `None`.
- [ ] On a miss, `author_recipe` produces a recipe with a non-empty `plan` and
      at least one `check`, then it is persisted and retrievable.
- [ ] Authoring the same class twice does not create duplicate/divergent recipes
      (idempotent given the same signature).
- [ ] `recipe_id` = `class@version`; a revision bumps version and appends the old
      one to `history` (mechanism present even if unused in v1).

## Open questions

- [ ] When do we bump a version vs. overwrite? v1 only ever creates v1 per class;
      versioning is exercised later by the drift/re-reason feature.

---

## Changelog

- **2026-07-28** — Created.
