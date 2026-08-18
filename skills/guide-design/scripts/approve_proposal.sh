#!/usr/bin/env bash
# approve_proposal.sh <name> <priority> [project_root]
#
# Appends an approved proposal to proposal-approved.md (existing behavior).
# Then, when SKIP_DESIGN_HANDOFF is not set, creates the openspec change:
#   - openspec/changes/<name>/ with .openspec.yaml + full proposal.md
#   - roadmap-meta.yaml containing change_type (parsed from .rddf/improvements head)
#   - iteration.json planned entry
#
# Idempotency: if openspec/changes/<name>/ already exists, the create flow
# is skipped (no overwrite).
#
# Env vars:
#   SKIP_DESIGN_HANDOFF=yes    -> skip create flow (legacy / skeleton path)
#   PARENT_FEATURE              -> optional, written to roadmap-meta.yaml

set -euo pipefail

# Cross-repo approval gate (ADR-0031)
CROSS_REPO_CATEGORY="cross-repo-federation"
AUTO_ACCEPT=false
MANUAL_FLAG=false
HUB_ISSUE_ARG=""

# Argument parsing: collect flags, leaving NAME and PRIORITY as positional
_remaining_args=()
while [[ $# -gt 0 ]]; do
  case "$1" in
    --auto-accept) AUTO_ACCEPT=true; shift ;;
    --manual) MANUAL_FLAG=true; shift ;;
    --hub-issue)
      HUB_ISSUE_ARG="$2"
      shift 2 ;;
    --hub-issue=*)
      HUB_ISSUE_ARG="${1#*=}"
      shift ;;
    --) shift; break ;;
    -*) shift ;;
    *) _remaining_args+=("$1"); shift ;;
  esac
done
set -- "${_remaining_args[@]}" "$@"

NAME="${1:-}"
PRIORITY="${2:-P1}"
PROJECT_ROOT="${3:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" 2>/dev/null && pwd)"
LIB_DIR="$SCRIPT_DIR/../../_lib"

detect_cross_repo_category() {
  local proposal_name="$1"
  # SSOT (ADR-0031 §分类传递契约): .rddf/improvements/<name>.md `**分类**:` head field.
  # roadmap-meta.yaml is created by THIS script later in the flow, so reading it
  # here is fail-open on first approve (Oracle C2). Do not use it as the source.
  local imp_file="$PROJECT_ROOT/.rddf/improvements/$proposal_name.md"
  if [[ ! -f "$imp_file" ]]; then
    return 1
  fi
  head -8 "$imp_file" | grep -oE '\*\*分类\*\*:[ \t]*[^|]+' | head -1 | sed 's/.*\*\*分类\*\*:[ \t]*//' | xargs
}

is_cross_repo_proposal() {
  local cat
  cat=$(detect_cross_repo_category "$1" 2>/dev/null || echo "")
  [[ "$cat" == "$CROSS_REPO_CATEGORY" ]]
}

# Append one entry to .rddf/state/.cross-repo-audit.jsonl via cross_repo_audit.
# Args: <decision> ; reads ACTOR / NAME / HUB_ISSUE_ARG / HUB_STATE / HUB_LABELS.
_write_cross_repo_audit() {
  local decision="$1"
  AUDIT_PATH="$PROJECT_ROOT/.rddf/state/.cross-repo-audit.jsonl" \
  AUDIT_LIB="$LIB_DIR" \
  AUDIT_ACTOR="$ACTOR" \
  AUDIT_PROPOSAL="$NAME" \
  AUDIT_HUB_ISSUE="$HUB_ISSUE_ARG" \
  AUDIT_DECISION="$decision" \
  AUDIT_HUB_STATE="$HUB_STATE" \
  AUDIT_HUB_LABELS="$HUB_LABELS" \
  python3 - <<'PYEOF'
import os, sys
from datetime import datetime, timezone
sys.path.insert(0, os.environ["AUDIT_LIB"])
from cross_repo_audit import append_audit_log_entry
labels = [l for l in os.environ.get("AUDIT_HUB_LABELS", "").split(",") if l]
append_audit_log_entry(os.environ["AUDIT_PATH"], {
    "timestamp": datetime.now(timezone.utc).isoformat(),
    "proposal_name": os.environ["AUDIT_PROPOSAL"],
    "hub_issue": os.environ["AUDIT_HUB_ISSUE"],
    "approver": os.environ["AUDIT_ACTOR"],
    "actor": os.environ["AUDIT_ACTOR"],
    "decision": os.environ["AUDIT_DECISION"],
    "hub_state": os.environ.get("AUDIT_HUB_STATE", "unknown"),
    "hub_labels": labels,
})
PYEOF
}

