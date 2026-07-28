# IP — Tool registry & executor

- **Slug:** `executor`
- **Status:** planned
- **FEATURES.md row:** #6

## Goal

Run a recipe's `plan` deterministically: resolve each step to a registered tool,
execute in order, and support **region routing** (a plan can send table regions
to a table extractor and text regions to chunk+embed). Produces the artifacts
(chunks) that the check gates and the corpus stores.

## Data model changes

None. Introduces `Tool` (a named, versioned deterministic function) and an
`ExecutionResult` carrying produced chunks + metrics.

## API contract

- `ToolRegistry.register(name, fn)`, `ToolRegistry.get(name)`.
- Tool signature: `fn(ctx, **params) -> ctx'` (threads a mutable execution context
  holding bytes, extracted text, regions, chunks).
- `execute(recipe, event, registry) -> ExecutionResult`.
- Plan step forms: a plain tool step `{tool, ...params}` or a route step
  `{route: {<region_type>: [steps...]}}`.
- v1 tools may be **stubs** (e.g. `ocr` returns placeholder text, `embed` returns
  zero-vectors) — real implementations land later behind the same names.

## UI states

N/A. Execution outcomes: produced chunks / raised error (recorded, not crashing
the whole run).

## Acceptance criteria

- [ ] A linear plan `[ocr, chunk, embed, store]` runs each tool once, in order.
- [ ] A route step dispatches each region type to its sub-steps.
- [ ] An unregistered tool name fails clearly (named error), does not silently pass.
- [ ] The result exposes the produced chunks so the inline check can inspect them.
- [ ] No LLM is invoked in execution.

## Open questions

- [ ] Parallel vs serial execution — v1 serial; the read-parallel/write-serial
      optimization is deferred.

---

## Changelog

- **2026-07-28** — Created.
