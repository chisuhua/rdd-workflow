#!/usr/bin/env bash
# Phase 1.5: Deps + execution_mode decision.
# Exit 6 if STRICT_DEPS_GATE FAIL.
set -euo pipefail

CHANGE_NAME="${1:-}"
PROJECT_ROOT="${PROJECT_ROOT:-$(pwd)}"

if [ -z "$CHANGE_NAME" ]; then
    echo "phase1_5_deps.sh requires <change-name>" >&2
    exit 2
fi

echo "=== Phase 1.5: Deps + Execution Mode Decision for $CHANGE_NAME ==="

# Legacy plan-handoff fallback (per spec §3.4 + Oracle C2)
LEGACY_EXEC_MODE=""
if [ -f ".rddf/state/.plan-handoff.json" ]; then
    LEGACY_EXEC_MODE=$(python3 -c "
import json
data = json.load(open('.rddf/state/.plan-handoff.json'))
print(data.get('execution_mode_decisions', {}).get('$CHANGE_NAME', {}).get('mode', ''))
" 2>/dev/null || echo "")
fi

python3 <<PYEOF
import sys
sys.path.insert(0 "$PROJECT_ROOT")
from _lib.builder_deps import decide_execution_mode, analyze_deps, analyze_deps_with_strict_gate
from _lib.builder_handoff import write_builder_handoff

manual_deps = []
meta_path = "openspec/changes/$CHANGE_NAME/roadmap-meta.yaml"
import os
if os.path.exists(meta_path):
    try:
        import yaml
        with open(meta_path) as f:
            meta = yaml.safe_load(f) or {}
        manual_deps = meta.get("manual_deps", []) or []
    except Exception:
        pass

import glob
files_changed = sum(1 for _ in glob.glob("openspec/changes/$CHANGE_NAME/**", recursive=True))
task_count = 5

decision = decide_execution_mode(
    file_count=files_changed,
    task_count=task_count,
    risk_keywords=[],
)

# Override with legacy plan-handoff execution_mode if available
legacy = "$LEGACY_EXEC_MODE"
if legacy in ("worktree", "lightweight"):
    decision["mode"] = legacy
    decision["reason"] = "from legacy .plan-handoff.json fallback (Wave 1 compat)"

deps = analyze_deps(
    change_name="$CHANGE_NAME",
    proposal_path="openspec/changes/$CHANGE_NAME/proposal.md",
    manual_deps=manual_deps,
    cross_repo=False,
)

gate = analyze_deps_with_strict_gate(blockers=deps["blockers"])
if not gate["passes"]:
    print(f"STRICT_DEPS_GATE FAIL: blockers={gate['failures']}")
    sys.exit(6)

write_builder_handoff(
    project_root="$PROJECT_ROOT",
    change_name="$CHANGE_NAME",
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