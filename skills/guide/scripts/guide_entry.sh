#!/usr/bin/env bash
# skills/guide/scripts/guide_entry.sh — extracted from guide.md v2.0 L45-L108
# Provides: guide_entry() function (pure source-able library)
#
# Why this exists:
#   The original code block embedded in skills/guide/SKILL.md had two latent
#   bugs when AI copies it into a `bash -c "..."` invocation:
#     1. `source "$(dirname "$(readlink -f "${BASH_SOURCE[0]:-$0}")")/..."`
#        fails because BASH_SOURCE[0] is empty in `bash -c` context and
#        $0 resolves to "bash" → readlink returns /usr/bin/bash → wrong path.
#     2. The `if RECO_JSON=$(...); then ... fi` was rendered in markdown
#        without the `if` keyword, leaving a bare `then` that triggers
#        `syntax error near unexpected token 'then'`.
#
#   Extracting to this script makes the SKILL.md a thin "how to call" doc
#   (~15 lines) and gives AI a single robust entry point that handles
#   path resolution via a 4-tier fallback (env var → BASH_SOURCE → /proc →
#   walk-up from cwd).
#
# Usage (AI / wrapper):
#   SKILL_DIR=/path/to/skills/guide \
#     bash -c 'source "$SKILL_DIR/scripts/guide_entry.sh" && guide_entry'
#
#   SKILL_DIR=/path/to/skills/guide \
#     bash -c 'source "$SKILL_DIR/scripts/guide_entry.sh" && guide_entry --json'
#
#   SKILL_DIR=/path/to/skills/guide \
#     bash -c 'source "$SKILL_DIR/scripts/guide_entry.sh" && guide_entry --no-binding'
#
# Usage (manual shell):
#   source /path/to/skills/guide/scripts/guide_entry.sh
#   guide_entry                       # human-readable state overview
#   guide_entry --json                # append JSON block (scripts-friendly)
#   guide_entry --no-binding          # skip rddf-session binding scan
#   guide_entry --help                # this help
#
# Outputs (exported as env vars after guide_entry runs):
#   RECOMMEND         — e.g. "guide-ship"
#   REASON            — Chinese explanation
#   CONFIDENCE        — high / medium / low
#   ALL_OPTIONS_JSON  — JSON array of all menu options
#   WT_ISSUES_JSON    — JSON array of worktree cleanliness issues (may be [])
#   BINDING_LINES     — bash array of session binding messages (set by
#                       scan_session_binding; empty if --no-binding)

set -euo pipefail

# ---------------------------------------------------------------------------
# Path resolution — handles `bash -c` invocation where BASH_SOURCE[0] is empty
# ---------------------------------------------------------------------------
_resolve_skill_dir() {
  # Tier 1: explicit SKILL_DIR env var (set by AI / wrapper / install.sh)
  if [ -n "${SKILL_DIR:-}" ] && [ -f "$SKILL_DIR/scripts/scan-state.sh" ]; then
    printf '%s\n' "$SKILL_DIR"
    return 0
  fi

  # Tier 2: BASH_SOURCE[0] (wrapper / sourced invocation)
  local src="${BASH_SOURCE[0]:-}"
  if [ -n "$src" ] && [ "$src" != "bash" ] && [ -e "$src" ]; then
    (cd "$(dirname "$src")/.." && pwd)
    return 0
  fi

  # Tier 3: $0 (rare; only valid if invoked as `bash /full/path/to/script.sh`)
  if [ -n "${0:-}" ] && [ "$0" != "bash" ] && [ -e "$0" ]; then
    (cd "$(dirname "$(readlink -f "$0" 2>/dev/null || echo "$0")")/.." && pwd)
    return 0
  fi

  # Tier 4: walk up from cwd to find scan-state.sh (last-resort heuristic)
  local d
  d="$(pwd)"
  while [ "$d" != "/" ]; do
    if [ -f "$d/skills/guide/scripts/scan-state.sh" ]; then
      printf '%s\n' "$d/skills/guide"
      return 0
    fi
    d="$(dirname "$d")"
  done

  return 1
}

SKILL_DIR="$(_resolve_skill_dir)"
if [ -z "$SKILL_DIR" ] || [ ! -f "$SKILL_DIR/scripts/scan-state.sh" ]; then
  echo "ERROR: cannot locate skills/guide directory." >&2
  echo "       Set SKILL_DIR=/path/to/skills/guide or run from a repo where" >&2
  echo "       skills/guide/scripts/scan-state.sh exists." >&2
  return 1 2>/dev/null || exit 1
fi
export SKILL_DIR

# Source the scanner library
# shellcheck source=scripts/scan-state.sh
source "$SKILL_DIR/scripts/scan-state.sh"

# ---------------------------------------------------------------------------
# Main entry: scan + synthesize + render
# ---------------------------------------------------------------------------
guide_entry() {
  local OUTPUT_JSON=0
  local NO_BINDING=0

  case "${1:-}" in
    --help|-h)
      cat <<'EOF'
