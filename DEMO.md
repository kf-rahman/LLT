# DEMO — Readwise as an aggregation source

> Working doc for the demo. Goal: show how our ingestion engine plugs into an
> **aggregation tool (Readwise)** and turns a user's aggregated content into a
> searchable, always-in-sync, accountable RAG corpus — with zero pipeline setup.
> Branch: `demo`. Pick up from "Build plan".

## The narrative

A Readwise user aggregates articles, PDFs, tweets, and highlights from everywhere
into one pile. We point our engine at their Readwise account and it turns that
pile into a **queryable, incrementally-synced, traceable knowledge corpus**. When
they save or edit something in Readwise, a webhook fires and we ingest just that
item (idempotent — unchanged items skip, edits reprocess, deletes remove).

Pitch to any aggregation-tool user: *"your aggregated content becomes an
intelligent RAG corpus automatically, and every answer traces back to its source."*

## Feasibility — verified (2026-07-29)

Readwise has a real, documented, token-auth API. Two relevant surfaces:

**Reader API** (`/api/v3/`) — the read-later app. **This is the one we use.**
- `GET https://readwise.io/api/v3/list/` — list documents.
  - **`withHtmlContent=true` returns `html_content`** (full article text) ← the
    key: we can ingest real content, not just metadata.
  - Filters: `updatedAfter` (ISO-8601), `location`, `category`, `tag`, `limit`
    (1–100), `pageCursor` pagination.
  - Standard fields: `id, url, source_url, title, author, category, location,
    tags, site_name, word_count, created_at, updated_at, notes, summary, ...`
  - Rate limit: **20 req/min**.
- `POST https://readwise.io/api/v3/save/` — save a document (not needed for demo).

**Highlights API** (`/api/v2/`) — books/Kindle/article highlights (bonus stream).
- `GET https://readwise.io/api/v2/export/` → books + highlights (`text, note,
  tags, source, ...`), `updatedAfter` incremental. Rate limit 20/min.

**Webhooks** — real-time notifications on document/highlight **create/update/delete**.

Auth: header `Authorization: Token XXX` (token from https://readwise.io/access_token).

Docs: [Reader API](https://readwise.io/reader_api) ·
[Highlights API](https://readwise.io/api_deets) ·
[Webhooks](https://docs.readwise.io/readwise/docs/webhooks)

### Pricing
- **Free 30-day trial, no credit card** — full Reader + API access. Enough to
  build and demo end-to-end for free.
- After trial (no permanent free tier): full plan (incl. Reader) **$9.99/mo**
  annual / **$12.99/mo** monthly. *Lite ($5.59/mo) excludes Reader — not usable.*
  Student: 50% off.

## Why it maps ~1:1 to our architecture

| Readwise | Our engine |
|---|---|
| `GET /api/v3/list/?withHtmlContent=true` | `ReadwiseConnector` → one `IngestEvent` per doc (bytes = `html_content`) |
| `updatedAfter` incremental filter | our idempotent change detection (new/modified/unchanged) |
| webhooks (create/update/delete) | our event trigger — ingest just that item |
| document `id` | our identity key (Layer 1) |

Nothing in the core pipeline changes. Two small, in-scope additions needed.

## Build plan (pick up here)

1. **`ingestor/connectors/readwise.py` — `ReadwiseConnector`** implementing the
   existing `Connector` protocol:
   - `list_events()` → `GET /api/v3/list/?withHtmlContent=true`, paginate on
     `nextPageCursor`, yield an `IngestEvent` per doc:
     - `path = f"readwise://{doc['id']}"` (identity)
     - `read = lambda: html_content.encode()`
     - `content_hash = sha256(html_content)` (drives modified-detection)
     - `mime = "text/html"`
   - Accept `updated_after` to fetch only changed docs (incremental sync).
   - Token from `READWISE_TOKEN` env (add to `.env.example`).
   - Respect the 20 req/min limit (simple sleep/backoff on 429 + `Retry-After`).
2. **HTML processing path**:
   - `classify.py`: add `kind == "html"` (mime `text/html`) → class key `html`.
   - `tools.py`: add an `extract_html` tool (strip tags → clean text; consider a
     lib like `selectolax`/`beautifulsoup4`, or a minimal regex strip to stay
     dep-light). Register it.
   - `recipes.py`: add a default `html` recipe:
     `[extract_html, chunk, embed, store]`, checks `[chunks > 0, text_nonempty]`.
3. **(Optional) Highlights stream**: a second connector over `/api/v2/export/`
   yielding one event per book (concatenated highlight text) → class `highlights`.
4. **(Optional) Webhook trigger**: a tiny endpoint that, on a Readwise webhook,
   runs `ingest_event` for the changed doc id — the live "edit → re-ingest" moment.

Reuses everything else unchanged: idempotency, recipe memory, bounded chunking,
inline check, corpus, tracing.

## User setup (do before the live demo)
1. Start the **free Readwise trial**; add ~10–20 articles/PDFs to **Reader**.
2. Generate a token at https://readwise.io/access_token → `export READWISE_TOKEN=...`.
3. (Optional) Configure a webhook to our endpoint for the live update moment.

## Demo script (the live flow)
1. `ingestor ingest-readwise` → watch it pull docs, classify `html`, build a real
   embedded corpus. Show counts + a sample extracted chunk.
2. Re-run → **everything skips** (idempotent). Show the "0 committed" summary.
3. Edit/add one item in Readwise → re-run (or webhook) → **only that item
   reprocesses**; old chunks replaced.
4. Open `traces.jsonl` / a document row → **provenance**: this chunk came from
   this Readwise doc, via this recipe, at this time.
5. (If retrieval is added later) ask a question → grounded answer with a link
   back to the Readwise source.

## Caveats to be honest about in the demo
- Reader requires a plan that includes Reader (trial covers it).
- 20 req/min list limit — fine for a demo corpus, respect at scale.
- HTML cleanliness varies by source; the `extract_html` tool must clean it.
- Recipe author is still hand-coded templates (the `html` recipe is a template),
  not an LLM — don't oversell "the agent reasons about Readwise data."

## Status
Planned. Corresponds to a future FEATURES.md row ("Readwise connector + HTML
path"). Build on this `demo` branch; merge to `main`/`feat` when working.
