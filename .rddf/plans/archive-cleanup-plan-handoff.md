# archive-cleanup-plan-handoff Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use skill_use("execute") to implement this plan task-by-task.

**Goal:** 归档后清理 .plan-handoff.json，保持状态一致

**Architecture:** 在 archive_change 末尾增加 handoff 清理步骤

**Tech Stack:** Bash, Python, JSON

---

## File Structure

### Production Code

| File | Responsibility |
|---|---|
| `skills/guide-ship/scripts/ship_archive.sh` | 增加 handoff 清理 |

### Tests

| File | Responsibility |
|---|---|
| `tests/integration/test_archive_handoff_cleanup.bats` | 测试清理逻辑 |

---

### Task 1: 实现 plan-handoff 清理

**Files:**
- Modify: `skills/guide-ship/scripts/ship_archive.sh`
- Test: `tests/integration/test_archive_handoff_cleanup.bats`

- [ ] **Step 1: Write the failing test**

```bash
@test "archive: cleans up plan-handoff after archive" {
  run archive_change_for_mode "/project" "test-change" "worktree"
  handoff_content=$(cat .rddf/state/.plan-handoff.json)
  [[ "$handoff_content" =~ "archived_at" ]]
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `bats tests/integration/test_archive_handoff_cleanup.bats`
Expected: FAIL

- [ ] **Step 3: Write minimal implementation**

```bash
cleanup_plan_handoff() {
  local project_root="$1"
  local change_name="$2"
  local handoff_file="$project_root/.rddf/state/.plan-handoff.json"
  
  [ ! -f "$handoff_file" ] && return 0
  
  python3 -c "
import json
from datetime import datetime, timezone

with open('$handoff_file') as f:
    data = json.load(f)

# Add archived_at timestamp
data['archived_at'] = datetime.now(timezone.utc).isoformat()

# Update active_changes count
active = data.get('active_changes', 0)
if active > 0:
    data['active_changes'] = active - 1

# Track archived change
if 'archived_changes' not in data:
    data['archived_changes'] = []
data['archived_changes'].append('$change_name')

with open('$handoff_file', 'w') as f:
    json.dump(data, f, indent=2)
"
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `bats tests/integration/test_archive_handoff_cleanup.bats`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add skills/guide-ship/scripts/ship_archive.sh tests/integration/test_archive_handoff_cleanup.bats
git commit -m "feat: cleanup plan-handoff after archive"
```
