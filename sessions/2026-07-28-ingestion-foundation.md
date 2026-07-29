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

## Update — real-corpus run + reference check (same session)

Ran the loop over a real corpus: **50 clinical monograph PDFs** in
`~/Desktop/general-magic/data/...`, and checked against the reference full RAG
workflow in `general-magic/General-Magic-CaseStudy/` (its own ingestion + Chroma
index + eval over the same PDFs). This surfaced two real bugs synthetic tests
missed — both now fixed:

- **All 50 PDFs failed on the first run.** Cause chain: `_looks_tabular` fired on
  almost any PDF → everything misclassified `pdf__text+tables`; the `layout` tool
  still decoded raw PDF bytes instead of pypdf; and that recipe gated on
  `tables_extracted > 0`, so mostly-text docs hard-failed. Fixed: strict tabular
  heuristic (>=4 consistent rows), real pypdf text in `layout`, and tables are a
  bonus (gate = `chunks > 0` + `text_nonempty`). → **52/52 ingest, 0 failures.**
- **Chunking was silently truncating.** vs the reference (~200-tok windows, hard
  cap 256): our chunks averaged ~910 tokens (max ~8800), so 52 chunks lost most
  content at embed time (MiniLM truncates at 256 tok). Fixed with bounded
  sentence-aligned windowing (`CHUNK_MAX_CHARS`). → 1130 chunks, avg ~157 tok,
  **0 over the cap** (reference: 718, also 0 over).

**Reference comparison result:** coverage parity (we ingest all docs, real text +
OCR + 384-dim embeddings), and chunking now in the same bounded regime. The
reference additionally extracts structured facts (formulary/cross-refs/figures)
tied to its clinical-QA use case — out of scope for our general ingestion layer.

Takeaway captured: the real data confirmed we needed a bounded chunker (the
question "do we need Onyx's chunker" → we needed the *size-bound idea*, not the
whole thing). Also note our chunker doesn't yet do sentence-overlap between
windows like the reference — a cheap future improvement.

## What's next

- Merge `feat/ingestion-foundation` → `main` (or keep building on the branch).
- Optional chunk quality: add 1-sentence overlap between windows (reference does).
- Optionally borrow from Onyx (ideas, not the app): the typed `Section` model and
  contextual-retrieval chunk summaries (needs the LLM wired first).
- Later: wire a real LLM `RecipeAuthor` (Anthropic) behind the existing seam.
