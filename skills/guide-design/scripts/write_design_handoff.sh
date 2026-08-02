#!/usr/bin/env bash
# skills/guide-design/scripts/write_design_handoff.sh
# Exports: write_design_handoff() [v2 — emits changes_pre_created array]
#
# Writes .rddf/state/.design-handoff.json via the Python helper.
# Oracle C1: env-var only passing, no bash string interpolation into python.
#
# Usage:
#   write_design_handoff <proposals_reviewed> [change_names...]
# Or with env var:
#   CHANGES_PRE_CREATED="name1,name2" write_design_handoff 3
#
# v2 schema requires changes_pre_created: [...]. Callers MUST pass change names
# (either as positional args or via CHANGES_PRE_CREATED env var).

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" 2>/dev/null && pwd)"

write_design_handoff() {
  local proposals_reviewed="${1:-0}"
  shift || true
  PROJECT_ROOT="${PROJECT_ROOT:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"

  if [ "$#" -gt 0 ]; then
    CHANGES_PRE_CREATED="$(IFS=','; echo "$*")"
  fi
  CHANGES_PRE_CREATED="${CHANGES_PRE_CREATED:-}"
  export PROJECT_ROOT PROPOSALS_REVIEWED="$proposals_reviewed" CHANGES_PRE_CREATED

  mkdir -p "$PROJECT_ROOT/.rddf/state"
  python3 "$SCRIPT_DIR/write_design_handoff.py"
}

# Direct execution (not sourced)
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
  write_design_handoff "${@:-0}"
fi