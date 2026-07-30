#!/usr/bin/env bash
# approve_proposal.sh <name> <priority> [project_root]
# Appends an approved proposal to proposal-approved.md.
# Uses state.sh::append_approved helper.

set -euo pipefail

NAME="$1"
PRIORITY="${2:-P1}"
PROJECT_ROOT="${3:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" 2>/dev/null && pwd)"
LIB_DIR="$SCRIPT_DIR/../../_lib"

# Source state.sh for append_approved
if [ -f "$LIB_DIR/state.sh" ]; then
  source "$LIB_DIR/state.sh"
else
  echo "❌ state.sh not found at $LIB_DIR/state.sh" >&2
  exit 1
fi

# Check if approved file exists
APPROVED_FILE="$PROJECT_ROOT/proposal-approved.md"
if [ ! -f "$APPROVED_FILE" ]; then
  echo "❌ proposal-approved.md not found at $APPROVED_FILE" >&2
  echo "   请确保 proposal-approved.md 已创建" >&2
  exit 1
fi

# check_archived <name> <project_root>
# Returns 0 if change is already archived, 1 otherwise.
check_archived() {
  local cname="$1"
  local proot="${2:-.}"
  # Match archive pattern: YYYY-MM-DD-<name>
  if ls -d "$proot/openspec/changes/archive/"*"-$cname" 2>/dev/null | grep -q .; then
    return 0
  fi
  return 1
}

# Check if improvement file exists
IMP_FILE="$PROJECT_ROOT/improvements/$NAME.md"
if [ ! -f "$IMP_FILE" ]; then
  echo "❌ improvement file not found: $IMP_FILE" >&2
  exit 1
fi

# Skip if already archived: auto-approve to completed section
if check_archived "$NAME" "$PROJECT_ROOT"; then
  mark_approved_completed "$PROJECT_ROOT" "$NAME"
  exit 0
fi

# Append to approved list
append_approved "$PROJECT_ROOT" "$NAME" "$PRIORITY"
