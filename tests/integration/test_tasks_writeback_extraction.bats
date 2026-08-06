#!/usr/bin/env bats
# tests/integration/test_tasks_writeback_extraction.bats
# Task B7 regression: execute.md L366-L399 was a ~34-line inline bash block for
# tasks.md writeback (Method A: awk index() precise match, Method B: awk gsub() bulk mark).
# Extracted to _lib/tasks_writeback.sh exposing:
#   - mark_task_done <task_desc>     — precise single-task mark
#   - mark_all_tasks_done            — bulk mark all - [ ] → - [x]
#
# 6 tests lock the refactor in place:
#   1. Helper file exists with exported functions.
#   2. execute.md L366-L399 inline block is removed.
#   3. execute.md sources and invokes the helper.
#   4. mark_task_done marks specific task (functional).
#   5. mark_task_done handles missing task (functional).
#   6. mark_all_tasks_done marks everything (functional).

load ../test_helper

EXECUTE_MD="$REPO_ROOT/skills/execute/SKILL.md"
TASKS_WB="$REPO_ROOT/skills/execute/scripts/tasks_writeback.sh"

@test "tasks_writeback_helper_exists" {
  [ -f "$TASKS_WB" ]
  bash -c "cd '$REPO_ROOT' && source '$TASKS_WB' && declare -f mark_task_done && declare -f mark_all_tasks_done" | grep -q 'mark_task_done'
}

@test "execute_inline_block_removed" {
  # No old inline bash: TMPFILE variable assignment (now encapsulated in helper)
  ! grep -q 'TMPFILE=.*mktemp.*tasks_' "$EXECUTE_MD"
  # No old inline awk pipeline pattern (the raw awk to TMPFILE redirect)
  ! grep -q '\$PROJECT_ROOT/openspec/changes.*tasks\.md.*TMPFILE' "$EXECUTE_MD"
}

@test "execute_invokes_helper" {
  grep -q 'source.*scripts/tasks_writeback.sh' "$EXECUTE_MD"
  grep -qE 'mark_task_done|mark_all_tasks_done' "$EXECUTE_MD"
}

@test "mark_task_done_marks_specific_task" {
  local tmpdir
  tmpdir=$(mktemp -d)
  mkdir -p "$tmpdir/openspec/changes/test-change"
  cat > "$tmpdir/openspec/changes/test-change/tasks.md" <<'EOF'
# Tasks
- [ ] Implement UART config
- [ ] Add tests
- [ ] Update docs
EOF
  output=$(PROJECT_ROOT="$tmpdir" CHANGE_NAME="test-change" bash -c "source '$TASKS_WB' && mark_task_done 'Implement UART config'" 2>&1 || true)
  echo "$output" | grep -q 'tasks.md 已更新'
  grep -q '\[x\] Implement UART config' "$tmpdir/openspec/changes/test-change/tasks.md"
  rm -rf "$tmpdir"
}

@test "mark_task_done_handles_missing_task" {
  local tmpdir
  tmpdir=$(mktemp -d)
  mkdir -p "$tmpdir/openspec/changes/test-change"
  echo "- [ ] Other task" > "$tmpdir/openspec/changes/test-change/tasks.md"
  output=$(PROJECT_ROOT="$tmpdir" CHANGE_NAME="test-change" bash -c "source '$TASKS_WB' && mark_task_done 'Nonexistent task'" 2>&1 || true)
  rm -rf "$tmpdir"
  echo "$output" | grep -qE '未找到|未匹配|warning'
}

@test "mark_all_tasks_done_marks_everything" {
  local tmpdir
  tmpdir=$(mktemp -d)
  mkdir -p "$tmpdir/openspec/changes/test-change"
  cat > "$tmpdir/openspec/changes/test-change/tasks.md" <<'EOF'
- [ ] Task 1
- [ ] Task 2
- [ ] Task 3
EOF
  output=$(PROJECT_ROOT="$tmpdir" CHANGE_NAME="test-change" bash -c "source '$TASKS_WB' && mark_all_tasks_done" 2>&1 || true)
  count=$(grep -c '^\- \[x\]' "$tmpdir/openspec/changes/test-change/tasks.md")
  [ "$count" = "3" ]
  rm -rf "$tmpdir"
}
