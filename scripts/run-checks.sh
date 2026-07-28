#!/usr/bin/env bash
# run-checks.sh — environment-aware checks. Wire the TODOs to your stack.
#
#   ./scripts/run-checks.sh [lint|typecheck|test|all]
#
# With no argument it picks a sensible set based on APP_ENV
# (development | test | production). The functions are no-ops until you fill
# them in, so a fresh clone never fails.
set -euo pipefail
cd "$(dirname "$0")/.."

APP_ENV="${APP_ENV:-development}"
target="${1:-}"

lint()      { :; }   # TODO: wire a linter (e.g. ruff) when we adopt one
typecheck() { :; }   # TODO: wire mypy/pyright when we adopt one

tests() {
  command -v python3 >/dev/null 2>&1 || { echo "python3 not found; skipping tests"; return 0; }
  # `|| code=$?` keeps `set -e` from aborting before we inspect the exit code.
  local code=0
  python3 -m pytest -q || code=$?
  # exit 5 = "no tests collected yet" — not a failure during early scaffolding.
  [ "$code" -eq 5 ] && return 0
  return "$code"
}

run() { echo "▶ $1"; "$1"; }

if [ -n "$target" ]; then
  case "$target" in
    lint)      run lint ;;
    typecheck) run typecheck ;;
    test)      run tests ;;
    all)       run lint; run typecheck; run tests ;;
    *) echo "unknown target: $target" >&2; exit 2 ;;
  esac
  exit 0
fi

echo "APP_ENV=$APP_ENV"
case "$APP_ENV" in
  development) run typecheck ;;
  test)        run typecheck; run tests ;;
  production)  run lint; run typecheck; run tests ;;
  *) echo "unknown APP_ENV: $APP_ENV" >&2; exit 2 ;;
esac
