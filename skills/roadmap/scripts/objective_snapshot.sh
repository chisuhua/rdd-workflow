#!/usr/bin/env bash
# skills/roadmap/scripts/objective_snapshot.sh — bash wrapper for objective snapshot command.
#
# Writes a dated §9.5 DAG snapshot segment. Format is mandatory (per design D10):
# timestamp + regenerate command + fenced code block with deps output.
# Idempotent: replaces same-day snapshot.
#
# Usage:
#   bash objective_snapshot.sh <id>
#
# Env vars consumed:
#   PROJECT_ROOT  Required. Repo root.
#   OBJECTIVE_ID  Required. Objective ID.
set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "usage: objective_snapshot.sh <id>" >&2
  exit 2
fi

export OBJECTIVE_ID="$1"
export PROJECT_ROOT="${PROJECT_ROOT:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"

python3 - <<'PYEOF'
import os, re, subprocess, sys
from datetime import date
from pathlib import Path

PROJECT_ROOT = Path(os.environ["PROJECT_ROOT"])
obj_id = os.environ["OBJECTIVE_ID"]

if not obj_id.startswith("objective-"):
    obj_id = f"objective-{obj_id}"

target = PROJECT_ROOT / ".rddf" / "roadmap" / "objectives" / f"{obj_id}.md"
if not target.exists():
    print(f"❌ objective not found: {target}", file=sys.stderr)
    sys.exit(1)

# Phase 1: stub deps output (since rddf deps --change <objective> isn't implemented yet).
# Real implementation will call `rddf deps --change <obj_id>` and pipe into fenced block.
deps_output = f"(Phase 1 stub) — manually inspect {obj_id} §9.1 manual_deps and features linked via objective_ref."

today = date.today().isoformat()
snapshot_segment = f"\n### 9.5 DAG snapshot ({today})\n\n> Snapshot derived at {today}, regenerate: rddf deps {obj_id}\n\n```\n{deps_output}\n```\n"

text = target.read_text(encoding="utf-8")
# Remove any existing snapshot from same day (idempotent)
text = re.sub(rf"\n### 9\.5 DAG snapshot \({today}\).*?(?=^## |\Z)", "", text, flags=re.MULTILINE | re.DOTALL)
# Append new snapshot at end of file (before EOF)
if not text.endswith("\n"):
    text += "\n"
text += snapshot_segment

# Update last_revised in frontmatter
text = re.sub(r"^last_revised: \d{4}-\d{2}-\d{2}$", f"last_revised: {today}", text, flags=re.MULTILINE)

target.write_text(text, encoding="utf-8")
print(f"✅ snapshot written to §9.5 ({today})")
PYEOF
