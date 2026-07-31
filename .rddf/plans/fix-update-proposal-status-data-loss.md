# fix-update-proposal-status-data-loss Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use skill_use("execute") to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 修复 `update_proposal_status.py` 在"已实施"表插入新行后 `break` 丢弃剩余行的问题，使归档时已实施表的历史条目全部保留。

**Architecture:** 修改 `update_proposal_status()` 的插入循环控制流：插入新行后不 `break`，继续写剩余行。用 bats 集成测试锁定"已实施表非空"场景（现有测试只覆盖空表）。

**Tech Stack:** Python 3.11+ (update_proposal_status.py), bats-core 1.10+ (集成测试)

---

## File Structure

### Production Code

| File | Responsibility |
|---|---|
| `skills/propose/scripts/update_proposal_status.py` | 修复 `update_proposal_status()` 插入逻辑（break → 继续写剩余行） |

### Tests

| File | Responsibility |
|---|---|
| `tests/integration/test_archive_proposal_status.bats` | 新增"已实施表非空"场景测试；现有空表用例保持通过 |

---

### Task 1: 复现数据丢失 bug（失败测试）

**Files:**
- Modify: `tests/integration/test_archive_proposal_status.bats`
- Test: `tests/integration/test_archive_proposal_status.bats`

- [ ] **Step 1: Write the failing test**

在 `tests/integration/test_archive_proposal_status.bats` 末尾追加测试（已实施表含 2 条历史记录，归档后必须全部保留）：

```bash
@test "archive-proposal-status: preserves existing completed entries" {
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
| [old-a](improvements/old-a.md) | P0 | 2026-07-20 |
| [old-b](improvements/old-b.md) | P1 | 2026-07-22 |
MD
    echo "# old a" > "$TEST_DIR/improvements/old-a.md"
    echo "# old b" > "$TEST_DIR/improvements/old-b.md"
    echo "# new change" > "$TEST_DIR/improvements/new-change.md"
    PROJECT_ROOT="$REPO_ROOT"
    run python3 "$PROJECT_ROOT/skills/propose/scripts/update_proposal_status.py" "new-change" "$TEST_DIR"
    [ "$status" -eq 0 ]
    # 已实施表必须包含 new-change + 全部旧条目 (old-a, old-b)
    completed_entries=$(python3 -c "
with open('$TEST_DIR/proposal-approved.md') as f:
    content = f.read()
section = content.split('## 已实施')[1]
import re
names = re.findall(r'\[([^\]]+)\]\(improvements/', section)
print(' '.join(sorted(names)))
")
    [ "$completed_entries" = "new-change old-a old-b" ]
    rm -rf "$TEST_DIR"
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `bats tests/integration/test_archive_proposal_status.bats`
Expected: FAIL — `completed_entries` 只有 `new-change`（old-a/old-b 因 break 被丢弃）

- [ ] **Step 3: Write minimal implementation**

修改 `skills/propose/scripts/update_proposal_status.py` 第 43-58 行的插入循环。当前逻辑：

```python
    result = []
    for i, line in enumerate(new_lines):
        result.append(line)
        if line.startswith("## 已实施") and not inserted:
            j = i + 1
            while j < len(new_lines) and (
                new_lines[j].startswith("|") or new_lines[j].strip() == ""
            ):
                j += 1
            completed_row = f"| [{change_name}](improvements/{change_name}.md) | {priority} | {date.today().isoformat()} |\n"
            result.insert(j, completed_row)
            inserted = True
            break   # ← BUG: break 丢弃剩余行（表头、分隔线、旧条目）
```

修复为**不 break**，插入后继续处理剩余行：

```python
    result = []
    for i, line in enumerate(new_lines):
        result.append(line)
        if line.startswith("## 已实施") and not inserted:
            j = i + 1
            while j < len(new_lines) and (
                new_lines[j].startswith("|") or new_lines[j].strip() == ""
            ):
                j += 1
            completed_row = f"| [{change_name}](improvements/{change_name}.md) | {priority} | {date.today().isoformat()} |\n"
            result.insert(j, completed_row)
            inserted = True
            # 不再 break —— 后续行（表头、分隔线、旧条目）继续被 append
