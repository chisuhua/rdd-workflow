# fix-test-infrastructure-and-skill-registration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use skill_use("execute") to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 修复 bats 测试基础设施损坏（`load test_helper` 路径解析失败）与 skill 计数断言失效（INSTALL.md 声称 14 个技能，磁盘 17 个）。

**Architecture:** 三处修复：(1) `tests/integration/` 下 7 个 `.bats` 文件的裸 `load test_helper` 改为 `load ../test_helper`（与其余 138 个文件一致）；(2) `skills/INSTALL.md` 的技能计数文案从 14 更新为 17（对齐磁盘实际状态）；(3) 验证 concurrency 测试环境自适应（已通过，无需改动）。`test_detectors.py` 性能失败为环境抖动，不在本 change 范围。

**Tech Stack:** bats-core, bash, pytest

---

## File Structure

### Production Code

| File | Responsibility |
|---|---|
| `skills/INSTALL.md` | 技能计数文案更新 14 → 17（description + 正文） |

### Test Infrastructure

| File | Responsibility |
|---|---|
| `tests/integration/test_adr_gate.bats` 等 7 个文件 | `load test_helper` → `load ../test_helper` 路径修正 |

### Tests

| File | Responsibility |
|---|---|
| `tests/unit/test_doc_contracts.py` | 现有断言锁定计数一致性（无需改动，修复后自动通过） |

---

### Task 1: 修复 bats test_helper 路径解析

**Files:**
- Modify: `tests/integration/test_adr_gate.bats:1`
- Modify: `tests/integration/test_arch_handoff_stale.bats:1`
- Modify: `tests/integration/test_archive_gate.bats:1`
- Modify: `tests/integration/test_archive_handoff_cleanup.bats:1`
- Modify: `tests/integration/test_plan_fallback.bats:1`
- Modify: `tests/integration/test_ship_archive_incomplete.bats:1`
- Modify: `tests/integration/test_skill_version_check.bats:1`
- Test: 手动验证（bats 运行）

- [ ] **Step 1: 确认失败基线**

Run: `cd /workspace/project/rdd-workflow && bats tests/integration/test_adr_gate.bats 2>&1 | head -5`
Expected: FAIL — `bats_load_safe: Could not find 'test_helper'[.bash]`（裸 load 找不到）

- [ ] **Step 2: 修正 load 路径**

将 7 个 `tests/integration/*.bats` 文件第 1 行的裸 `load test_helper` 改为：

```bash
load ../test_helper
```

（与 `tests/integration/` 下其余 138 个文件一致；`tests/smoke.bats` 在 `tests/` 根目录，`load test_helper` 正确，不动）

用以下命令批量修正：

```bash
cd /workspace/project/rdd-workflow
for f in \
  tests/integration/test_adr_gate.bats \
  tests/integration/test_arch_handoff_stale.bats \
  tests/integration/test_archive_gate.bats \
  tests/integration/test_archive_handoff_cleanup.bats \
  tests/integration/test_plan_fallback.bats \
  tests/integration/test_ship_archive_incomplete.bats \
  tests/integration/test_skill_version_check.bats; do
  sed -i '1s/^load test_helper$/load ..\/test_helper/' "$f"
done
grep -rn "^load test_helper$" tests/integration/ || echo "✅ 全部修正"
```

- [ ] **Step 3: 验证修正生效**

Run: `cd /workspace/project/rdd-workflow && bats tests/integration/test_adr_gate.bats 2>&1 | tail -5`
Expected: PASS 或正常测试输出（不再报 `bats_load_safe` 找不到 test_helper）

- [ ] **Step 4: 运行 smoke 确认整体**

Run: `bats tests/smoke.bats 2>&1 | tail -5`
Expected: PASS（smoke 7 个用例）

- [ ] **Step 5: Commit**

```bash
git add tests/integration/*.bats
git commit -m "fix: correct test_helper load path in integration bats files"
```

---

### Task 2: 更新 INSTALL.md 技能计数

