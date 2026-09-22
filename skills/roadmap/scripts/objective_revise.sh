#!/usr/bin/env bash
# skills/roadmap/scripts/objective_revise.sh — bash wrapper for objective revise command.
#
# Phase 1: stub. The full implementation requires interactive prompts (kind /
# content / decision / reason) that need a TTY-aware python REPL. For now this
# script appends a manual row passed via env vars.
#
# Usage:
#   bash objective_revise.sh <id> [--kind sprint-review] [--content "..."] [--decision "..."] [--reason "..."]
#
# Env vars consumed:
#   PROJECT_ROOT          Required. Repo root.
#   OBJECTIVE_ID          Required. Objective ID.
#   LEDGER_KIND           Optional. One of 5 kinds. Default: sprint-review.
#   LEDGER_CONTENT        Optional. Content column.
#   LEDGER_DECISION       Optional. Decision column.
#   LEDGER_REASON         Optional. Reason column.
set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "usage: objective_revise.sh <id> [--kind <kind>] [--content \"...\"] [--decision \"...\"] [--reason \"...\"]" >&2
  exit 2
fi

export OBJECTIVE_ID="$1"; shift

while [[ $# -gt 0 ]]; do
  case "$1" in
    --kind)     export LEDGER_KIND="${2:-sprint-review}"; shift 2 ;;
    --content)  export LEDGER_CONTENT="${2:-}"; shift 2 ;;
    --decision) export LEDGER_DECISION="${2:-}"; shift 2 ;;
    --reason)   export LEDGER_REASON="${2:-}"; shift 2 ;;
    *) echo "❌ unknown arg: $1" >&2; exit 2 ;;
  esac
done

export PROJECT_ROOT="${PROJECT_ROOT:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
export LEDGER_KIND="${LEDGER_KIND:-sprint-review}"

python3 - <<'PYEOF'
import os, sys, re
from datetime import date
from pathlib import Path

PROJECT_ROOT = Path(os.environ["PROJECT_ROOT"])
obj_id = os.environ["OBJECTIVE_ID"]
kind = os.environ["LEDGER_KIND"]
content = os.environ.get("LEDGER_CONTENT", "")
decision = os.environ.get("LEDGER_DECISION", "")
reason = os.environ.get("LEDGER_REASON", "")

if not obj_id.startswith("objective-"):
    obj_id = f"objective-{obj_id}"

sys.path.insert(0, str(PROJECT_ROOT))
from _lib.objective import KIND_ENUM, parse_objective, validate_objective  # noqa: E402

if kind not in KIND_ENUM:
    print(f"❌ invalid kind: {kind} (must be one of {sorted(KIND_ENUM)})", file=sys.stderr)
    sys.exit(1)

target = PROJECT_ROOT / ".rddf" / "roadmap" / "objectives" / f"{obj_id}.md"
if not target.exists():
    print(f"❌ objective not found: {target}", file=sys.stderr)
    sys.exit(1)

data = parse_objective(target)
errors = validate_objective(data)
if errors:
    print(f"❌ objective invalid: {errors[:3]}", file=sys.stderr)
    sys.exit(1)

# Append row to §11
text = target.read_text(encoding="utf-8")
today = date.today().isoformat()
sprint_id = f"sprint-{today[:7]}"
new_row = f"| {sprint_id} | {kind} | {content} | {decision} | {reason} |"

# Find §11 section and append row before any trailing whitespace
pattern = re.compile(r"(## 11\. 跟踪台账[^\n]*\n(?:\|[^\n]*\n)+)", re.MULTILINE)
m = pattern.search(text)
if not m:
    print("❌ §11 ledger header not found", file=sys.stderr)
    sys.exit(1)

# Update last_revised in frontmatter
text = re.sub(r"^last_revised: \d{4}-\d{2}-\d{2}$", f"last_revised: {today}", text, flags=re.MULTILINE)

# Insert new row right after the header rows
header_end = m.end()
text = text[:header_end] + new_row + "\n" + text[header_end:]

target.write_text(text, encoding="utf-8")
print(f"✅ appended ledger row to {target}")
print(f"   kind={kind} content={content!r} decision={decision!r} reason={reason!r}")
PYEOF