```

- [ ] **Step 4: Run test to verify it passes**

Run: `bats tests/integration/test_archive_proposal_status.bats`
Expected: PASS — 全部用例通过（含新增的 preserves-existing-completed-entries）

- [ ] **Step 5: Commit**

```bash
git add tests/integration/test_archive_proposal_status.bats skills/propose/scripts/update_proposal_status.py
git commit -m "fix: preserve existing completed entries in update_proposal_status"
```

---

### Task 2: 连续归档场景验证

**Files:**
- Modify: `tests/integration/test_archive_proposal_status.bats`
- Test: `tests/integration/test_archive_proposal_status.bats`

- [ ] **Step 1: Write the failing test**

追加连续归档测试（3 个 change 依次归档，条目数 = 原始数 + 3）：

```bash
@test "archive-proposal-status: consecutive archives accumulate entries" {
    TEST_DIR=$(mktemp -d)
    mkdir -p "$TEST_DIR/improvements"
    cat > "$TEST_DIR/proposal-approved.md" <<'MD'
# 已批准提案

| Proposal | Priority | Approved |
|----------|----------|----------|
| [c1](improvements/c1.md) | P0 | 2026-07-31 |
| [c2](improvements/c2.md) | P1 | 2026-07-31 |
| [c3](improvements/c3.md) | P2 | 2026-07-31 |

## 已实施

| Proposal | Priority | Completed |
|----------|----------|-----------|
| [base](improvements/base.md) | P1 | 2026-07-01 |
MD
    echo "# x" > "$TEST_DIR/improvements/c1.md"
    echo "# x" > "$TEST_DIR/improvements/c2.md"
    echo "# x" > "$TEST_DIR/improvements/c3.md"
    echo "# x" > "$TEST_DIR/improvements/base.md"
    PROJECT_ROOT="$REPO_ROOT"
    for c in c1 c2 c3; do
        run python3 "$PROJECT_ROOT/skills/propose/scripts/update_proposal_status.py" "$c" "$TEST_DIR"
        [ "$status" -eq 0 ]
    done
    count=$(grep -c 'improvements/' "$TEST_DIR/proposal-approved.md" 2>/dev/null || true)
    # 已批准区 0 + 已实施区 4 (base+c1+c2+c3)
    [ "$count" -eq 4 ]
    rm -rf "$TEST_DIR"
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `bats tests/integration/test_archive_proposal_status.bats`
Expected: FAIL — 每次归档后条目数递减（break 丢弃旧条目）

- [ ] **Step 3: Write minimal implementation**

无需新实现——Task 1 的修复已使循环不再 break。若此步失败说明 Task 1 修复不完整，检查 `result.insert(j, completed_row)` 后是否有残留 `break`。

- [ ] **Step 4: Run test to verify it passes**

Run: `bats tests/integration/test_archive_proposal_status.bats`
Expected: PASS — 连续归档 3 个 change 后已实施区共 4 条

- [ ] **Step 5: Commit**

```bash
git add tests/integration/test_archive_proposal_status.bats
git commit -m "test: consecutive archive accumulation scenario"
```

---

### Task 3: 空表场景回归 + 全量验证

**Files:**
- Test: `tests/integration/test_archive_proposal_status.bats`
- Modify: 无（验证既有行为）

- [ ] **Step 1: Write the failing test**

无新测试——现有空表用例（`normal update changes status`）已存在，作为回归基线。验证其 fixture 中"已实施"表为空（仅表头）时插入行为不变。

- [ ] **Step 2: Run test to verify it fails**

Run: `bats tests/integration/test_archive_proposal_status.bats`
Expected: 现有空表用例通过（回归基线无失败）

- [ ] **Step 3: Write minimal implementation**

无实现变更。若空表用例失败，检查插入位置逻辑（`j = i + 1` 跳过表头/分隔线后插入）未被 Task 1 改动破坏。

- [ ] **Step 4: Run test to verify it passes**

Run:
```bash
bats tests/integration/test_archive_proposal_status.bats
python3 -m pytest tests/unit/ -q --tb=short
```
Expected: 全部通过（bats 新增 2 用例 + 既有用例；pytest 全量回归）

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "test: verify empty-table behavior unchanged + full regression"
```
