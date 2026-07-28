# IP — Core data model & stores

- **Slug:** `data-model-and-stores`
- **Status:** in-progress
- **FEATURES.md row:** #1

## Goal

Establish the persistence spine everything else builds on: the `documents`
SQLite table (Layer 1, keyed by path), the recipe store (Layer 2, JSON per
class), and the core dataclasses. After this, other features have typed objects
and durable stores to read/write.

## Data model changes

**`documents` table (SQLite):**

| column | type | notes |
|---|---|---|
| `path` | TEXT PRIMARY KEY | identity = source + path |
| `content_hash` | TEXT | sha256 of bytes; detects modification |
| `class_key` | TEXT | signature-derived class |
| `recipe_id` | TEXT | exact recipe used, e.g. `scanned-pdf@1` |
| `trace_id` | TEXT | links to trace log |
| `status` | TEXT | `processing` \| `complete` \| `failed` \| `skipped` |
| `acl` | TEXT NULL | **reserved** for future permissions; unused in v1 |
| `updated_at` | TEXT | ISO-8601 UTC |

**Recipe (JSON file `recipes/<class>.json`):**
```json
{ "recipe_id": "scanned-pdf@1", "class_key": "scanned-pdf", "version": 1,
  "plan": [ { "tool": "...", "...": "..." } ], "checks": ["..."],
  "history": [] }
```

## API contract

- `Document`, `Recipe`, `IngestEvent`, `Signature` dataclasses (`ingestor/models.py`).
- `DocumentStore`: `get(path)`, `upsert(doc)`, `set_status(path, status)`,
  `delete(path)`.
- `RecipeStore`: `get(class_key)`, `save(recipe)`, `all()`.

## UI states

N/A (library). "States" are store outcomes: hit/miss, present/absent.

## Acceptance criteria

- [ ] `DocumentStore.upsert` then `get` round-trips a `Document` faithfully.
- [ ] `get` on an unknown path returns `None`.
- [ ] Table auto-creates on first use (idempotent schema init).
- [ ] `RecipeStore.save` then `get(class_key)` returns the same recipe;
      `get` on unknown class returns `None`.
- [ ] `recipe_id` encodes `class@version` and is stable.
- [ ] `acl` column exists and defaults to NULL (reserved, untouched).

## Open questions

- [ ] SQLite path/location convention — default `./.ingestor/documents.db`? (assume yes)

---

## Changelog

- **2026-07-28** — Created.
