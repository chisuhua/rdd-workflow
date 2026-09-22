#!/usr/bin/env bash
# skills/roadmap/scripts/objective_list.sh — bash wrapper for objective list command.
#
# Per Oracle C1 (env-var passing pattern), this script does NOT use bash string
# interpolation into Python; all values flow through PROJECT_ROOT / STATUS_FILTER /
# FORMAT env vars.
#
# Usage:
#   bash objective_list.sh [--status <filter>] [--format table|json]
#
# Env vars consumed:
#   PROJECT_ROOT       Required. Repo root.
#   OBJECTIVE_STATUS   Optional. Status filter (active|deferred|completed|archived).
#   OBJECTIVE_FORMAT   Optional. Output format: table (default) | json.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Parse args into env vars (no shell-injection risk)
while [[ $# -gt 0 ]]; do
  case "$1" in
    --status)
      export OBJECTIVE_STATUS="${2:-}"
      shift 2
      ;;
    --format)
      export OBJECTIVE_FORMAT="${2:-table}"
      shift 2
      ;;
    -h|--help)
      sed -n '2,12p' "$0"
      exit 0
      ;;
    *)
      echo "❌ unknown arg: $1" >&2
      exit 2
      ;;
  esac
done

# Default PROJECT_ROOT
export PROJECT_ROOT="${PROJECT_ROOT:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"

python3 - <<'PYEOF'
import os, sys, json
from pathlib import Path

PROJECT_ROOT = Path(os.environ["PROJECT_ROOT"])
STATUS_FILTER = os.environ.get("OBJECTIVE_STATUS", "")
OUTPUT_FORMAT = os.environ.get("OBJECTIVE_FORMAT", "table")

sys.path.insert(0, str(PROJECT_ROOT))
from _lib.objective import parse_objective, STATUS_ENUM  # noqa: E402

obj_dir = PROJECT_ROOT / ".rddf" / "roadmap" / "objectives"
if not obj_dir.is_dir():
    if OUTPUT_FORMAT == "json":
        print(json.dumps({"objectives": []}))
    else:
        print("No objectives found.")
    sys.exit(0)

rows = []
errors = []
for f in sorted(obj_dir.glob("*.md")):
    if f.parent.name == "archive":
        continue
    try:
        data = parse_objective(f)
    except ValueError as e:
        errors.append(f"{f.name}: {e}")
        continue
    fm = data["frontmatter"]
    if STATUS_FILTER and fm.get("status") != STATUS_FILTER:
        continue
    rows.append({
        "id": f.stem,
        "priority": fm.get("priority", "?"),
        "status": fm.get("status", "?"),
        "review_by": fm.get("review_by", "?"),
        "theme": fm.get("theme", "")[:80],
    })

if OUTPUT_FORMAT == "json":
    print(json.dumps({"objectives": rows, "errors": errors}, ensure_ascii=False, indent=2))
else:
    if not rows:
        print("No objectives found.")
    else:
        # Table format
        print(f"{'ID':<55} {'Priority':<5} {'Status':<12} {'Review By':<12} Theme")
        print("-" * 110)
        for r in rows:
            print(f"{r['id']:<55} {r['priority']:<5} {r['status']:<12} {r['review_by']:<12} {r['theme']}")
    if errors:
        print("\n⚠️  parse errors:", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
PYEOF
