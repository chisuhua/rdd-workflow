#!/usr/bin/env bash
# rdd-planner stage entry: emit .planner-handoff.json
set -euo pipefail

CHANGE_NAME="${1:-}"
PROJECT_ROOT="${PROJECT_ROOT:-$(pwd)}"

if [ -z "$CHANGE_NAME" ]; then
    echo "planner_stage_entry.sh requires <change-name>" >&2
    exit 2
fi

if [ ! -d "$PROJECT_ROOT/openspec/changes/$CHANGE_NAME" ]; then
    echo "$PROJECT_ROOT/openspec/changes/$CHANGE_NAME not found" >&2
    exit 2
fi

PROPOSALS=$(PROJECT_ROOT="$PROJECT_ROOT" python3 -c "
import json
import os
from pathlib import Path
state = Path(os.environ['PROJECT_ROOT']) / '.rddf' / 'state' / '.planner-state.json'
if state.exists():
    d = json.loads(state.read_text())
    print('\n'.join(d.get('active_projects', [])))
" 2>/dev/null || true)
FEATURES=$(rddf roadmap list-features 2>/dev/null | grep -oE 'feat-[a-zA-Z0-9-]+' | head -10 || true)
CURRENT_SPRINT="sprint-$(date -u +%Y-%m)"
# Count approved items from the improvement truth source
# (improvement-approved.md) via the shared collector. The previous
# `rddf status --json` pipeline never worked: that flag does not exist,
# so the command always failed and `|| echo "0"` swallowed it =>
# APPROVED was permanently 0.
APPROVED=$(PROJECT_ROOT="$PROJECT_ROOT" python3 - <<'PYEOF' 2>/dev/null || echo "0"
import os, sys
root = os.environ.get("PROJECT_ROOT", ".")
sys.path.insert(0, root)
try:
    from skills._lib.dashboard import collect_pending
    snapshot = collect_pending(root)
    print(sum(1 for r in snapshot.approved_proposals if r.section == "approved"))
except Exception:
    print(0)
PYEOF
)

ACTIVE_OBJECTIVES_JSON=$(PROJECT_ROOT="$PROJECT_ROOT" python3 - <<'PYEOF' 2>/dev/null || echo "[]"
import os, sys
sys.path.insert(0, os.environ.get("PROJECT_ROOT", "."))
from _lib.objective_parser import collect_active_objectives
print(collect_active_objectives(os.environ.get("PROJECT_ROOT", ".")))
PYEOF
)

export PROJECT_ROOT PROPOSALS_READY="$PROPOSALS" PROPOSALS_APPROVED_COUNT="$APPROVED" FEATURES_ACTIVE="$FEATURES" CURRENT_SPRINT ACTIVE_OBJECTIVES_JSON

python3 -m _lib.planner_handoff
echo "planner stage entry complete: change=$CHANGE_NAME"