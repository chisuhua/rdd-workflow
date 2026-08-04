#!/usr/bin/env bash
# skills/_lib/tasks_writeback.sh — extracted from execute.md L366-L399
# Exports:
#   - mark_task_done <task_desc> — precise mark via awk index()
#   - mark_all_tasks_done        — bulk mark via awk gsub()
#
# Both methods use mktemp + mv for atomic write.
# Honors env vars:
#   CHANGE_NAME  — the OpenSpec change name (required)
#   PROJECT_ROOT — git project root (default: auto-detect)

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" 2>/dev/null && pwd)"

if [ -f "$SCRIPT_DIR/change_name.sh" ]; then
  source "$SCRIPT_DIR/change_name.sh"
fi

mark_task_done() {
  local TASK_DESC="${1:-}"
  local PROJECT_ROOT="${PROJECT_ROOT:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"

  if [ -z "$TASK_DESC" ]; then
    echo "❌ 需要 TASK_DESC"
    return 1
  fi

  if ! ensure_change_name; then
    return 1
  fi

  local TASKS_FILE="$PROJECT_ROOT/openspec/changes/$CHANGE_NAME/tasks.md"
  if [ ! -f "$TASKS_FILE" ]; then
    echo "❌ tasks.md 不存在: $TASKS_FILE"
    return 1
  fi

  local TMPFILE
  TMPFILE=$(mktemp -t tasks_XXXXXX.md)
  awk -v desc="- [ ] $TASK_DESC" -v repl="- [x] $TASK_DESC" '
    {
      pos = index($0, desc)
      if (pos > 0) {
        $0 = substr($0, 1, pos-1) repl substr($0, pos + length(desc))
        changed = 1
      }
    }
    { print }
    END { exit (changed ? 0 : 1) }
  ' "$TASKS_FILE" > "$TMPFILE"

  if [ $? -eq 0 ]; then
    mv "$TMPFILE" "$TASKS_FILE"
    echo "✅ tasks.md 已更新"
  else
    echo "⚠️  未找到匹配的任务描述: $TASK_DESC"
    rm -f "$TMPFILE"
    return 1
  fi
}

mark_all_tasks_done() {
  local PROJECT_ROOT="${PROJECT_ROOT:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"

  if ! ensure_change_name; then
    return 1
  fi

  local TASKS_FILE="$PROJECT_ROOT/openspec/changes/$CHANGE_NAME/tasks.md"
  if [ ! -f "$TASKS_FILE" ]; then
    echo "❌ tasks.md 不存在: $TASKS_FILE"
    return 1
  fi

  local TMPFILE
  TMPFILE=$(mktemp -t tasks_XXXXXX.md)
  awk '{gsub(/- \[ \] /,"- [x] ")}1' \
    "$TASKS_FILE" > "$TMPFILE" && \
    mv "$TMPFILE" "$TASKS_FILE"

  echo "✅ tasks.md 所有任务已标记为完成"
}