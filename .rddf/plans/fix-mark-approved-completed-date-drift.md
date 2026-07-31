# fix-mark-approved-completed-date-drift Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use skill_use("execute") to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 修复 `state.sh::mark_approved_completed` 幂等命中"已实施"区时覆盖原完成日期的问题，使重复归档/重放归档保留历史审计日期。

**Architecture:** 在 `mark_approved_completed` 的 Python 内联逻辑中，区分"已批准区"与"已实施区"的条目匹配：当 change 已在"已实施"区时直接退出（保留原行含原日期），不删除重插。bats/单元测试锁定幂等日期保留场景。

**Tech Stack:** bash + python3 内联（state.sh 既有模式）, bats-core / pytest

---

## File Structure

### Production Code

| File | Responsibility |
|---|---|
| `skills/_lib/state.sh::mark_approved_completed` | 幂等命中已实施区时保留原日期（不重插） |

### Tests

| File | Responsibility |
|---|---|
| `tests/unit/test_mark_approved_completed.py`（新增）或 `tests/integration/` | 幂等日期保留测试 |

---

### Task 1: 幂等命中已实施区保留原日期（失败测试）

**Files:**
- Modify: `skills/_lib/state.sh::mark_approved_completed`（L202-275）
- Test: `tests/unit/test_mark_approved_completed.py`（新增）

- [ ] **Step 1: Write the failing test**

新增 `tests/unit/test_mark_approved_completed.py`（bash 函数测试通过 bats 更直接——改用 `tests/integration/test_mark_approved_completed.bats`）：

```bash
@test "mark-approved-completed: idempotent call preserves original completion date" {
    TEST_DIR=$(mktemp -d)
    mkdir -p "$TEST_DIR/improvements"
    cat > "$TEST_DIR/proposal-approved.md" <<'MD'
# 已批准提案

| Proposal | Priority | Approved |
|----------|----------|----------|

## 已实施

| Proposal | Priority | Completed |
|----------|----------|-----------|
| [fix-scan-state-bats](improvements/fix-scan-state-bats.md) | P2 | 2026-07-23 |
MD
    echo "# x" > "$TEST_DIR/improvements/fix-scan-state-bats.md"
    source "$REPO_ROOT/skills/_lib/state.sh"
    # 幂等调用：change 已在已实施区（原日期 2026-07-23）
    run mark_approved_completed "$TEST_DIR" "fix-scan-state-bats"
    [ "$status" -eq 0 ]
    # 日期必须保持 2026-07-23，不能被改写为调用当天
    run grep -o '2026-07-23' "$TEST_DIR/proposal-approved.md"
    [ "$status" -eq 0 ]
    run grep -c "$(date -u +%Y-%m-%d)" "$TEST_DIR/proposal-approved.md"
    [ "$status" -ne 0 ]
    rm -rf "$TEST_DIR"
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `bats tests/integration/test_mark_approved_completed.bats`
Expected: FAIL — 日期被改写为调用当天（当前：幂等检查命中已实施区后删除重插，无条件用 `date -u +%Y-%m-%d`）

- [ ] **Step 3: Write minimal implementation**

修改 `skills/_lib/state.sh::mark_approved_completed`（L202-275）的 Python 内联逻辑。当前幂等检查：

```python
# Idempotency: check if already in completed section
in_completed = False
for line in lines:
    if f'[{name}]' in line:
        in_completed = True
        break

# Find entry in approved table
approved_idx = None
approved_line = None
for i, line in enumerate(lines):
    if f'[{name}]' in line and line.strip().startswith('|'):
        approved_idx = i
        approved_line = line
        break

# Already in completed table
if in_completed and approved_idx is None:
    sys.exit(0)
```

修复为：**区分条目所在区**。若条目出现在 `## 已实施` 之后（幂等命中），直接退出保留原行：

