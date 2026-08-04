#!/usr/bin/env bash
# skills/execute/scripts/run_regression_gate.sh
# Unified full-regression gate for the execute phase.
# Exports: run_regression_gate
# Honors SKIP_REGRESSION=1.
# If tests/KNOWN_FAILURES.txt and tests/scripts/report_regression.sh exist,
# run the baseline-aware report; otherwise fall back to plain recursive bats.

set -u

run_regression_gate() {
  if [ "${SKIP_REGRESSION:-}" = "1" ]; then
    printf '%s\n' '⏭  SKIP_REGRESSION=1，跳过全量回归门'
    return 0
  fi

  local SCRIPT_DIR REPO_ROOT
  SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
  REPO_ROOT="${PROJECT_ROOT:-$(cd "$SCRIPT_DIR/../.." && pwd)}"

  if [ -f "$REPO_ROOT/tests/KNOWN_FAILURES.txt" ] && [ -f "$REPO_ROOT/tests/scripts/report_regression.sh" ]; then
    printf '%s\n' '🔍 全量回归门 (baseline 对比)...'
    (cd "$REPO_ROOT" && bash "$REPO_ROOT/tests/scripts/report_regression.sh")
  else
    printf '%s\n' '🔍 全量回归门 (bats tests/ --recursive)...'
    (cd "$REPO_ROOT" && bats tests/ --recursive)
  fi
}

# Run directly when invoked, no-op when sourced
if [ "${BASH_SOURCE[0]:-$0}" = "${0}" ]; then
  run_regression_gate "$@"
fi