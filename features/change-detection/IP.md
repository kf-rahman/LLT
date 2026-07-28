# IP — Change detection (Layer 1)

- **Slug:** `change-detection`
- **Status:** planned
- **FEATURES.md row:** #2

## Goal

Given an incoming item (path + content), decide **new / modified / unchanged** by
looking it up in `documents` by path and comparing content hashes. This is what
makes ingestion idempotent — re-syncs cost ~nothing and edits are caught.

## Data model changes

None (uses `documents` from feature #1). Adds no columns.

## API contract

- `classify_change(store, path, content_hash) -> Change` where
  `Change ∈ {NEW, MODIFIED, UNCHANGED}`.
  - path absent → `NEW`
  - path present, hash equal → `UNCHANGED`
  - path present, hash differs → `MODIFIED`

## UI states

N/A. Outcomes are the three `Change` values.

## Acceptance criteria

- [ ] Unknown path → `NEW`.
- [ ] Known path, same hash → `UNCHANGED`.
- [ ] Known path, different hash → `MODIFIED`.
- [ ] Hash is content-based (same bytes ⇒ same hash; one byte change ⇒ different).

## Open questions

- [ ] Hash algo — sha256 (assume yes; fast enough, collision-safe).

---

## Changelog

- **2026-07-28** — Created.
