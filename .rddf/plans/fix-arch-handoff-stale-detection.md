# fix-arch-handoff-stale-detection Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use skill_use("execute") to implement this plan task-by-task.

**Goal:** scan_state() 增加 arch-handoff 文件系统交叉验证，检测过期 handoff

**Architecture:** 当 arch-handoff.adr_count == 0 时，检查文件系统 ADR 文件

**Tech Stack:** Bash

---

## File Structure

### Production Code

| File | Responsibility |
|---|---|
| `skills/guide/scripts/scan-state.sh` | 增加交叉验证逻辑 |

### Tests

| File | Responsibility |
|---|---|
| `tests/integration/test_arch_handoff_stale.bats` | 测试过期检测 |

---

### Task 1: 实现 arch-handoff 过期检测

**Files:**
- Modify: `skills/guide/scripts/scan-state.sh`
- Test: `tests/integration/test_arch_handoff_stale.bats`

- [ ] **Step 1: Write the failing test**

```bash
@test "scan-state: detects stale arch-handoff" {
  # Setup: arch-handoff says 0 ADRs but filesystem has 5
  run scan_state
  [[ "$output" =~ "arch-handoff 可能过期" ]]
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `bats tests/integration/test_arch_handoff_stale.bats`
Expected: FAIL

- [ ] **Step 3: Write minimal implementation**

```bash
check_arch_handoff_stale() {
  local project_root="$1"
  local arch_handoff="$project_root/.rddf/state/.arch-handoff.json"
  
  [ ! -f "$arch_handoff" ] && return 0
  
  local adr_count=$(python3 -c "import json; d=json.load(open('$arch_handoff')); print(d.get('adr_count', 0))" 2>/dev/null || echo 0)
  
  if [ "$adr_count" -eq 0 ]; then
    local fs_adr_count=$(ls "$project_root"/docs/adr/ADR-*.md 2>/dev/null | wc -l)
    if [ "$fs_adr_count" -gt 0 ]; then
      echo "⚠️  arch-handoff 记录 0 ADRs 但文件系统发现 $fs_adr_count 个 — handoff 可能过期"
      return 1
    fi
  fi
  return 0
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `bats tests/integration/test_arch_handoff_stale.bats`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add skills/guide/scripts/scan-state.sh tests/integration/test_arch_handoff_stale.bats
git commit -m "feat: add arch-handoff stale detection"
```
