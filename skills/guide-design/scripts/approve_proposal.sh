#!/usr/bin/env bash
# approve_proposal.sh <name> <priority> [project_root]
#
# Appends an approved proposal to proposal-approved.md (existing behavior).
# Then, when SKIP_DESIGN_HANDOFF is not set, creates the openspec change:
#   - openspec/changes/<name>/ with .openspec.yaml + full proposal.md
#   - roadmap-meta.yaml containing change_type (parsed from improvements head)
#   - iteration.json planned entry
#
# Idempotency: if openspec/changes/<name>/ already exists, the create flow
# is skipped (no overwrite).
#
# Env vars:
#   SKIP_DESIGN_HANDOFF=yes    -> skip create flow (legacy / skeleton path)
#   PARENT_FEATURE              -> optional, written to roadmap-meta.yaml

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

# Auto-stage proposal-approved.md so the design-phase write is never lost
# across the plan-phase commit boundary. fail-fast on git error.
if ! git add "$APPROVED_FILE" 2>/dev/null; then
  echo "❌ git add proposal-approved.md failed: $?" >&2
  exit 1
fi
echo "git add proposal-approved.md done"

# Skip create flow on legacy / skeleton path
if [ "${SKIP_DESIGN_HANDOFF:-no}" = "yes" ]; then
  exit 0
fi

CHANGE_DIR="$PROJECT_ROOT/openspec/changes/$NAME"
if [ -d "$CHANGE_DIR" ]; then
  echo "⏭  change dir already exists: $CHANGE_DIR (skipping create)"
  exit 0
fi

mkdir -p "$CHANGE_DIR"

cat > "$CHANGE_DIR/.openspec.yaml" <<EOF
name: $NAME
created_by: guide-design approve
EOF

CHANGE_NAME="$NAME" IMPROVEMENTS_PATH="$IMP_FILE" \
    python3 "$SCRIPT_DIR/generate_full_proposal.py" \
    > "$CHANGE_DIR/proposal.md" 2>/dev/null || {
    echo "⚠️  generate_full_proposal.py failed; falling back to skeleton" >&2
    cat > "$CHANGE_DIR/proposal.md" <<EOF
# $NAME

## Why

(Generated from $IMP_FILE)

## What Changes

**In Scope**: TBD

**Out of Scope**: TBD

## Capabilities

TBD

## Impact

TBD

## Acceptance

- [ ] TBD
EOF
}

HEAD_PHASE="default"
HEAD_CATEGORY="general"
HEAD_TYPE="feature"
if [ -f "$IMP_FILE" ]; then
  if grep -qE '\*\*阶段\*\*:\s*[^|]+' "$IMP_FILE"; then
    HEAD_PHASE=$(grep -oE '\*\*阶段\*\*:\s*[^|]+' "$IMP_FILE" | head -1 | sed 's/.*\*\*阶段\*\*:\s*//' | xargs)
  fi
  if grep -qE '\*\*分类\*\*:\s*[^|]+' "$IMP_FILE"; then
    HEAD_CATEGORY=$(grep -oE '\*\*分类\*\*:\s*[^|]+' "$IMP_FILE" | head -1 | sed 's/.*\*\*分类\*\*:\s*//' | xargs)
  fi
  if grep -qE '\*\*类型\*\*:\s*[^|]+' "$IMP_FILE"; then
    HEAD_TYPE=$(grep -oE '\*\*类型\*\*:\s*[^|]+' "$IMP_FILE" | head -1 | sed 's/.*\*\*类型\*\*:\s*//' | xargs)
  fi
fi

PARENT_FEATURE="${PARENT_FEATURE:-}"
cat > "$CHANGE_DIR/roadmap-meta.yaml" <<EOF
phase: $HEAD_PHASE
category: $HEAD_CATEGORY
change_type: $HEAD_TYPE
priority: $PRIORITY
parent_feature: "$PARENT_FEATURE"
EOF

ITERATION_FILE="$PROJECT_ROOT/.rddf/state/iteration.json"
if [ -f "$ITERATION_FILE" ]; then
  python3 - <<PYEOF
import json
import os
from pathlib import Path
p = Path("$ITERATION_FILE")
data = json.loads(p.read_text()) if p.exists() else {"version": 1, "changes": []}
data["changes"] = [c for c in data.get("changes", []) if c.get("name") != "$NAME"]
data["changes"].append({
    "name": "$NAME",
    "status": "planned",
    "phase": "$HEAD_PHASE",
    "category": "$HEAD_CATEGORY",
    "added_at": __import__("time").strftime("%Y-%m-%dT%H:%M:%S%z"),
})
p.write_text(json.dumps(data, indent=2))
PYEOF
fi

echo "✅ change created: $CHANGE_DIR (phase=$HEAD_PHASE, category=$HEAD_CATEGORY, type=$HEAD_TYPE)"
