# Session — 2026-07-28 — ingestion-foundation

- **Feature:** `features/orchestrator/IP.md` (+ #1–#10 of FEATURES.md)
- **Commit:** `4ad6eab`
- **Branch:** `feat/ingestion-foundation`

## What was done

Turned the design discussion into a working v1 of the agentic ingestion engine.

- **Planning docs:** rewrote `PROJECT.md` (vision, the two-layer flow, four-tier
  memory, tiny inline eval, future notes on retrieval-time permissions +
  drift/re-reason + OTel/Phoenix), `AGENTS.md` (stack, non-negotiables, the
  small-frequent-commit workflow), `FEATURES.md` (build-order list), and wrote
  per-feature IPs for #1–#10.
- **Implemented the full loop** (`ingestor/` package, Python 3.11+, stdlib only):
  - `models.py` — dataclasses; `config.py` — state-dir paths.
  - `db.py` (documents/SQLite), `recipe_store.py` (recipes/JSON), `corpus.py`
    (chunks/SQLite with `delete_by_path`).
  - `change.py` (new/modified/unchanged via content hash), `connector.py`
    (memoryless LocalFSConnector behind a `Connector` protocol).
  - `classify.py` (signature → class_key; PDF probes are labeled stubs),
    `recipes.py` (`get_recipe` hot path + `get_or_author` miss path,
    `DefaultRecipeAuthor` stub behind a `RecipeAuthor` seam).
  - `executor.py` + `tools.py` (plan runner with region routing; stub tools),
    `eval.py` (closed-set check evaluator), `trace.py` (append-only JSONL).
  - `orchestrator.py` (wires it all + memory write-back) and `cli.py`.
- **26 tests**, all green; smoke-tested the CLI (idempotent re-run, modified-file
  replacement verified). Wired `run-checks.sh test` → pytest (tolerating exit 5).

## Decisions made

- **Two keys, two layers:** identity (`documents.path`) detects new/modified/
  unchanged; class signature selects the recipe. Kept normalized — documents
  reference a recipe by `recipe_id` (renamed from bare version, per request).
- **Agent decides once; tools execute forever.** No LLM on the recipe-hit path;
  the author (stubbed now) runs only on a novel class. Enforced by a test.
- **Corpus writes are orchestrator-controlled, post-check.** The `store` tool is
  a marker; the inline check is the true gate (non-negotiable #1).
- **Onyx positioning:** adopt its connectors, replace its ingestion. Our
  `Connector` protocol is the wrap-in seam; local-FS is a dev stand-in.
- **`acl` reserved (nullable)** on documents + chunks for future retrieval-time
  permissions — schema won't need backfilling.
- **Branch, not main:** built on `feat/ingestion-foundation`; frequent small
  commits for session resilience. Merge to main when ready.

## What didn't work

- First `run-checks.sh test` wiring aborted under `set -e` before the exit-5
  tolerance ran; fixed with `|| code=$?`.

## What's next

- Merge `feat/ingestion-foundation` → `main` (or decide to keep building on the
  branch).
- Replace stubs with real tools (feature #14): pdfminer text-layer + camelot
  table detection in `classify.py`; real OCR/embeddings in `tools.py`.
- Wire a real LLM `RecipeAuthor` (Anthropic) behind the existing seam.
- Then feature #11 (retrieval/query API) — first consumer of the corpus.
