# Ingestor — an agentic ingestion engine

Point it at a data source and it keeps a searchable corpus continuously and
correctly in sync: it inspects each item, **decides how to process it, remembers
that decision, executes deterministically, and traces everything** — so setting
up a RAG system becomes "point your data here and ingestion is completely
accounted for."

See [`PROJECT.md`](PROJECT.md) for the full design.

---

## The core idea: agentic ingestion

Instead of one static pipeline, processing decisions are made **per data class,
once**, captured as a reusable **recipe**, then executed deterministically for
every item of that class. The expensive reasoning runs rarely (only for novel
data shapes); cheap deterministic tools do the bulk of the work.

```
source ─► event ─► LAYER 1: doc lookup (new / modified / unchanged)   ← idempotent
                   LAYER 2: classify → recipe (hit = run; miss = author once)
                   execute (with region routing) ─► inline check ─► corpus + trace
```

- **Idempotent:** re-syncing skips unchanged items, replaces modified ones, adds new ones.
- **Accountable:** every item links to the exact recipe, a trace id, and a status; every decision/run is in an append-only trace log.
- **Gated:** nothing enters the corpus unless the recipe's own checks pass.

Memory is tiered — **procedural** (recipes), **episodic** (trace log),
**semantic** (the corpus/embeddings), **working** (a reasoning turn).

---

## Quick start

```bash
python -m pip install -e ".[processing,dev]"   # real PDF/OCR/embeddings + test deps
python -m ingestor.cli ingest <some_dir>       # ingest a folder
python -m ingestor.cli ingest <some_dir>       # run again → unchanged items skip
python -m pytest -q                            # 34 tests
```

Generated state (SQLite stores, recipes, `traces.jsonl`) lands in a gitignored
`.ingestor/`.

### Providers (open-source defaults, all swappable via env)

Copy `.env.example` → `.env` and override any line. Defaults need no API keys:

| What | Default (open source) | Swap to |
|---|---|---|
| PDF text | pypdf | — |
| OCR | tesseract | `INGESTOR_OCR_PROVIDER=none` |
| Embeddings | sentence-transformers (`all-MiniLM-L6-v2`, 384-dim) | `hashing` (zero-dep) / `openai` / `voyage` |

Missing a dependency degrades gracefully (e.g. hashing embedder) rather than crashing.

---

## Status

Real and verified end-to-end on a 50-PDF corpus: change detection, per-class
recipes, real PDF extraction + OCR + embeddings, bounded chunking (no silent
truncation), inline checks, provenance tracing. **Deliberately not built yet:**
an LLM-backed recipe author (currently deterministic templates) and cloud
connectors (only local filesystem so far). See `FEATURES.md`.

---

## Repo conventions

This repo uses a lightweight file-based workflow: `PROJECT.md` (vision),
`AGENTS.md` (how we work here), `FEATURES.md` (build list), per-feature plans in
`features/<slug>/IP.md`, session logs in `sessions/`, and git hooks that block
secrets/failing tests and link sessions to commits. See [`WORKFLOW.md`](WORKFLOW.md).

## License

MIT — see [LICENSE](LICENSE).