# Cross-repo gate: block --auto-accept, require --manual + --hub-issue
if is_cross_repo_proposal "$NAME" 2>/dev/null; then
  if [ "${AUTO_ACCEPT}" = true ]; then
    echo "🚫 cross-repo proposal '$NAME' cannot use --auto-accept" >&2
    echo "   Use --manual --hub-issue <org/repo#N> instead" >&2
    exit 3
  fi
  if [ "$MANUAL_FLAG" != true ]; then
    echo "🚫 cross-repo proposal '$NAME' requires --manual flag" >&2
    exit 3
  fi
  if [ -z "$HUB_ISSUE_ARG" ]; then
    echo "🚫 cross-repo proposal requires --hub-issue <org/repo#N>" >&2
    exit 3
  fi

  # --- ADR-0031 §实现细节 3: interactive GitHub username (30s timeout) ---
  # CI fallback: RDDF_APPROVE_ACTOR env var (non-interactive terminals).
  ACTOR="${RDDF_APPROVE_ACTOR:-}"
  if [ -z "$ACTOR" ]; then
    _username=""
    read -t 30 -rp "GitHub username: " _username || true
    ACTOR="$_username"
  fi
  if [ -z "$ACTOR" ]; then
    echo "🚫 cross-repo approval requires a non-empty GitHub username" >&2
    echo "   (empty input or 30s timeout; set RDDF_APPROVE_ACTOR for non-interactive use)" >&2
    exit 4
  fi

  # --- ADR-0031 §实现细节 5: Hub Issue re-fetch before local approve ---
  HUB_REPO_PART="${HUB_ISSUE_ARG%%#*}"
  HUB_ISSUE_NUM="${HUB_ISSUE_ARG##*#}"
  if [ "$HUB_REPO_PART" = "$HUB_ISSUE_ARG" ] || [ -z "$HUB_ISSUE_NUM" ]; then
    echo "🚫 invalid --hub-issue format, expected <org/repo#N>: $HUB_ISSUE_ARG" >&2
    exit 3
  fi
  HUB_STATE="unknown"
  HUB_LABELS=""
  set +e
  HUB_FETCH_OUT=$(HUB_REPO_PART="$HUB_REPO_PART" HUB_ISSUE_NUM="$HUB_ISSUE_NUM" python3 - <<'PYEOF'
import json, os, subprocess, sys
repo = os.environ["HUB_REPO_PART"]
num = os.environ["HUB_ISSUE_NUM"]
try:
    r = subprocess.run(
        ["gh", "issue", "view", num, "--repo", repo, "--json", "state,labels"],
        capture_output=True, text=True, timeout=20,
    )
except FileNotFoundError:
    sys.exit(10)  # gh CLI missing -> network-class fail-open
except subprocess.TimeoutExpired:
    sys.exit(10)  # timeout -> network-class fail-open
if r.returncode != 0:
    err = (r.stderr or "").lower()
    if "auth" in err or "401" in err or "403" in err or "forbidden" in err:
        sys.exit(11)  # auth-class -> fail-closed
    sys.exit(10)  # network-class -> fail-open
try:
    data = json.loads(r.stdout or "{}")
except json.JSONDecodeError:
    sys.exit(10)
state = (data.get("state") or "").upper()
labels = ",".join(str(l.get("name", "")) for l in data.get("labels", []) if isinstance(l, dict))
print(f"{state}\t{labels}")
PYEOF
)
  HUB_FETCH_RC=$?
  set -e

  _hub_check_failed=no
  case "$HUB_FETCH_RC" in
    0)
      HUB_STATE="${HUB_FETCH_OUT%%$'\t'*}"
      HUB_LABELS="${HUB_FETCH_OUT#*$'\t'}"
      if [ "$HUB_STATE" != "OPEN" ] || ! printf '%s' ",$HUB_LABELS," | grep -q ",approved,"; then
        _hub_check_failed=yes
      fi
      ;;
    10)
      echo "⚠️  WARNING: Hub Issue re-fetch failed (network class); proceeding fail-open" >&2
      ;;
    *)
      echo "🚫 Hub Issue re-fetch failed (auth class); refusing to approve" >&2
      _hub_check_failed=yes
      ;;
  esac

  if [ "$_hub_check_failed" = yes ]; then
    # audit the rejected decision before refusing
    _write_cross_repo_audit "fail" || true
    if [ "${RDDF_REQUIRE_HUB_APPROVAL:-no}" = "yes" ]; then
      echo "🚫 RDDF_REQUIRE_HUB_APPROVAL=yes: Hub Issue '$HUB_ISSUE_ARG' not in approved state (exit 5)" >&2
      exit 5
    fi
    echo "🚫 Hub Issue '$HUB_ISSUE_ARG' not approved (state=$HUB_STATE labels=$HUB_LABELS) (exit 6)" >&2
    exit 6
  fi

  # --- ADR-0031 §实现细节 4: audit log write BEFORE accept ---
  _write_cross_repo_audit "approve"
fi

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
IMP_FILE="$PROJECT_ROOT/.rddf/improvements/$NAME.md"
if [ ! -f "$IMP_FILE" ]; then
  echo "❌ improvement file not found: $IMP_FILE" >&2
  exit 1
