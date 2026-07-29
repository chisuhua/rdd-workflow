# archive-gate-incomplete-tasks Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use skill_use("execute") to implement this plan task-by-task.

**Goal:** 归档前增加门控检查，防止 0 个完成任务的 change 被归档

**Architecture:** 在 archive_change 前检查 tasks.md 中 [x] 数量，0 个时阻止归档并要求二次确认

**Tech Stack:** Bash, OpenSpec CLI

---

## File Structure

### Production Code

| File | Responsibility |
|---|---|
| `skills/_lib/archive.sh` | 增加 archive-gate 检查函数 |
| `skills/guide-ship/SKILL.md` | 文档记录门控机制 |

### Tests

| File | Responsibility |
|---|---|
| `tests/integration/test_archive_gate.bats` | 测试门控阻止/通过场景 |

---

### Task 1: 实现 archive-gate 检查

**Files:**
- Modify: `skills/_lib/archive.sh`
- Test: `tests/integration/test_archive_gate.bats`

- [ ] **Step 1: Write the failing test**

```bash
@test "archive-gate: blocks change with 0 completed tasks" {
  run archive_change "test-zero-tasks"
  [ "$status" -eq 1 ]
  [[ "$output" =~ "未实现" ]]
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `bats tests/integration/test_archive_gate.bats`
Expected: FAIL

- [ ] **Step 3: Write minimal implementation**

```bash
archive_gate_check() {
  local change_name="$1"
  local tasks_file="openspec/changes/$change_name/tasks.md"
  local completed=$(grep -c '^- \[x\]' "$tasks_file" 2>/dev/null || echo 0)
  
  if [ "$completed" -eq 0 ] && [ "${FORCE_ARCHIVE_INCOMPLETE:-no}" != "yes" ]; then
    echo "❌ 未实现 (0 个完成任务)。设置 FORCE_ARCHIVE_INCOMPLETE=yes 跳过"
    return 1
  fi
  return 0
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `bats tests/integration/test_archive_gate.bats`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add skills/_lib/archive.sh tests/integration/test_archive_gate.bats
git commit -m "feat: add archive-gate for incomplete tasks"
```
