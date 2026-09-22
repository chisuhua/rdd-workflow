#!/usr/bin/env bash
# rdd-planner stage entry: emit .planner-handoff.json
set -euo pipefail

CHANGE_NAME="${1:-}"
PROJECT_ROOT="${PROJECT_ROOT:-$(pwd)}"

if [ -z "$CHANGE_NAME" ]; then
    echo "planner_stage_entry.sh requires <change-name>" >&2
    exit 2
fi

if [ ! -d "openspec/changes/$CHANGE_NAME" ]; then
    echo "openspec/changes/$CHANGE_NAME not found" >&2
    exit 2
fi

PROPOSALS=$(python3 -c "
import json
from pathlib import Path
state = Path('.rddf/state/.planner-state.json')
if state.exists():
    d = json.loads(state.read_text())
    print('\n'.join(d.get('active_projects', [])))
" 2>/dev/null || true)
FEATURES=$(rddf roadmap list-features 2>/dev/null | grep -oE 'feat-[a-zA-Z0-9-]+' | head -10 || true)
CURRENT_SPRINT="sprint-$(date -u +%Y-%m)"
APPROVED=$(rddf status --json 2>/dev/null | python3 -c "import sys, json; d=json.load(sys.stdin); print(sum(1 for c in d.get('changes', []) if c.get('status')=='approved'))" 2>/dev/null || echo "0")

# v1.2 (per add-objective-aware-planner): read .rddf/roadmap/objectives/*.md
# and serialize each active/deferred objective (id/priority/status/review_by/
# theme/next_sprint_candidates) for LLM consumption at stage entry.
# completed/archived objectives are excluded (not actionable).
ACTIVE_OBJECTIVES_JSON=$(PROJECT_ROOT="$PROJECT_ROOT" python3 - <<'PYEOF' 2>/dev/null || echo "[]"
import json, os, sys
from pathlib import Path

PROJECT_ROOT = Path(os.environ.get("PROJECT_ROOT", "."))
sys.path.insert(0, str(PROJECT_ROOT))
try:
    from _lib.objective import parse_objective
except ImportError:
    print("[]")
    sys.exit(0)

obj_dir = PROJECT_ROOT / ".rddf" / "roadmap" / "objectives"
if not obj_dir.is_dir():
    print("[]")
    sys.exit(0)

records = []
for f in sorted(obj_dir.glob("*.md")):
    if f.parent.name == "archive":
        continue
    try:
        data = parse_objective(f)
    except (ValueError, OSError):
        continue
    fm = data.get("frontmatter", {})
    if fm.get("status") not in ("active", "deferred"):
        continue
    # Parse §10 next_sprint_candidates as bullet list (- [ ] foo / - foo)
    candidates = []
    sec10 = data.get("sections", {}).get("## 10.", "")
    for line in sec10.splitlines():
        s = line.strip()
        if s.startswith("- [ ]"):
            candidates.append(s[5:].strip())
        elif s.startswith("- "):
            candidates.append(s[2:].strip())
    # Filter N/A — <reason> markers (deferred objectives per D9)
    candidates = [c for c in candidates if c and not c.startswith("N/A")]
    records.append({
        "id": fm.get("id", f.stem),
        "priority": fm.get("priority", "?"),
        "status": fm.get("status", "?"),
        "review_by": fm.get("review_by", ""),
        "theme": fm.get("theme", "")[:200],
        "next_sprint_candidates": candidates,
    })

print(json.dumps(records, ensure_ascii=False))
PYEOF
)

export PROJECT_ROOT PROPOSALS_READY="$PROPOSALS" PROPOSALS_APPROVED_COUNT="$APPROVED" FEATURES_ACTIVE="$FEATURES" CURRENT_SPRINT ACTIVE_OBJECTIVES_JSON

python3 -m _lib.planner_handoff
echo "planner stage entry complete: change=$CHANGE_NAME"