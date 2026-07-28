# IP — Corpus store

- **Slug:** `corpus`
- **Status:** planned
- **FEATURES.md row:** #10

## Goal

The searchable output — the semantic memory. Stores chunks (and later
embeddings) produced by execution, keyed so that a document's chunks can be
**deleted as a unit** when it is modified. v1 uses a simple local store (SQLite
table) behind an interface; a real vector DB slots in later.

## Data model changes

**`chunks` table (SQLite):**

| column | type | notes |
|---|---|---|
| `chunk_id` | TEXT PRIMARY KEY | |
| `path` | TEXT | owning document (FK-ish to `documents.path`) |
| `region` | TEXT | `text` \| `table` \| ... |
| `content` | TEXT | chunk text / serialized cell data |
| `embedding` | BLOB NULL | stubbed in v1 |
| `acl` | TEXT NULL | **reserved** for future permissions; unused in v1 |

## API contract

- `CorpusStore.add_chunks(path, chunks)`.
- `CorpusStore.delete_by_path(path)` — used on MODIFIED before re-adding.
- `CorpusStore.get_by_path(path)` — for tests/inspection.

## UI states

N/A.

## Acceptance criteria

- [ ] `add_chunks` then `get_by_path` returns exactly those chunks.
- [ ] `delete_by_path` removes all chunks for a document and nothing else.
- [ ] After a modified-item reprocess, only the new chunks remain for that path
      (no duplicates from the prior version).
- [ ] `acl` column exists, defaults NULL (reserved).

## Open questions

- [ ] When to introduce real embeddings + a vector index — deferred to the real
      tools feature (#14).

---

## Changelog

- **2026-07-28** — Created.
