# guide-plan-fallback-direct-create Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use skill_use("execute") to implement this plan task-by-task.

**Goal:** proposal-approved.md 不存在时提供直接创建 change 的后备路径

**Architecture:** 在 plan_intake.sh 中检测 proposal-approved.md 缺失，提供后备选项

**Tech Stack:** Bash

---

## File Structure

### Production Code

| File | Responsibility |
|---|---|
| `skills/guide-plan/scripts/plan_intake.sh` | 增加后备检测 |
| `skills/guide-plan/SKILL.md` | 文档更新 |

### Tests

| File | Responsibility |
|---|---|
| `tests/integration/test_plan_fallback.bats` | 测试后备路径 |

---

### Task 1: 实现直接创建后备路径

**Files:**
- Modify: `skills/guide-plan/scripts/plan_intake.sh`
- Test: `tests/integration/test_plan_fallback.bats`

- [ ] **Step 1: Write the failing test**

```bash
@test "plan_intake: offers direct-create when no proposal-approved.md" {
  rm -f proposal-approved.md
  run run_plan_intake
  [[ "$output" =~ "直接创建" ]]
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `bats tests/integration/test_plan_fallback.bats`
Expected: FAIL

- [ ] **Step 3: Write minimal implementation**

```bash
check_direct_create_fallback() {
  local project_root="$1"
  local approved_file="$project_root/proposal-approved.md"
  
  if [ ! -f "$approved_file" ]; then
    local archived_count=$(ls -d "$project_root"/openspec/changes/archive/*/ 2>/dev/null | wc -l)
    if [ "$archived_count" -gt 0 ]; then
      echo "🆕 未发现 proposal-approved.md — 检测到 $archived_count 个历史归档"
      echo "   后备模式: 跳过提案审批，直接创建新 change"
      echo "   后续可手动追加 proposal-approved.md 作为审计追溯"
      return 0
    fi
  fi
  return 1
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `bats tests/integration/test_plan_fallback.bats`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add skills/guide-plan/scripts/plan_intake.sh tests/integration/test_plan_fallback.bats
git commit -m "feat: add direct-create fallback for mature projects"
```
