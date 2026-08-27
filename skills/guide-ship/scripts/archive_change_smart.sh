#!/usr/bin/env bash
# One-click archive funnel for OpenSpec changes.
# Usage: archive_change_smart.sh [--dry-run] [--strict] <change_name>

set -o pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
DRY_RUN=no
STRICT=no
CHANGE_NAME=""

error() {
  printf '❌ archive_change_smart: %s\n' "$*" >&2
  return 1
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --dry-run) DRY_RUN=yes ;;
    --strict) STRICT=yes ;;
    --help|-h)
      printf 'Usage: %s [--dry-run] [--strict] <change_name>\n' "$(basename "$0")"
      exit 0
      ;;
    --*) error "unknown option: $1"; exit 1 ;;
    *)
      if [ -n "$CHANGE_NAME" ]; then
        error "exactly one change_name is required"
        exit 1
      fi
      CHANGE_NAME="$1"
      ;;
  esac
  shift
done

[ -n "$CHANGE_NAME" ] || { error "change_name is required"; exit 1; }
CHANGE_DIR="$PROJECT_ROOT/openspec/changes/$CHANGE_NAME"
[ -d "$CHANGE_DIR" ] || {
  error "change directory does not exist: $CHANGE_DIR"
  exit 1
}

# shellcheck source=/dev/null
PROJECT_ROOT="$PROJECT_ROOT" source "$SCRIPT_DIR/ship_archive.sh"
MODE="$(detect_archive_mode "$PROJECT_ROOT" "$CHANGE_NAME")"
printf '📦 archive_change_smart: %s mode=%s\n' "$CHANGE_NAME" "$MODE"

if [ "$DRY_RUN" = yes ]; then
  printf '🔎 dry-run: would call archive_change_for_mode "%s" "%s" "%s"\n' \
    "$PROJECT_ROOT" "$CHANGE_NAME" "$MODE"
  exit 0
fi

if [ "$STRICT" = yes ]; then
  printf '🔒 strict mode: failing fast on any step failure\n'
fi

if ! archive_change_for_mode "$PROJECT_ROOT" "$CHANGE_NAME" "$MODE"; then
  error "archive_change_for_mode failed for $CHANGE_NAME"
  exit 1
fi

ITERATION_PATH="$PROJECT_ROOT/.rddf/state/iteration.json"
if ! PROJECT_ROOT="$PROJECT_ROOT" CHANGE_NAME="$CHANGE_NAME" ITERATION_PATH="$ITERATION_PATH" \
  python3 - <<'PYEOF'
import json
import os
import re
import sys
from pathlib import Path

root = Path(os.environ["PROJECT_ROOT"])
name = os.environ["CHANGE_NAME"]
iteration_path = Path(os.environ["ITERATION_PATH"])
if not iteration_path.is_file():
    print(f"iteration.json not found: {iteration_path}", file=sys.stderr)
    sys.exit(1)
try:
    data = json.loads(iteration_path.read_text(encoding="utf-8"))
except (OSError, json.JSONDecodeError) as exc:
    print(f"cannot read iteration.json: {exc}", file=sys.stderr)
    sys.exit(1)
entry = next((item for item in data.get("changes", []) if item.get("name") == name), None)
if entry is None:
    print(f"iteration entry not found for {name}", file=sys.stderr)
    sys.exit(1)
if entry.get("status") != "archived":
    print(f"iteration status is {entry.get('status')!r}, expected 'archived'", file=sys.stderr)
    sys.exit(1)
tasks_total = entry.get("tasks_total")
tasks_done = entry.get("tasks_done")
if tasks_total is None or tasks_done != tasks_total:
    print(f"iteration tasks incomplete: tasks_done={tasks_done}, tasks_total={tasks_total}", file=sys.stderr)
    sys.exit(1)
print(f"✅ iteration verified: status=archived tasks_done={tasks_done}/{tasks_total}")
PYEOF
then
  error "iteration.json verification failed"
  exit 1
fi

if [ -n "$(git -C "$PROJECT_ROOT" status --porcelain 2>/dev/null)" ]; then
  error "working tree is not clean after archive; archive moves may not be committed"
  exit 1
fi
printf '✅ archive moves committed; working tree clean\n'
exit 0
