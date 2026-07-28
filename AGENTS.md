# AGENTS.md

> Always loaded into context (via `CLAUDE.md → @AGENTS.md`). This is how the
> agent should work on THIS project. Keep it lean: a wrong instruction is worse
> than no instruction. When the agent repeats a mistake, add one line here —
> don't write an essay.
>
> _Replace everything below with your project's reality, then delete this
> quote block._

## What this is

<!-- One or two sentences. What is the product, and what's the hard part?
     Point to PROJECT.md for the full overview. -->

## Stack

- **Frontend:** <!-- e.g. Next.js (App Router), TypeScript, Tailwind -->
- **Backend:** <!-- e.g. FastAPI (Python) -->
- **Database:** <!-- e.g. Postgres via SQLAlchemy + Alembic; SQLite locally -->
- **Other:** <!-- LLM APIs, queues, etc. -->

## Commands

```
# run          <!-- e.g. npm run dev  /  uvicorn app.main:app --reload -->
# test         <!-- e.g. npm test     /  pytest -->
# typecheck    <!-- e.g. npm run type-check -->
# checks       ./scripts/run-checks.sh   # env-aware (APP_ENV=development|test|production)
```

## Conventions

- <!-- e.g. Business logic in services/, not route handlers. -->
- <!-- e.g. No `any` in TypeScript; components under ~200 lines. -->
- <!-- e.g. Money is integer cents or Decimal, never float. -->
- <!-- e.g. Dates stored UTC, displayed local. -->

## Non-negotiables

1. <!-- The rules that must never be broken — the ones where a wrong call is a
        real-world mistake. Keep this list short and real. -->

## How we work here

- Plan each feature in `features/<slug>/IP.md` **before** writing code.
- Review output against the IP's acceptance criteria — not "the tests pass".
- Scope changed? Append to the IP's changelog. Don't rewrite the IP.
- End every session with a summary in `sessions/`.
- Repeated mistake? Add a line to this file, same session.
