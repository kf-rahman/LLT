# AGENTS.md

## What this is

An **agentic ingestion engine**. Point it at a data source; it classifies each
item, chooses or authors a **recipe** (how to process that class), executes the
recipe deterministically, remembers what it did, and traces everything. The hard
part is making ingestion *idempotent, incremental, and accountable* — not the
model calls. See [`PROJECT.md`](PROJECT.md) for the full flow.

## Stack

- **Language:** Python 3.11+ (3.13 locally)
- **Persistence:** SQLite (`documents` table) via stdlib `sqlite3`; recipes as
  JSON files in `recipes/`; trace log as append-only JSONL.
- **Models/validation:** dataclasses (stdlib) for core types; keep deps minimal.
- **Agent/LLM:** Anthropic (Claude) for recipe authoring — behind an interface,
  stubbed until wired. Default to the latest capable Claude model.
- **Tests:** pytest.

## Commands

```
# run        python -m ingestor.cli ingest <source_dir>
# test       python -m pytest -q
# checks     ./scripts/run-checks.sh   # env-aware (APP_ENV=development|test|production)
```

## Conventions

- **Deterministic by default; LLM only on a miss.** Classification and execution
  never call an LLM. The agent runs only to author a recipe for a novel class.
- **Recipes are per-class; documents reference them by `recipe_id`.** Never inline
  a recipe into a document row (avoids the one-recipe-many-docs update anomaly).
- **Two lookups, in order:** (1) document by path → new/modified/unchanged;
  (2) class signature → recipe hit/miss. Keep them separate.
- **A recipe is a plan (list of tool calls) + its own `checks`.** "Usable" is
  defined by the recipe, not globally. Execution walks the plan; it may route by
  region (tables vs text).
- **Idempotency is sacred.** Re-syncing must not duplicate. Unchanged → skip;
  modified → delete old chunks then reprocess; new → insert.
- **Everything is traced.** Every decision and tool run appends to the trace log
  with the item's `trace_id`. The trace log is append-only; never edit past lines.
- Keep the hot-path stores (documents, recipes) small; the trace log is the only
  thing that grows unbounded (compact/tier it later, never in the lookup path).
- Money/time conventions N/A yet; when added, money = integer cents, time = UTC.

## Non-negotiables

1. **Nothing enters the corpus unless its recipe's `checks` pass.** A failed check
   discards output and logs `ok:false` — it must never write partial/garbage chunks.
2. **A modified item must delete its old chunks before writing new ones** — never
   leave two versions of the same document in the corpus.
3. **No LLM call in the steady-state (recipe-hit) path.** If you find yourself
   calling a model to process a known class, that's a bug.

## How we commit (session resilience)

We commit **constantly and in small, self-contained pieces** so that if a session
ends abruptly the next one resumes cleanly. Rules:

- **Every change is assigned to a commit.** Don't leave work uncommitted at the
  end of a step. If it's worth doing, commit it.
- **Small and comprehensible.** One logical change per commit (one module, one
  behavior, one doc), with a message that explains *why*, not just *what*.
- **Commit early, commit often.** Prefer many small commits over one large one;
  it makes an interrupted session trivial to pick up (`git log` is the handoff).
- Use conventional prefixes: `feat:`, `fix:`, `docs:`, `chore:`, `test:`,
  `refactor:`. Scope them, e.g. `feat(recipes): ...`.
- The pre-commit hook blocks secrets and failing tests; the post-commit hook links
  session logs to commit hashes. Let them do their job — don't bypass with
  `--no-verify` unless a hook is demonstrably wrong.

## How we work here

- Plan each feature in `features/<slug>/IP.md` **before** writing code.
- Review output against the IP's acceptance criteria — not "the tests pass".
- Scope changed? Append to the IP's changelog. Don't rewrite the IP.
- End every session with a summary in `sessions/`.
- Repeated mistake? Add a line to this file, same session.
