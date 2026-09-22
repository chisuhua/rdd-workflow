#!/usr/bin/env bash
# skills/roadmap/scripts/objective_show.sh — bash wrapper for objective show command.
#
# Usage:
#   bash objective_show.sh <id>
#
# Env vars consumed:
#   PROJECT_ROOT  Required. Repo root.
#   OBJECTIVE_ID  Required. Objective ID (with or without 'objective-' prefix).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [[ $# -lt 1 ]]; then
  echo "usage: objective_show.sh <id>" >&2
  exit 2
fi

export OBJECTIVE_ID="$1"
export PROJECT_ROOT="${PROJECT_ROOT:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"

python3 - <<'PYEOF'
import os, sys
from pathlib import Path

PROJECT_ROOT = Path(os.environ["PROJECT_ROOT"])
obj_id = os.environ["OBJECTIVE_ID"]

sys.path.insert(0, str(PROJECT_ROOT))
from _lib.objective import parse_objective, derive_associations  # noqa: E402

# Strip prefix if present
if not obj_id.startswith("objective-"):
    obj_id = f"objective-{obj_id}"

target = PROJECT_ROOT / ".rddf" / "roadmap" / "objectives" / f"{obj_id}.md"
if not target.exists():
    print(f"❌ objective not found: {target}", file=sys.stderr)
    sys.exit(1)

data = parse_objective(target)
fm = data["frontmatter"]

# Header
print(f"# {obj_id}")
print()
print(f"**status**: {fm.get('status', '?')}  **priority**: {fm.get('priority', '?')}  **owner**: {fm.get('owner', '?')}")
print(f"**created**: {fm.get('created', '?')}  **last_revised**: {fm.get('last_revised', '?')}  **review_by**: {fm.get('review_by', '?')}")
print(f"**theme**: {fm.get('theme', '?')}")
deps = fm.get("manual_deps", [])
if deps:
    print(f"**manual_deps**: {', '.join(deps)}")
supersedes = fm.get("supersedes")
if supersedes:
    print(f"**supersedes**: {supersedes}")
print()

# Sections
for sec in ("## 1.", "## 2.", "## 3.", "## 5.", "## 9.", "## 10.", "## 11."):
    content = data["sections"].get(sec, "").strip()
    if content:
        print(sec, content)
        print()

# Derived view note
assoc = derive_associations(data)
print("---")
print("> §7 features / §8 changes / §9.5 deps: 由 `rddf roadmap deps-objective` 派生（CLI 实时渲染，不手写）")
print(f"> 当前 manual_deps (from frontmatter): {assoc['objectives']}")
PYEOF
