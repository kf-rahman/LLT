# IP — Tracing / provenance log

- **Slug:** `tracing`
- **Status:** planned
- **FEATURES.md row:** #9

## Goal

Record what the system did to every item — the episodic memory / audit trail —
as an append-only JSONL log keyed by `trace_id`. Enables "why was this chunk
produced?" debugging. Designed so OpenTelemetry/Phoenix can replace the sink
later without changing callers.

## Data model changes

Append-only file `./.ingestor/traces.jsonl`. Record types:
- `decision` — a routing/authoring decision (why a recipe was chosen/created).
- `trace` — a tool ran / an outcome (ok true/false, metrics).
Both carry `trace_id`, `path`, `ts` (UTC ISO-8601).

## API contract

- `Tracer.new_trace(path) -> trace_id`.
- `Tracer.decision(trace_id, path, why, **fields)`.
- `Tracer.event(trace_id, path, ok, **fields)`.
- Writes are append-only; **never edit or delete past lines.**

## UI states

N/A. It's a log; reads are by `trace_id` or `path`.

## Acceptance criteria

- [ ] Every ingested item gets a `trace_id` and ≥1 trace record.
- [ ] A recipe authoring (miss) emits a `decision` record with a `why`.
- [ ] A skipped (unchanged) item is traced as skipped.
- [ ] A failed check emits a `trace` with `ok:false` naming the failed checks.
- [ ] Records are valid JSON lines; the file only grows (append-only).

## Open questions

- [ ] Retention/compaction — out of scope for v1 (log grows); note for later.

---

## Changelog

- **2026-07-28** — Created.
