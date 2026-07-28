# Agentic Workflow Starter

A lightweight, file-based workflow for building software with a coding agents. 

The idea: your project's plan, conventions, and history live in **plain
markdown committed next to the code**, not in chat history. A new session (or a
new collaborator) gets fully oriented by reading a handful of files.

---

## The six components

| File / dir | What it's for |
|---|---|
| **`PROJECT.md`** | High-level overview — who the users are, what "done" looks like, what's explicitly out of scope. First thing a new session reads. |
| **`FEATURES.md`** | The master list of everything to build, with a status per item (`planned` / `in-progress` / `complete` / `deferred`). No Jira — a flat list that stays honest. |
| **`AGENTS.md`** | How the agent should work: your stack, conventions, non-negotiables. **Always loaded** (`CLAUDE.md` just imports it). Keep it lean — a wrong instruction is worse than none. |
| **`features/<slug>/IP.md`** | A per-feature **Implementation Plan**, written *before* any code. Goal, data model, API contract, UI states, acceptance criteria, open questions. Scope changes are **appended as a changelog**, never rewritten. |
| **`sessions/YYYY-MM-DD-<slug>.md`** | A session summary written at the **end of every session** — what was done, decided, what didn't work, what's next. Committed with the code; the post-commit hook stamps the real commit hash into it. |
| **`.githooks/` + QA skill** | Enforcement. `pre-commit` blocks secrets, failing tests, and anti-patterns; `post-commit` links the session to its commit; `run-checks.sh` is environment-aware. The **QA skill** loads only when you're writing tests. |

See [`WORKFLOW.md`](WORKFLOW.md) for the full "how a feature gets built" walkthrough.

---

## Quick start

```bash
# 1. Use this template (or clone it) as your new project
git clone https://github.com/kf-rahman/Agentic-Workflow.git my-project
cd my-project
rm -rf .git && git init            # start your own history

# 2. Activate the git hooks (they live in .githooks/, tracked in the repo)
./scripts/setup.sh

# 3. Make it yours — fill in the three always-on files
$EDITOR PROJECT.md      # what you're building & for whom
$EDITOR AGENTS.md       # your stack, conventions, non-negotiables
$EDITOR FEATURES.md     # the list of what to build
```

Then build features one at a time (see below).

---

## The loop, in one screen

```
1. Pick the next item in FEATURES.md, set it to `in-progress`.

2. Plan it:   cp -r features/_template features/<slug>
              $EDITOR features/<slug>/IP.md      # fill in the contract

3. Build it:  ask the agent → "Implement features/<slug>/IP.md"
              (single session works from the IP as the contract)

4. Review it against the IP's acceptance criteria — you are the reviewer.
              · agent repeats a mistake?  → add ONE line to AGENTS.md
              · scope changed?            → append to the IP's changelog

5. Log it:    "write a session summary"  → sessions/YYYY-MM-DD-<slug>.md

6. Commit code + session file together.
              · pre-commit blocks secrets / failing tests / anti-patterns
              · post-commit stamps the commit hash into the session file
              · mark the feature `complete` in FEATURES.md
```

---

## Why

This was created as part of a research experitment to really understand agentic workflows. After comparing a few workflows we found this workflow to be a realistinc one.
If you want to learn more about the other workflows that we had explored and the findings here is the full blogpost https://kf-rahman.github.io/OneMLLab/post.html?slug=vibing-the-perfect-agentic-workflow

## License

MIT — see [LICENSE](LICENSE). Use it, fork it, make it yours.
