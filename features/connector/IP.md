# IP — Connector & event emission

- **Slug:** `connector`
- **Status:** planned
- **FEATURES.md row:** #3

## Goal

Point the engine at a data source and get one `IngestEvent` per item. v1 is a
local-filesystem connector; the interface is designed so S3/Drive/Notion slot in
later without touching the orchestrator.

## Data model changes

None. Produces `IngestEvent { path, content_hash, mime, size, bytes_ref }`.

## API contract

- `Connector` protocol: `list_events() -> Iterator[IngestEvent]`.
- `LocalFSConnector(root)`: walks `root`, emits an event per file with computed
  content hash and detected MIME.
- The connector has **no memory** — it lists everything present. Change detection
  (feature #2) decides what to actually do. This is intentional.

## UI states

N/A. Empty source → zero events.

## Acceptance criteria

- [ ] Pointing at a dir with N files yields N events.
- [ ] Each event carries a correct content hash and a resolvable way to read bytes.
- [ ] Re-listing the same unchanged dir yields identical events (deterministic).
- [ ] Nested subdirectories are walked.

## Open questions

- [ ] Symlinks / hidden files — skip dotfiles by default? (assume yes)

---

## Changelog

- **2026-07-28** — Created.
- **2026-07-28** — Decision: we do **not** build our own cloud connectors. We
  adopt Onyx's connector breadth and wrap them behind this `Connector` interface;
  our differentiation is the agentic ingestion layer downstream of the event. The
  local-FS connector here is a dev stand-in. (See PROJECT.md "positioning".)
