#!/usr/bin/env bash
# skills/_lib/plan_deps_candidates.sh — extracted from guide-plan.md L451-L488
# Exports: generate_deps_candidates()
#
# Writes .rddf/state/.deps-candidates.json containing all committed changes.
# Honors Oracle C1: bash wrapper passes env vars only, no string interpolation.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" 2>/dev/null && pwd)"

generate_deps_candidates() {
  PROJECT_ROOT="${PROJECT_ROOT:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
  export PROJECT_ROOT
  mkdir -p "$PROJECT_ROOT/.rddf/state"
  python3 "$SCRIPT_DIR/plan_deps_candidates_env.py"
}