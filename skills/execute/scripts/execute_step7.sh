#!/usr/bin/env bash
# _lib/execute_step7.sh — extracted from execute.md L195-L282
# Exports: run_step7_report()
#
# Step 7 final report after change execution:
# - Reads tasks.md progress (done/total)
# - Syncs iteration.json (graceful on failure)
# - Prints next-step instructions
# - Lists other worktrees (porcelain-format parsing)
#
# Oracle C1 safe: all values flow through os.environ — no bash string
# interpolation into Python source code.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" 2>/dev/null && pwd)"

if [ -f "$SCRIPT_DIR/change_name.sh" ]; then
  source "$SCRIPT_DIR/change_name.sh"
fi

run_step7_report() {
  PROJECT_ROOT="${PROJECT_ROOT:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
  export PROJECT_ROOT
  if ensure_change_name; then
    export CHANGE_NAME
  else
    export CHANGE_NAME=""
  fi
  python3 "$SCRIPT_DIR/execute_step7_env.py"
}
