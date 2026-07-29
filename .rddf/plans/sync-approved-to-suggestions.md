# sync-approved-to-suggestions Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use skill_use("execute") to implement this plan task-by-task.

**Goal:** 双索引自动同步，approved.md 更新时同步更新 suggestions.md

**Architecture:** 在 append_approved 和 mark_approved_completed 中增加同步逻辑

**Tech Stack:** Bash, Python, Markdown

---

## File Structure

### Production Code

| File | Responsibility |
|---|---|
| `skills/_lib/state.sh` | 增加 sync_suggestions 函数 |

### Tests

| File | Responsibility |
|---|---|
| `tests/integration/test_sync_suggestions.bats` | 测试双索引同步 |

---

### Task 1: 实现双索引同步

**Files:**
- Modify: `skills/_lib/state.sh`
- Test: `tests/integration/test_sync_suggestions.bats`

- [ ] **Step 1: Write the failing test**

```bash
@test "sync: append_approved updates suggestions.md" {
  run append_approved "/project" "test-change" "P1"
  grep -q "test-change" proposal-suggestions.md
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `bats tests/integration/test_sync_suggestions.bats`
Expected: FAIL

- [ ] **Step 3: Write minimal implementation**

```bash
sync_suggestions() {
  local project_root="$1"
  local name="$2"
  local status="$3"  # approved/completed
  
  local suggestions_file="$project_root/proposal-suggestions.md"
  [ ! -f "$suggestions_file" ] && return 0
  
  python3 -c "
import re, sys
name = '$name'
status = '$status'
with open('$suggestions_file') as f:
    content = f.read()
# Update status in suggestions table
pattern = r'(\| \[' + re.escape(name) + r'\]\([^)]+\) \| [^|]+ \| [^|]+ \|) [^|]+ (\|)'
replacement = r'\1 ' + status + r' \2'
content = re.sub(pattern, replacement, content)
with open('$suggestions_file', 'w') as f:
    f.write(content)
"
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `bats tests/integration/test_sync_suggestions.bats`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add skills/_lib/state.sh tests/integration/test_sync_suggestions.bats
git commit -m "feat: sync approved.md and suggestions.md"
```