**Files:**
- Modify: `skills/INSTALL.md:3`（description frontmatter）
- Modify: `skills/INSTALL.md:11`（正文计数）
- Test: `tests/unit/test_doc_contracts.py::test_install_description_skill_count_matches_disk`

- [ ] **Step 1: 确认失败基线**

Run: `cd /workspace/project/rdd-workflow && python3 -m pytest tests/unit/test_doc_contracts.py::test_install_description_skill_count_matches_disk -v --tb=short`
Expected: FAIL — `INSTALL.md claims 14 skills, disk has 17`

- [ ] **Step 2: 确认磁盘实际计数**

Run: `python3 -c "
import sys; sys.path.insert(0, '.')
from tests.unit.test_doc_contracts import _count_skill_files
print('disk skill files:', _count_skill_files())
"`
Expected: 17

- [ ] **Step 3: 更新 INSTALL.md 计数**

修改 `skills/INSTALL.md`：

L3（frontmatter description）:
```
description: 安装 RDD Workflow 技能——支持全局安装（~/.agents/skills/，跨项目可用）和项目安装（.opencode/skills/rdd-workflow/）。全局安装后从 1 个顶层 INSTALL.md 加 16 个 per-skill 子目录复制全部 17 个子技能到目标位置；自动安装 Python 依赖和 rddf CLI。
```

L11（正文）:
```
本技能将 RDD Workflow 的 17 个子技能安装到当前项目目录。
```

（计数 = `len(top) + len(sub)` = 1 顶层 INSTALL.md + 16 个 per-skill SKILL.md = 17）

- [ ] **Step 4: 运行测试验证**

Run: `cd /workspace/project/rdd-workflow && python3 -m pytest tests/unit/test_doc_contracts.py -v --tb=short`
Expected: PASS（全部 doc contract 断言通过）

- [ ] **Step 5: Commit**

```bash
git add skills/INSTALL.md
git commit -m "fix: sync INSTALL.md skill count with disk (14 → 17)"
```

---

### Task 3: concurrency 测试验证 + 全量回归

**Files:**
- Test: `tests/unit/test_iteration_concurrency.py`, `tests/unit/test_rddf_session.py`（验证）

- [ ] **Step 1: 验证 concurrency 测试已通过（无需改动）**

Run: `cd /workspace/project/rdd-workflow && python3 -m pytest tests/unit/test_iteration_concurrency.py tests/unit/test_rddf_session.py -q --tb=line`
Expected: PASS（38 passed — 当前基线）

- [ ] **Step 2: 运行全量 unit 回归**

Run: `python3 -m pytest tests/unit/ -q --tb=line`
Expected: 1040 passed, 1 failed（仅 `test_detectors.py::test_all_builtin_detectors_run_sequentially_under_500ms` — 环境抖动性能测试，非本 change 引入；若该测试通过则 1041 passed）

- [ ] **Step 3: 验证 guide-design skill 注册**

Run: `ls /home/ubuntu/.agents/skills/guide-design/SKILL.md`
Expected: 文件存在（guide-design 已在磁盘，计数断言修复后 test_package_json_skills_count_within_delta 自动通过）

- [ ] **Step 4: Commit**

```bash
git add -A
git commit -m "chore: verify full regression for test infra fixes" || echo "无新改动,跳过"
```

---

## Self-Review

**Spec 覆盖:**
- ✅ proposal.md In Scope#1 (bats test_helper 路径) → Task 1
- ✅ proposal.md In Scope#2 (test_doc_contracts skill 计数) → Task 2（修复 INSTALL.md 文案而非改测试，保持断言有效）
- ✅ proposal.md In Scope#3 (concurrency 环境依赖) → Task 3（验证已通过）
- ✅ 验收标准: `npm test` 退出 0 / pytest 通过 / guide-design 可用 → Task 1+2+3

**占位符扫描:** 无 TBD/TODO，所有步骤含实际命令与代码。

**类型一致性:** 计数逻辑 `_count_skill_files()` 不变，仅同步 INSTALL.md 文案；bats load 路径与 138 个现有文件一致。
