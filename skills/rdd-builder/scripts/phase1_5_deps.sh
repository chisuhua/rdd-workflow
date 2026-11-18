#!/usr/bin/env bash
# Phase 1.5: Deps + execution_mode decision.
# Exit 6 if STRICT_DEPS_GATE FAIL.
set -euo pipefail

CHANGE_NAME="${1:-}"
PROJECT_ROOT="${PROJECT_ROOT:-$(pwd)}"

AUTO_APPROVE=0
for arg in "$@"; do
    case "$arg" in
        --auto-approve) AUTO_APPROVE=1 ;;
    esac
done
export AUTO_APPROVE

if [ -z "$CHANGE_NAME" ]; then
    echo "phase1_5_deps.sh requires <change-name>" >&2
    exit 2
fi

echo "=== Phase 1.5: Deps + Execution Mode Decision for $CHANGE_NAME ==="

# Legacy plan-handoff execution_mode (v3 residue). It has no writer in v4,
# so it can only ever contradict the computed decision: it is read for the
# WARNING below and NEVER overrides (lowest priority — see
# fix-execution-mode-decision AC "LEGACY_EXEC_MODE").
LEGACY_EXEC_MODE=""
if [ -f "$PROJECT_ROOT/.rddf/state/.plan-handoff.json" ]; then
    LEGACY_EXEC_MODE=$(python3 -c "
import json
data = json.load(open('$PROJECT_ROOT/.rddf/state/.plan-handoff.json'))
print(data.get('execution_mode_decisions', {}).get('$CHANGE_NAME', {}).get('mode', ''))
" 2>/dev/null || echo "")
fi

# Resolve the rdd-workflow package root — the directory that CONTAINS
# `_lib/`. It is NOT the project root: in a user project `_lib/` lives under
# the installed package. (Same order as phase2_execute.sh / phase3_archive.sh.)
_resolve_pkg_root() {
  local c here
  here="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
  if [ -d "$here/_lib" ]; then
    printf '%s' "$here"
    return 0
  fi
  for c in \
    "$PROJECT_ROOT/.opencode/skills/rdd-workflow" \
    "$HOME/.agents/skills/rdd-workflow" \
    "$HOME/.agents/skills"
  do
    if [ -n "$c" ] && [ -d "$c/_lib" ]; then
      printf '%s' "$c"
      return 0
    fi
  done
  return 1
}
PKG_ROOT="$(_resolve_pkg_root || true)"

PKG_ROOT="$PKG_ROOT" python3 <<PYEOF
import os
import sys
PKG_ROOT = os.environ.get("PKG_ROOT") or ""
if PKG_ROOT:
    sys.path.insert(0, PKG_ROOT)
sys.path.insert(0, os.path.abspath("$PROJECT_ROOT"))
from _lib.builder_deps import (
    decide_execution_mode, compute_mode_inputs, compute_conflict,
    analyze_deps, analyze_deps_with_strict_gate,
)
from _lib.builder_handoff import update_builder_handoff

PROJECT_ROOT = os.path.abspath("$PROJECT_ROOT")
CHANGE_NAME = "$CHANGE_NAME"

manual_deps = []
meta_path = os.path.join(PROJECT_ROOT, "openspec", "changes", CHANGE_NAME, "roadmap-meta.yaml")
if os.path.exists(meta_path):
    try:
        import yaml
        with open(meta_path, encoding="utf-8") as f:
            meta = yaml.safe_load(f) or {}
        manual_deps = meta.get("manual_deps", []) or []
    except Exception:
        pass

# Real inputs, computed from absolute paths (the decision must not depend on
# the cwd): tasks.md checkbox total, the plan's "**Files:**" paths and the
# structured "risk:" declaration.
#
# NOTE: this heredoc is UNQUOTED on purpose (it interpolates $PROJECT_ROOT and
# $CHANGE_NAME) — so backticks in the python block would be executed by bash.
# Keep them out of this block.
inputs = compute_mode_inputs(PROJECT_ROOT, CHANGE_NAME)

decision = decide_execution_mode(
    file_count=inputs["file_count"],
    task_count=inputs["task_count"],
    risk_keywords=inputs["risk_keywords"],
)

# The reason states the ACTUAL input values and what was unavailable —
# never a constant (fix-execution-mode-decision).
notes = list(inputs["notes"])
conflicts = compute_conflict(PROJECT_ROOT, CHANGE_NAME)
if conflicts:
    decision = {
        "mode": "worktree",
        "reason": (decision["reason"] or "no rule fired") + " AND conflict: " + "; ".join(conflicts),
    }
if notes:
    decision["reason"] = decision["reason"] + " | " + "; ".join(notes)

# Legacy plan-handoff execution_mode: LOWEST priority — it never overrides the
# computed decision, it only warns (v4 has no writer for that field).
legacy = "$LEGACY_EXEC_MODE"
if legacy in ("worktree", "lightweight"):
    print(
        "⚠️  legacy .plan-handoff.json execution_mode='%s' 已忽略"
        "（v4 残留，无写入方）—— 保留计算得到的判定: %s" % (legacy, decision["mode"]),
        file=sys.stderr,
    )

deps = analyze_deps(
    change_name=CHANGE_NAME,
    proposal_path=os.path.join(PROJECT_ROOT, "openspec", "changes", CHANGE_NAME, "proposal.md"),
    manual_deps=manual_deps,
    cross_repo=False,
)

gate = analyze_deps_with_strict_gate(blockers=deps["blockers"])
if not gate["passes"]:
    print(f"STRICT_DEPS_GATE FAIL: blockers={gate['failures']}")
    sys.exit(6)

# Merge, not overwrite: a full write resets approval_status to its "pending"
# default (dropping P0's "approved") and any field written by another phase.
update_builder_handoff(
    PROJECT_ROOT,
    CHANGE_NAME,
    current_phase="phase-1.5",
    execution_mode_decision={
        "mode": decision["mode"],
        "reason": decision["reason"],
        "decided_at": __import__("datetime").datetime.utcnow().isoformat(),
        "decided_by": "phase-1.5-deps-analyzer",
    },
    deps_status=deps,
)
print(f"Phase 1.5 done: mode={decision['mode']}, deps={len(manual_deps)} manual, {len(deps['blockers'])} blockers")
PYEOF