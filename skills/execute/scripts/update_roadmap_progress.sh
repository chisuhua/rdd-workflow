#!/usr/bin/env bash
# skills/_lib/update_roadmap_progress.sh — extracted from execute.md L296-L346
# Exports: update_roadmap_progress <change_name>
#
# Updates .rddf/state/roadmap-state.json to mark a change as completed.
# Reads roadmap-meta.yaml to determine phase/category, then updates the
# state file's completed_changes and all_changes_complete gate status.
#
# Oracle C1 safe: all values flow through os.environ — no bash string
# interpolation into Python source code.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" 2>/dev/null && pwd)"

if [ -f "$SCRIPT_DIR/change_name.sh" ]; then
  source "$SCRIPT_DIR/change_name.sh"
fi

update_roadmap_progress() {
  local CHANGE_NAME="${1:-${CHANGE_NAME:-}}"

  if [ -z "$CHANGE_NAME" ]; then
    if ! ensure_change_name; then
      echo "⚠️  update_roadmap_progress: CHANGE_NAME is required" >&2
      return 0  # Non-fatal
    fi
    CHANGE_NAME="${CHANGE_NAME:-}"
  fi

  PROJECT_ROOT="${PROJECT_ROOT:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
  export PROJECT_ROOT
  export CHANGE_NAME

  # Guard: skip if roadmap-meta.yaml doesn't exist (matches original behavior)
  if [ ! -f "$PROJECT_ROOT/openspec/changes/$CHANGE_NAME/roadmap-meta.yaml" ]; then
    return 0  # Non-fatal skip
  fi

  python3 "$SCRIPT_DIR/update_roadmap_progress_env.py"
}