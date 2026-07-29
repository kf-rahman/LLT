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

## Update — real providers (same session)

Replaced the processing stubs with real, verified implementations, per user
direction (open-source defaults, everything env-swappable, LLM recipe author
stays hand-coded for now):

- `providers.py` — env-configured providers with graceful fallback:
  - **PDF text** via pypdf (`extract_pdf_text` → text + has_text_layer).
  - **OCR** via tesseract (images *and* scanned-PDF page images); `none` option.
  - **Embeddings** via sentence-transformers (default, 384-dim) with a zero-dep
    hashing fallback; `openai`/`voyage` seams raise clearly until wired.
- `tools.py` extract_text/ocr/embed and `classify.py` PDF probes now call the
  real providers (text_layer/scanned are real pypdf; tables = text heuristic).
- Deps as an optional `processing` extra; `.env.example` documents every knob.
- Tests use the deterministic hashing embedder + real tesseract; 33 passing.
- **Verified end-to-end with real defaults:** a text PDF, a scanned PDF, an
  image, and a CSV all ingested — real extracted text, real OCR output, real
  384-dim vectors in the corpus.

Decisions: Onyx will **not** be forked (it's a 94MB app, not a library); we adopt
individual MIT connectors à la carte only when needed. Considering borrowing
Onyx's chunker + typed Section model + contextual-retrieval summaries as ideas.

## What's next

- Merge `feat/ingestion-foundation` → `main` (or keep building on the branch).
- Optionally borrow from Onyx (ideas, not the app): its `indexing/chunker.py`
  strategy (min-content merge, mini-chunks), the `Section`/`TextSection`/
  `ImageSection` typed model, and contextual-retrieval chunk summaries.
- Feature #11 (retrieval/query API) — first consumer of the real embeddings.
- Later: wire a real LLM `RecipeAuthor` (Anthropic) behind the existing seam.