fi

# Skip if already archived: auto-approve to completed section
if check_archived "$NAME" "$PROJECT_ROOT"; then
  mark_approved_completed "$PROJECT_ROOT" "$NAME"
  exit 0
fi

# Per wire-design-content-review-gate: invoke .rddf/improvements-layer content
# review via the shared helper BEFORE any approve-side-effect. The helper
# honors STRICT_DESIGN_GATE / SKIP_CONTENT_REVIEW and propagates the
# review's exit code (0 pass/warn, 1 blocking). In default mode warnings
# allow approve to continue; in STRICT mode blocking aborts.
SCRIPT_DIR_LOCAL="$(cd "$(dirname "${BASH_SOURCE[0]}")" 2>/dev/null && pwd)"
if [ -x "$SCRIPT_DIR_LOCAL/run_content_review.sh" ]; then
  export IMPROVEMENTS_PATH="$IMP_FILE"
  set +e
  bash "$SCRIPT_DIR_LOCAL/run_content_review.sh"
  review_rc=$?
  set -e
  unset IMPROVEMENTS_PATH
  if [ "$review_rc" -eq 1 ]; then
    echo "❌ design content review blocked approve (STRICT_DESIGN_GATE or default blocking)" >&2
    exit 1
  fi
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
HEAD_FEATURE=""
if [ -f "$IMP_FILE" ]; then
  # Restrict to first 8 lines: body often mentions these field names as examples.
  HEAD_SECTION="$(head -8 "$IMP_FILE")"
  if echo "$HEAD_SECTION" | grep -qE '\*\*阶段\*\*:[ \t]*[^|]+'; then
    HEAD_PHASE=$(echo "$HEAD_SECTION" | grep -oE '\*\*阶段\*\*:[ \t]*[^|]+' | head -1 | sed 's/.*\*\*阶段\*\*:[ \t]*//' | xargs)
  fi
  if echo "$HEAD_SECTION" | grep -qE '\*\*分类\*\*:[ \t]*[^|]+'; then
    HEAD_CATEGORY=$(echo "$HEAD_SECTION" | grep -oE '\*\*分类\*\*:[ \t]*[^|]+' | head -1 | sed 's/.*\*\*分类\*\*:[ \t]*//' | xargs)
  fi
  if echo "$HEAD_SECTION" | grep -qE '\*\*类型\*\*:[ \t]*[^|]+'; then
    HEAD_TYPE=$(echo "$HEAD_SECTION" | grep -oE '\*\*类型\*\*:[ \t]*[^|]+' | head -1 | sed 's/.*\*\*类型\*\*:[ \t]*//' | xargs)
  fi
  if echo "$HEAD_SECTION" | grep -qE '\*\*特性\*\*:[ \t]*[^|]+'; then
    HEAD_FEATURE=$(echo "$HEAD_SECTION" | grep -oE '\*\*特性\*\*:[ \t]*[^|]+' | head -1 | sed 's/.*\*\*特性\*\*:[ \t]*//' | xargs)
  fi
fi

PARENT_FEATURE="${PARENT_FEATURE:-$HEAD_FEATURE}"

# Validate parent_feature against existing features (validate-feature-name)
# Warning by default (non-blocking), STRICT_FEATURE_VALIDATION=yes exits with code 2
if [ -n "$PARENT_FEATURE" ] && [ "$PARENT_FEATURE" != "__ungrouped__" ]; then
  set +e
  PROJECT_ROOT_VAL="$PROJECT_ROOT" \
  PARENT_FEATURE_VAL="$PARENT_FEATURE" \
  STRICT_FEATURE_VALIDATION_VAL="${STRICT_FEATURE_VALIDATION:-}" \
  python3 - "$PROJECT_ROOT" "$PARENT_FEATURE" <<'PYEOF'
import os
import sys
from pathlib import Path
sys.path.insert(0, os.path.join(sys.argv[1], "skills", "propose", "scripts"))
from propose_change import _collect_existing_features
existing = _collect_existing_features(sys.argv[1])
pf = sys.argv[2]
strict = os.environ.get("STRICT_FEATURE_VALIDATION_VAL", "") == "yes"
if pf and pf not in existing:
    listed = sorted(existing)[:10]
    suffix = f" (and {len(existing) - 10} more)" if len(existing) > 10 else ""
    msg = (
        f"⚠️  parent_feature='{pf}' not in existing features {listed}{suffix}. "
        f"Possible typo — verify spelling or use an existing feature name."
    )
    print(msg, file=sys.stderr)
    sys.exit(2 if strict else 0)
PYEOF
  rc=$?
  set -e
  if [ "$rc" -eq 2 ]; then
    echo "❌ parent_feature validation blocked approve (STRICT_FEATURE_VALIDATION=yes)" >&2
    exit 2
  fi
fi

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
