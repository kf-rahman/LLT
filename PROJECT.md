# PROJECT.md

## One-liner

An **agentic ingestion engine**: point it at a data source and it keeps a
searchable corpus continuously and correctly in sync — inspecting each item,
deciding how to process it, remembering that decision, and tracing everything —
so that setting up a RAG system becomes "point your data here and ingestion is
completely accounted for."

## The problem

Existing RAG stacks have *static* ingestion: you hand-configure one pipeline
(this parser, this chunker) and it runs the same way for everything. Real data
sources are heterogeneous (scanned PDFs, tables, images, CSVs, mixed documents)
and they *change over time*. The result is brittle: mixed content is mangled,
re-syncs duplicate data, and when a chunk is wrong there is no way to find out
why it was produced. Nobody can trust the corpus.

## What makes this different: agentic ingestion

Ingestion decisions are made **per data class by an agent, once**, captured as a
reusable **recipe**, and then executed **deterministically** for every item of
that class. The agent is the expensive part and runs rarely (only for genuinely
novel data shapes); deterministic tools do the bulk of the work. Every decision
and every execution is traced, and the system remembers what it did so an update
becomes a clean delta, not a blind re-ingest.

## The flow (the core loop)

```
point at data source ─► connector lists items ─► emit one EVENT per item
        │
   LAYER 1 — DOCUMENT (identity = source + path), SQLite `documents` table
        │   look the item up by path, compare content hash:
        ├─ unchanged  → SKIP (idempotent: re-syncs cost ~nothing)
        ├─ new        → insert row, continue
        └─ modified   → update row + DELETE old chunks, continue   (reprocess/replace)
        │
   LAYER 2 — CLASS (type signature), recipe store
        │   classify the item CHEAPLY (deterministic signals, no LLM):
        │     signature = {text_layer?, tables?, scanned?, ...} → class key
        │   look up the recipe for that class:
        ├─ HIT   → run the recipe's plan (deterministic tools, no LLM)
        └─ MISS  → spawn sub-agent → it authors a recipe ONCE → save it → run it
        │
   EXECUTE — run the recipe plan; a plan can fan out by region
        │     (table regions → table extractor; text regions → chunk+embed)
        │
   UPDATE MEMORY — write-back step:
        │     • if a new recipe was authored → write recipe store
        │     • upsert `documents` row {path, hash, class, recipe_id, trace_id, status}
        │
   CHECK ("usable") — run the recipe's own `checks`:
        ├─ pass → commit chunks to corpus, set status=complete
        └─ fail → discard output, log trace with ok=false (nothing bad enters corpus)
        │
   TRACE — every decision + tool run emitted as spans (→ Phoenix later)
```

### Worked example

- `invoice_jan.pdf` (scanned, image-only) arrives, never seen → MISS → agent
  authors recipe `scanned-pdf@1` = `[ocr, chunk, embed, store]`; runs it.
- `invoice_feb.pdf` (also scanned) → class HIT → runs `scanned-pdf@1`, **no agent**.
- `invoice_jan.pdf` re-uploaded, edited → identity known, hash differs →
  **modified** → delete old chunks, reprocess with `scanned-pdf@1`.
- `invoice_jan.pdf` re-uploaded, identical → hash matches → **skip**.
- A PDF with **text + tables** → signature `{text_layer, tables}` → its own class
  `pdf__text+tables`; the recipe's plan routes table regions to a table extractor
  and text regions to chunk+embed. One recipe, multiple tools, no per-item LLM.

## Memory model (four tiers, distinct stores)

| Tier | What it is here | Store |
|---|---|---|
| **Procedural** — "how to process class X" | the **recipes** (plan + checks) | recipe store (JSON per class) |
| **Episodic** — "what happened to item Y" | the **trace log** | append-only JSONL |
| **Semantic** — "facts from the data" | the **corpus** (chunks/embeddings) | vector / relational store |
| **Working** — this reasoning turn only | sub-agent scratch context | in-memory, discarded |

The two stores the hot path touches are kept small: **documents** (one row per
item, keyed by path) and **recipes** (one entry per class). They are separate on
purpose — one recipe serves many documents, so documents *reference* a recipe by
`recipe_id` rather than copying it (normalized; a recipe change is one write).

## Classification & the agent's judgment

Classifying a *known* shape needs **no LLM** — cheap deterministic detectors
(text-layer present? tables detected? image-only?) produce a signature → class.
The **LLM (sub-agent) is invoked only on a novel signature**, and only to author
the recipe once. After that, the cheap classifier routes every future item of
that shape to the saved recipe. (Grounding: LLM cascades / FrugalGPT — pay for
reasoning only when confidence is low; agent decides once, tools execute forever.)

## Eval (v1: deliberately tiny)

A single **inline "usable" check** per item, defined *by the recipe* (each recipe
carries its own `checks`, e.g. `chunks == pages`, `text_nonempty`). Pass → commit
to corpus; fail → discard + log. No scoring, no LLM-judge yet. Richer eval
(sampled quality checks, drift detection → re-reason, recipe A/B on a golden set)
is deferred — see future notes.

## What "done" looks like (v1)

- Point the engine at a local source; it ingests every item, choosing/authoring
  a recipe per class and recording it.
- Re-running the sync is **idempotent**: unchanged items are skipped, modified
  items are reprocessed with old chunks replaced, new items are added.
- Every item has a `documents` row linking it to the exact `recipe_id`, a
  `trace_id`, and a `status`; every decision/run is in the trace log.
- A failing "usable" check keeps bad output out of the corpus.

## Explicitly out of scope (for now)

- **Retrieval/query API** beyond a minimal read of the corpus — the query side is
  a later feature.
- **Rich eval**: drift detection, re-reasoning triggers, recipe regression/A-B.
- **Cloud connectors** (S3, Drive, Notion) — v1 uses a local-filesystem connector;
  the connector interface is designed so these slot in later.
- **Real OCR/embedding models** are behind tool interfaces and may be stubbed in
  v1; the contract is what matters first.
- **Multi-tenant / permissions** — see the future note.

## Future notes

- **Permissions in the ingestion layer (for retrieval).** We want to capture,
  *at ingest time*, who is allowed to see each item, and carry that through to the
  corpus, so that at **retrieval** time we can enforce "this user may see this
  document." The access facts belong on the item/chunk records written during
  ingestion. **Not in this version** — but the `documents`/corpus schema should
  leave room for an `acl` / `visibility` field so we don't have to backfill later.
- **Eval → drift → re-reason loop.** Later, the inline check grows into a
  Sentinel policy layer: sampled quality eval + concept-drift detection that fires
  a *re-reason* trigger (agent revises the recipe → new version → regression-eval
  vs the old recipe on a golden set before promotion).
- **Observability substrate.** Emit OpenTelemetry spans and adopt Arize Phoenix
  for traces/dashboards rather than building our own store; Sentinel stays our
  domain policy on top.

## Links

- Workflow reference: [`WORKFLOW.md`](WORKFLOW.md)
- Architecture background: *Dive into Claude Code: The Design Space of Today's and
  Future AI Agent Systems* (arXiv:2604.14228) — orchestrator loop, context
  compaction, memory tiers.
- Grounding: FrugalGPT (arXiv:2305.05176); semantic caching (GPTCache); *Build
  Systems à la Carte* (incremental recompute); *A Survey on Concept Drift
  Adaptation* (Gama et al.); *Provenance in Databases: Why, How, and Where*.
- Reference systems: R2R (SciPhi) — ingestion + agentic retrieval; Onyx — source
  connectors + continuous sync; Letta (MemGPT) — memory tiers.