```python
# Split sections: everything after '## 已实施' is the completed table
completed_section_start = None
for i, line in enumerate(lines):
    if line.startswith('## 已实施'):
        completed_section_start = i
        break

# Idempotency: if entry already in completed table, keep original row (preserve date)
for i, line in enumerate(lines):
    if f'[{name}]' in line and line.strip().startswith('|'):
        if completed_section_start is not None and i > completed_section_start:
            sys.exit(0)  # already completed — preserve original date, no rewrite

# Find entry in approved table (only in the approved section)
approved_idx = None
approved_line = None
for i, line in enumerate(lines):
    if f'[{name}]' in line and line.strip().startswith('|'):
        if completed_section_start is not None and i > completed_section_start:
            continue  # skip completed-section rows
        approved_idx = i
        approved_line = line
        break

if approved_idx is None:
    sys.exit(0)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `bats tests/integration/test_mark_approved_completed.bats`
Expected: PASS — 幂等调用后日期保持 2026-07-23

- [ ] **Step 5: Commit**

```bash
git add skills/_lib/state.sh tests/integration/test_mark_approved_completed.bats
git commit -m "fix: preserve original completion date on idempotent mark_approved_completed"
```

---

### Task 2: 首次归档行为保持

**Files:**
- Test: `tests/integration/test_mark_approved_completed.bats`

- [ ] **Step 1: Write the failing test**

追加首次归档测试（从已批准区移入时日期 = 调用当天，行为不变）：

```bash
@test "mark-approved-completed: first-time archive uses today's date" {
    TEST_DIR=$(mktemp -d)
    mkdir -p "$TEST_DIR/improvements"
    cat > "$TEST_DIR/proposal-approved.md" <<'MD'
# 已批准提案

| Proposal | Priority | Approved |
|----------|----------|----------|
| [new-change](improvements/new-change.md) | P1 | 2026-07-31 |

## 已实施

| Proposal | Priority | Completed |
|----------|----------|-----------|
MD
    echo "# x" > "$TEST_DIR/improvements/new-change.md"
    source "$REPO_ROOT/skills/_lib/state.sh"
    run mark_approved_completed "$TEST_DIR" "new-change"
    [ "$status" -eq 0 ]
    run grep -c "$(date -u +%Y-%m-%d)" "$TEST_DIR/proposal-approved.md"
    [ "$status" -eq 0 ]
    rm -rf "$TEST_DIR"
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `bats tests/integration/test_mark_approved_completed.bats`
Expected: 基线——首次归档使用当天日期（Task 1 修复不应破坏此行为）

- [ ] **Step 3: Write minimal implementation**

无新实现——Task 1 的修复仅影响"已实施区命中"分支，首次归档路径（已批准区匹配）行为不变。

- [ ] **Step 4: Run test to verify it passes**

Run: `bats tests/integration/test_mark_approved_completed.bats`
Expected: PASS — 首次归档日期 = 调用当天

- [ ] **Step 5: Commit**

```bash
git add tests/integration/test_mark_approved_completed.bats
git commit -m "test: first-time archive uses today's date"
```

---

### Task 3: 全量回归

**Files:**
- Test: 全量

- [ ] **Step 1: Write the failing test**

无新测试——全量回归验证。

- [ ] **Step 2: Run test to verify it fails**

Run:
```bash
bats tests/integration/test_mark_approved_completed.bats
bats tests/smoke.bats
python3 -m pytest tests/unit/ -q --tb=short
```
Expected: 基线——仅记录现有状态

- [ ] **Step 3: Write minimal implementation**

无实现变更。若 smoke/unit 失败，检查 `state.sh` 其他调用方（`archive.sh`、`update_proposal_status.py`）是否受 sections 区分逻辑影响。

- [ ] **Step 4: Run test to verify it passes**

Run:
```bash
bats tests/integration/test_mark_approved_completed.bats
bats tests/smoke.bats
python3 -m pytest tests/unit/ -q --tb=short
```
Expected: 全部通过

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "test: full regression for mark_approved_completed fix"
```
