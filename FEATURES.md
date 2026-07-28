# FEATURES.md

The master list of everything to build. One flat list that stays honest — no
ticket system. Update the status as you go; it's the source of truth for
"what's left".

**Status:** `planned` · `in-progress` · `complete` · `deferred`

Built in dependency order: the persistence spine first, then change detection,
then classification/recipes, then execution, then the orchestrator that wires
them, then eval and tracing.

| # | Feature | Status | IP | Notes |
|---|---------|--------|----|-------|
| 1 | Core data model & stores (documents SQLite table, recipe store) | in-progress | `features/data-model-and-stores/IP.md` | the persistence spine |
| 2 | Change detection (identity lookup: new / modified / unchanged) | planned | `features/change-detection/IP.md` | Layer 1 |
| 3 | Connector & event emission (local filesystem, pluggable interface) | planned | `features/connector/IP.md` | v1 = local FS |
| 4 | Classification / signature detection (deterministic, no LLM) | planned | `features/classification/IP.md` | Layer 2 signature |
| 5 | Recipe lookup & authoring (hit → run; miss → sub-agent authors) | planned | `features/recipes/IP.md` | agent stubbed first |
| 6 | Tool registry & executor (plan execution + region routing) | planned | `features/executor/IP.md` | deterministic tools |
| 7 | Orchestrator (wires the full flow + memory write-back steps) | planned | `features/orchestrator/IP.md` | the core loop |
| 8 | Inline "usable" check (recipe-defined checks; gate the corpus) | planned | `features/inline-eval/IP.md` | eval v1, tiny |
| 9 | Tracing / provenance log (append-only JSONL; OTel later) | planned | `features/tracing/IP.md` | episodic memory |
| 10 | Corpus store (chunks/embeddings; delete-old-on-modify) | planned | `features/corpus/IP.md` | semantic memory |
| 11 | Retrieval / query API | deferred | — | after ingestion is solid |
| 12 | Ingestion-layer permissions → retrieval enforcement | deferred | — | **future**; schema leaves room now |
| 13 | Rich eval: drift detection → re-reason, recipe A/B on golden set | deferred | — | grows the inline check into Sentinel |
| 14 | Real tools (OCR, table extraction, embeddings) behind interfaces | deferred | — | v1 may stub these |
| 15 | Observability substrate (OpenTelemetry → Arize Phoenix) | deferred | — | adopt, don't build |

<!--
Conventions:
- Keep build-order numbering; the IP column points to features/<slug>/IP.md once planned.
- Don't delete completed rows — a finished list is a changelog of the build.
- "deferred" means "decided not now, on purpose" (note why). It is not "todo".
-->
