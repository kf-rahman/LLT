# IP — Orchestrator (the core loop)

- **Slug:** `orchestrator`
- **Status:** planned
- **FEATURES.md row:** #7

## Goal

Wire the whole flow for a single event and for a whole source: change detection →
classification → recipe lookup/authoring → execute → memory write-back → inline
check → corpus commit → trace. This is the loop `PROJECT.md` describes.

## Data model changes

None new. Orchestrates the stores from other features. Enforces the memory
write-back steps explicitly.

## API contract

- `ingest_event(event, deps) -> IngestOutcome` performing, in order:
  1. `classify_change` → if `UNCHANGED`: set status `skipped`, trace, **return**.
  2. `detect_signature` → `class_key`.
  3. `get_recipe` → hit; else `author_recipe` + save (**memory write**).
  4. **memory write:** upsert `documents` row {path, hash, class, recipe_id,
     trace_id, status=`processing`}. If `MODIFIED`: delete old corpus chunks first.
  5. `execute(recipe, event)`.
  6. inline `check` → pass: commit chunks + status `complete`; fail: discard +
     status `failed`.
  7. trace throughout.
- `ingest_source(connector, deps) -> list[IngestOutcome]` — loop over events.

## UI states

- **skipped** (unchanged), **complete** (checked+stored), **failed** (check failed),
  and per-event trace records.

## Acceptance criteria

- [ ] Fresh file → NEW → recipe chosen → executed → checked → `complete`; a
      `documents` row and trace records exist linking path→recipe_id→trace_id.
- [ ] Re-running on unchanged source → all `skipped`, no re-execution, no new chunks.
- [ ] Modified file → old chunks deleted, reprocessed, single current version remains.
- [ ] A failing check → status `failed`, **no chunks committed** to the corpus.
- [ ] The recipe-hit path performs **no LLM call**.
- [ ] Memory write-back happens even on failure (row reflects final status).

## Open questions

- [ ] Transaction boundaries — should corpus commit + status update be atomic?
      v1: best-effort ordered writes; note as a hardening item.

---

## Changelog

- **2026-07-28** — Created.