guide_entry 用法:
  source $SKILL_DIR/scripts/guide_entry.sh && guide_entry                # 人类可读
  source $SKILL_DIR/scripts/guide_entry.sh && guide_entry --json         # JSON
  source $SKILL_DIR/scripts/guide_entry.sh && guide_entry --no-binding   # 跳过 binding
  source $SKILL_DIR/scripts/guide_entry.sh && guide_entry --help         # 此帮助

CLI 一行调用:
  SKILL_DIR=/path/to/skills/guide \
    bash -c 'source "$SKILL_DIR/scripts/guide_entry.sh" && guide_entry'

Outputs (env vars):
  RECOMMEND, REASON, CONFIDENCE, ALL_OPTIONS_JSON, WT_ISSUES_JSON
  BINDING_LINES (bash array, set by scan_session_binding)
EOF
      return 0 2>/dev/null || exit 0
      ;;
    --json)       OUTPUT_JSON=1; NO_BINDING=1 ;;
    --no-binding) NO_BINDING=1 ;;
    *)            OUTPUT_JSON=0; NO_BINDING=0 ;;
  esac

  local PROJECT_ROOT
  PROJECT_ROOT=$(git rev-parse --show-toplevel 2>/dev/null || pwd)

  scan_state "$PROJECT_ROOT"

  # v2.1: structured recommendation from workflow_synthesizer (read-only)
  RECO_JSON=""
  ALL_OPTIONS_JSON=""
  WT_ISSUES_JSON='[]'

  if command -v python3 >/dev/null 2>&1; then
    RECO_JSON=$(PY_PROJECT_ROOT="$PROJECT_ROOT" python3 -c '
import json, os, sys
from dataclasses import asdict
sys.path.insert(0, os.environ["PY_PROJECT_ROOT"])
from skills._lib.workflow_synthesizer import synthesize
r = synthesize(os.environ["PY_PROJECT_ROOT"])
print(json.dumps({
    "suggested_action": r.suggested_action,
    "reason": r.reason,
    "confidence": r.confidence,
    "unblocked_changes": list(r.unblocked_changes),
    "active_session": r.active_session,
    "orphaned_sessions": list(r.orphaned_sessions),
    "all_options": [
        {"id": o.id, "label": o.label, "description": o.description,
         "action": o.action, "group": o.group}
        for o in r.all_options
    ],
    "wt_issues": [asdict(i) for i in r.wt_issues],
}))
' 2>/dev/null) || RECO_JSON=""

    if [ -n "$RECO_JSON" ]; then
      ALL_OPTIONS_JSON=$(printf '%s' "$RECO_JSON" \
        | python3 -c 'import json,sys; print(json.dumps(json.load(sys.stdin)["all_options"]))')
      WT_ISSUES_JSON=$(printf '%s' "$RECO_JSON" \
        | python3 -c 'import json,sys; print(json.dumps(json.load(sys.stdin).get("wt_issues", [])))' 2>/dev/null || echo '[]')
      RECOMMEND=$(printf '%s' "$RECO_JSON" \
        | python3 -c 'import json,sys; print(json.load(sys.stdin)["suggested_action"])')
      REASON=$(printf '%s' "$RECO_JSON" \
        | python3 -c 'import json,sys; print(json.load(sys.stdin)["reason"])')
      CONFIDENCE=$(printf '%s' "$RECO_JSON" \
        | python3 -c 'import json,sys; print(json.load(sys.stdin)["confidence"])')
      export RECOMMEND REASON CONFIDENCE ALL_OPTIONS_JSON WT_ISSUES_JSON
    fi
  fi

  # Print project state overview (for AI + user visibility)
  echo "📋 Workflow Entry - $(basename "$PROJECT_ROOT")"
  echo "   ───────────────────────────────────────────"
  echo "   roadmap.md: $([ -f "$PROJECT_ROOT/roadmap.md" ] && echo '✅' || echo '❌')"
  echo "   .arch-handoff.json: $([ -f "$PROJECT_ROOT/.rddf/state/.arch-handoff.json" ] && echo '✅' || echo '❌')"
  echo "   .plan-handoff.json: $([ -f "$PROJECT_ROOT/.rddf/state/.plan-handoff.json" ] && echo '✅' || echo '❌')"

  # Ensure state.sh helpers are available (scan-state.sh may have skipped sourcing)
  type -t detect_approved_inconsistency &>/dev/null || source "$PROJECT_ROOT/skills/_lib/state.sh"
  # Audit trail protection: flag suggestions marked "completed" without an approved record
  detect_approved_inconsistency "$PROJECT_ROOT" 2>/dev/null || true

  if [ "$NO_BINDING" -eq 0 ]; then
    scan_session_binding "$PROJECT_ROOT"
  fi

  # JSON output for scripting consumers
  if [ "$OUTPUT_JSON" -eq 1 ] && [ -n "$RECO_JSON" ]; then
    echo "---BEGIN_RECO_JSON---"
    printf '%s' "$RECO_JSON"
    echo ""
    echo "---END_RECO_JSON---"
  fi
}