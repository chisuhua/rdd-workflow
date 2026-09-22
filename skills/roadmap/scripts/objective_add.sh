#!/usr/bin/env bash
# skills/roadmap/scripts/objective_add.sh — bash wrapper for objective add command.
#
# Usage:
#   bash objective_add.sh <id> --theme "<text>" [--priority P0|P1|P2] [--status active|deferred] [--force]
#
# Env vars consumed:
#   PROJECT_ROOT        Required. Repo root.
#   OBJECTIVE_ID        Required. Objective ID.
#   OBJECTIVE_THEME     Required. One-sentence theme.
#   OBJECTIVE_PRIORITY  Optional. P0|P1|P2. Default: P1.
#   OBJECTIVE_STATUS    Optional. active|deferred. Default: active.
#   OBJECTIVE_FORCE     Optional. "1" to overwrite existing file.
set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "usage: objective_add.sh <id> --theme \"<text>\" [--priority P0|P1|P2] [--status active|deferred] [--force]" >&2
  exit 2
fi

export OBJECTIVE_ID="$1"; shift

while [[ $# -gt 0 ]]; do
  case "$1" in
    --theme)
      export OBJECTIVE_THEME="${2:-}"
      shift 2
      ;;
    --priority)
      export OBJECTIVE_PRIORITY="${2:-P1}"
      shift 2
      ;;
    --status)
      export OBJECTIVE_STATUS="${2:-active}"
      shift 2
      ;;
    --force)
      export OBJECTIVE_FORCE=1
      shift
      ;;
    *)
      echo "❌ unknown arg: $1" >&2
      exit 2
      ;;
  esac
done

if [[ -z "${OBJECTIVE_THEME:-}" ]]; then
  echo "❌ --theme is required" >&2
  exit 2
fi

export PROJECT_ROOT="${PROJECT_ROOT:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"

python3 - <<'PYEOF'
import os, sys
from datetime import date, timedelta
from pathlib import Path

PROJECT_ROOT = Path(os.environ["PROJECT_ROOT"])
obj_id = os.environ["OBJECTIVE_ID"]
theme = os.environ["OBJECTIVE_THEME"]
priority = os.environ.get("OBJECTIVE_PRIORITY", "P1")
status = os.environ.get("OBJECTIVE_STATUS", "active")
force = os.environ.get("OBJECTIVE_FORCE", "") == "1"

# Normalize id
if not obj_id.startswith("objective-"):
    obj_id = f"objective-{obj_id}"

sys.path.insert(0, str(PROJECT_ROOT))
from _lib.objective import ID_PATTERN  # noqa: E402

if not ID_PATTERN.match(obj_id):
    print(f"❌ invalid objective id pattern: {obj_id}", file=sys.stderr)
    sys.exit(1)

target = PROJECT_ROOT / ".rddf" / "roadmap" / "objectives" / f"{obj_id}.md"
if target.exists() and not force:
    print(f"❌ objective exists: {target} (use --force to overwrite)", file=sys.stderr)
    sys.exit(1)

target.parent.mkdir(parents=True, exist_ok=True)
today = date.today().isoformat()
review_by = (date.today() + timedelta(days=90)).isoformat()

content = f"""---
id: {obj_id}
status: {status}
created: {today}
last_revised: {today}
review_by: {review_by}
owner: rdd-planner
priority: {priority}
manual_deps: []
supersedes: null
theme: {theme}
---

# Objective: {obj_id}

## 1. 驱动诊断（Why now）
TODO

## 2. 目标愿景 + 完成判据
TODO

## 3. 架构依据
无

## 9. 目标依赖与 Decision Gate
### 9.1 前置 objective 依赖
无

### 9.2 Go / No-Go Decision Gate
TODO

## 10. next_sprint_candidates
- TODO

## 11. 跟踪台账（append-only）
| Sprint | kind | 内容 | Decision/调整 | 原因 |
|--------|------|------|---------------|------|
| sprint-{today[:7]} | sprint-review | objective 创建 | — | initial |
"""

target.write_text(content, encoding="utf-8")
print(f"✅ created: {target}")
PYEOF
