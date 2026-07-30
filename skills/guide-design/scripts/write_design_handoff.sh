#!/usr/bin/env bash
# skills/guide-design/scripts/write_design_handoff.sh
# Exports: write_design_handoff()
#
# Writes .rddf/state/.design-handoff.json via the Python helper.
# Oracle C1: env-var only passing, no bash string interpolation into python.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" 2>/dev/null && pwd)"

write_design_handoff() {
  local proposals_reviewed="${1:-0}"
  PROJECT_ROOT="${PROJECT_ROOT:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
  export PROJECT_ROOT PROPOSALS_REVIEWED="$proposals_reviewed"

  mkdir -p "$PROJECT_ROOT/.rddf/state"
  python3 "$SCRIPT_DIR/write_design_handoff.py"
}

# Direct execution (not sourced)
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
  write_design_handoff "${1:-0}"
fi