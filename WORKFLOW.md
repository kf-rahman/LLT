# How a feature gets built

The full loop, start to finish. See [`README.md`](README.md) for the overview
of the six components.

```
                    HOW A FEATURE GETS BUILT
                    ─────────────────────────

  ┌─────────────────────────────────────────────────┐
  │  PROJECT.md + FEATURES.md + AGENTS.md            │
  │  loaded automatically at session start           │
  └──────────────────────┬──────────────────────────┘
                         │
         ┌───────────────▼────────────────────────────┐
         │  cp -r features/_template features/<slug>   │
         │  fill in features/<slug>/IP.md:             │
         │   · Goal (from the user's point of view)    │
         │   · Data model changes                      │
         │   · API contract                            │
         │   · UI states (loading, empty, error, done) │
         │   · Acceptance criteria (testable)          │
         │   · Open questions — flag, don't assume     │
         └───────────────┬────────────────────────────┘
                         │
         ┌───────────────▼────────────────────────────┐
         │  "Implement features/<slug>/IP.md"          │
         │  (+ load the QA skill if focus is on tests) │
         │  single session works from the IP contract  │
         └───────────────┬────────────────────────────┘
                         │
         ┌───────────────▼────────────────────────────┐
         │  you review against the IP's criteria       │
         │   · agent made a mistake?                   │
         │       → add ONE line to AGENTS.md           │
         │   · scope changed?                          │
         │       → append to the IP changelog          │
         └───────────────┬────────────────────────────┘
                         │
         ┌───────────────▼────────────────────────────┐
         │  "write a session summary"                  │
         │   → sessions/YYYY-MM-DD-<slug>.md           │
         │   what was done · decided · didn't work ·   │
         │   what's next                               │
         └───────────────┬────────────────────────────┘
                         │
         ┌───────────────▼────────────────────────────┐
         │  git commit  (session file + code together) │
         │                                             │
         │  pre-commit hook:                           │
         │   · blocks secrets / API keys / .env        │
         │   · blocks failing tests (run-checks test)  │
         │   · blocks project-specific anti-patterns   │
         │   · warns if no session file is staged      │
         │                                             │
         │  post-commit hook:                          │
         │   · stamps the commit hash into the session │
         │                                             │
         │  mark the feature `complete` in FEATURES.md │
         └───────────────┬────────────────────────────┘
                         │
         ┌───────────────▼────────────────────────────┐
         │  next session opens and immediately knows:  │
         │   sessions/<last>.md    → what's next       │
         │   features/<slug>/IP.md → what's left       │
         │   AGENTS.md             → any new rules      │
         └─────────────────────────────────────────────┘
```

## Notes on each step

**Planning (`IP.md`) is not optional.** The plan is what replaces a subagent
pipeline — it constrains scope — and what replaces a memory protocol — it's the
persisted record of what was decided. Skipping it is where agents wander.

**You are the reviewer.** The workflow deliberately keeps all judgment with the
human. "The tests pass" is not "it's done" — done is "it meets the acceptance
criteria in the IP". That's exactly what the QA skill enforces when tests are
being written.

**Corrections compound.** A repeated agent mistake becomes one line in
`AGENTS.md`, so it's fixed for every future session — not re-explained each
time. Keep `AGENTS.md` lean; prune rules that no longer apply.

**The session log is the handoff.** The next session (yours tomorrow, or a
collaborator's) starts by reading the latest `sessions/*.md`, the active
`IP.md`, and `AGENTS.md`. If those three don't orient someone in two minutes,
tighten them.
