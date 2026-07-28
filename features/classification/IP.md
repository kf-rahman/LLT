# IP — Classification / signature detection (Layer 2)

- **Slug:** `classification`
- **Status:** planned
- **FEATURES.md row:** #4

## Goal

Cheaply (no LLM) compute a **signature** of an item's structure and derive a
**class key** from it. The class key is what the recipe lookup uses. A novel
signature (no recipe yet) is what triggers the agent.

## Data model changes

None. Produces `Signature` (a set of boolean/enumerable structural facts) and a
`class_key` string.

## API contract

- `detect_signature(event) -> Signature`, e.g.
  `{ kind: "pdf", text_layer: bool, tables: bool, scanned: bool }` or
  `{ kind: "csv" }`, `{ kind: "image" }`.
- `class_key_of(signature) -> str`, a stable string, e.g. `pdf__text+tables`,
  `scanned-pdf`, `csv`, `image`.
- Detectors are deterministic and cheap. v1 may use MIME + light heuristics and
  stub deep detectors (real table detection) behind the same interface.

## UI states

N/A.

## Acceptance criteria

- [ ] Same input ⇒ same signature ⇒ same class key (deterministic, stable).
- [ ] A scanned/image-only PDF and a text PDF get *different* class keys.
- [ ] A PDF with both text and tables maps to a distinct `pdf__text+tables` key.
- [ ] Class key is filesystem-safe (usable as a recipe filename).
- [ ] No LLM is invoked anywhere in this module.

## Open questions

- [ ] How rich should v1 signatures be? Start minimal (mime + text_layer + tables
      + scanned); expand as real detectors land.

---

## Changelog

- **2026-07-28** — Created.
