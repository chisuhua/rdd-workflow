#!/usr/bin/env bash
# skills/roadmap/scripts/objective_archive.sh — bash wrapper for objective archive command.
#
# Usage:
#   bash objective_archive.sh <id>
#
# Env vars consumed:
#   PROJECT_ROOT  Required. Repo root.
#   OBJECTIVE_ID  Required. Objective ID.
set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "usage: objective_archive.sh <id>" >&2
  exit 2
fi

export OBJECTIVE_ID="$1"
export PROJECT_ROOT="${PROJECT_ROOT:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"

python3 - <<'PYEOF'
import os, shutil, sys
from pathlib import Path

PROJECT_ROOT = Path(os.environ["PROJECT_ROOT"])
obj_id = os.environ["OBJECTIVE_ID"]

if not obj_id.startswith("objective-"):
    obj_id = f"objective-{obj_id}"

src = PROJECT_ROOT / ".rddf" / "roadmap" / "objectives" / f"{obj_id}.md"
dst = PROJECT_ROOT / ".rddf" / "roadmap" / "objectives" / "archive" / f"{obj_id}.md"

if not src.exists():
    print(f"❌ objective not found: {src}", file=sys.stderr)
    sys.exit(1)

dst.parent.mkdir(parents=True, exist_ok=True)
shutil.move(str(src), str(dst))
print(f"✅ archived: {src.name} → objectives/archive/{dst.name}")
PYEOF
