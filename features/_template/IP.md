# IP — <Feature name>

> **Implementation Plan.** Write this *before* touching code. It's the contract
> the session builds against, and the persisted record of what was decided.
> Copy this folder: `cp -r features/_template features/<slug>`.
>
> When scope changes or an approach doesn't work, **append a Changelog entry at
> the bottom** — do not rewrite the sections above. The history is the point.

- **Slug:** `<slug>`
- **Status:** planned <!-- planned | in-progress | complete | deferred -->
- **FEATURES.md row:** #<n>

## Goal

<!-- From the user's point of view, in one or two sentences. What can they do
     after this ships that they couldn't before? Not "add a table" — rather
     "an admin can export the week's orders as a CSV". -->

## Data model changes

<!-- New/changed tables, columns, types, migrations. "None" is a valid answer.
     Be explicit about money (integer cents / Decimal) and time (UTC). -->

## API contract

<!-- Endpoints or functions this adds/changes: method, path, request shape,
     response shape, error cases. This is what the frontend builds against. -->

## UI states

Design for all four — not just the happy path:

- **Loading:** <!-- what the user sees while it works -->
- **Empty:** <!-- no data yet -->
- **Error:** <!-- it failed — what's shown, what can they do -->
- **Done / success:** <!-- the happy path -->

## Acceptance criteria

Testable, checkable statements. These are what "complete" means — and what the
QA skill writes tests against (the criteria, not the implementation).

- [ ] <!-- e.g. Submitting a valid order returns 201 and persists the raw text. -->
- [ ] <!-- e.g. An invalid order shows an inline error and loses nothing. -->
- [ ] <!-- e.g. ... -->

## Open questions

Flag anything ambiguous here instead of assuming. The human answers these
before (or during) the build.

- [ ] <!-- e.g. Should delivery date be required, or inferred from the text? -->

---

## Changelog

_Append-only. Newest at the bottom. Dated. Record what changed and why._

- **YYYY-MM-DD** — Created.
