# fix-skill-tool-cache Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use skill_use("execute") to implement this plan task-by-task.

**Goal:** 检测 skill 加载内容是否过期，提示用户刷新

**Architecture:** 在 scan-state.sh 中增加文件 mtime 或 git log 对比检测

**Tech Stack:** Bash, Git

---

## File Structure

### Production Code

| File | Responsibility |
|---|---|
| `skills/guide/scripts/scan-state.sh` | 增加 skill 版本检测 |

### Tests

| File | Responsibility |
|---|---|
| `tests/integration/test_skill_version_check.bats` | 测试版本不一致检测 |

---

### Task 1: 实现 skill 版本检测

**Files:**
- Modify: `skills/guide/scripts/scan-state.sh`
- Test: `tests/integration/test_skill_version_check.bats`

- [ ] **Step 1: Write the failing test**

```bash
@test "scan-state: detects stale skill version" {
  # Setup: modify skill file but not git commit
  run scan_state
  [[ "$output" =~ "skill 版本滞后" ]]
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `bats tests/integration/test_skill_version_check.bats`
Expected: FAIL

- [ ] **Step 3: Write minimal implementation**

```bash
check_skill_version() {
  local skill_file="$1"
  local skill_name=$(basename "$skill_file" .md)
  local file_mtime=$(stat -c %Y "$skill_file" 2>/dev/null || echo 0)
  local git_mtime=$(git log -1 --format=%ct "$skill_file" 2>/dev/null || echo 0)
  
  if [ "$file_mtime" -gt "$git_mtime" ]; then
    echo "⚠️  $skill_name 版本滞后 (文件比 git 新)"
    return 1
  fi
  return 0
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `bats tests/integration/test_skill_version_check.bats`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add skills/guide/scripts/scan-state.sh tests/integration/test_skill_version_check.bats
git commit -m "feat: add skill version check in scan-state"
```
