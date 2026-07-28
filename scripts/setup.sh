#!/usr/bin/env bash
# setup.sh — activate the workflow's git hooks. Run once after cloning.
set -euo pipefail
cd "$(dirname "$0")/.."

git config core.hooksPath .githooks
chmod +x .githooks/* scripts/*.sh 2>/dev/null || true

echo "✓ Hooks activated (core.hooksPath = .githooks)"
echo "    pre-commit  → blocks secrets, failing tests, anti-patterns"
echo "    post-commit → stamps the commit hash into your session file"
echo
echo "Next:"
echo "  1. Edit PROJECT.md, AGENTS.md, FEATURES.md"
echo "  2. Wire your commands in scripts/run-checks.sh"
echo "  3. Plan a feature:  cp -r features/_template features/<slug>"
