#!/usr/bin/env bash
# skills/roadmap/scripts/objective_deps.sh — bash wrapper for objective deps command.
#
# Phase 1 stub: prints the manual_deps from frontmatter. Phase 2 will call
# `rddf deps` for change-level DAG and grep for objective_ref in feature
# fragments.
#
# Usage:
#   bash objective_deps.sh <id>
#
# Env vars consumed:
#   PROJECT_ROOT  Required. Repo root.
#   OBJECTIVE_ID  Required. Objective ID.
set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "usage: objective_deps.sh <id>" >&2
  exit 2
fi

export OBJECTIVE_ID="$1"
export PROJECT_ROOT="${PROJECT_ROOT:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"

python3 - <<'PYEOF'
import os, sys
from pathlib import Path

PROJECT_ROOT = Path(os.environ["PROJECT_ROOT"])
obj_id = os.environ["OBJECTIVE_ID"]

if not obj_id.startswith("objective-"):
    obj_id = f"objective-{obj_id}"

sys.path.insert(0, str(PROJECT_ROOT))
from _lib.objective import parse_objective, derive_associations  # noqa: E402

target = PROJECT_ROOT / ".rddf" / "roadmap" / "objectives" / f"{obj_id}.md"
if not target.exists():
    print(f"❌ objective not found: {target}", file=sys.stderr)
    sys.exit(1)

data = parse_objective(target)
assoc = derive_associations(data)

print(f"# Dependencies for {obj_id}")
print()
print("## §7 features (Phase 2: derived)")
print(f"  (count: {len(assoc['features'])}) — Phase 1 stub returns empty list")
print()
print("## §8 changes (Phase 2: derived)")
print(f"  (count: {len(assoc['changes'])}) — Phase 1 stub returns empty list")
print()
print("## §9 manual_deps (from frontmatter)")
if assoc["objectives"]:
    for d in assoc["objectives"]:
        print(f"  - {d}")
else:
    print("  (none)")
print()
print("> Phase 2 enhancement: scan .rddf/roadmap/features/*.md and openspec/changes/*/roadmap-meta.yaml for objective_ref")
PYEOF
