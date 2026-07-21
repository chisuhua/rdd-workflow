# audit-attach-detach-calls Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use skill_use("execute") to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 产出 attach_change/detach_change 调用链审计报告, 列出所有调用点 + 缺失 hook, 不修改任何源代码。

**Architecture:** 纯只读静态分析。grep 扫描调用点 → 追踪 hook 调用矩阵 → 对比 ADR-0017 契约 → 写入 markdown 报告。每个 Task 含验证步骤 (替代 TDD test, 因审计无 production code)。

**Tech Stack:** bash/grep (静态扫描) + markdown (报告) + pytest (regression 验证)

---

## File Structure

### Production Code

| File | Responsibility |
|---|---|
| (none) | 本 change 为 audit-only, 不修改 production code |

### Audit Artifacts

| File | Responsibility |
|---|---|
| `openspec/changes/audit-attach-detach-calls/design.md` | 审计方法论 (已写) |
| `openspec/changes/audit-attach-detach-calls/tasks.md` | 任务分解 (已写) |
| `openspec/changes/audit-attach-detach-calls/proposal.md` | 变更提案 (已 fill) |
| `.rddf/state/attach-detach-audit.md` | 审计报告 (本 plan 产出) |

### Tests

| File | Responsibility |
|---|---|
| (none modified) | `tests/unit/test_rddf_session.py` 仅作为 regression baseline, 不修改 |

---

## Task 1: 静态扫描所有 attach_change/detach_change 调用点

**Files:**
- Read: `skills/` (全树)
- Read: `tests/` (全树)
- Read: `docs/` (全树)
- Produce: 调用点清单 (写入审计报告 §3)

- [ ] **Step 1: Write the failing test (验证条件)**

审计报告 §3 必须包含一个表格, 列出每个调用点的 文件:行号 + 类型 + 上下文。
验证条件: 报告存在且表格至少 6 行 (已知有 ≥6 个匹配文件)。

```bash
# 验证: 报告 §3 表格行数 >= 6
test -f .rddf/state/attach-detach-audit.md
grep -c '^| .*|.*|.*|.*|$' .rddf/state/attach-detach-audit.md
```

- [ ] **Step 2: Run test to verify it fails**

Run: `test -f .rddf/state/attach-detach-audit.md && echo EXISTS || echo MISSING`
Expected: `MISSING` (报告尚未生成)

- [ ] **Step 3: Write minimal implementation (执行扫描)**

```bash
# 全量扫描, 分类记录
grep -rn 'attach_change\|detach_change' skills/ tests/ docs/ \
  --include="*.py" --include="*.sh" --include="*.md" --include="*.bats" \
  > /tmp/audit_grep_raw.txt
```

对每个匹配分类:
- `definition` - 函数定义行 (`def attach_change` / `def detach_change`)
- `import` - import 行 (`from ... import attach_change`)
- `production-call` - 生产代码中的 `coord.attach_change(` / `coord.detach_change(`
- `test-call` - 测试代码中的 `coordinator.attach_change(` / `coordinator.detach_change(`
- `doc-reference` - 文档/注释中的提及

- [ ] **Step 4: Run test to verify it passes**

Run: 扫描完成后, 确认清单完整 (覆盖 rddf_session.py / rddf_session_hooks.sh / test_rddf_session.py / proposal.md / proposal-suggestions.md / archived tasks.md)
Expected: ≥6 个文件被记录

- [ ] **Step 5: Commit**

```bash
# 数据已收集, 留待 Task 4 写入报告; 此处不单独 commit (Task 4 统一 commit)
echo "Task 1 完成: 调用点清单已收集"
```

---

## Task 2: 追踪 3 个 hook × 3 个 guide skill 调用矩阵

**Files:**
- Read: `skills/rddf-session/scripts/rddf_session_hooks.sh` (hook 实现)
- Read: `skills/guide-arch/SKILL.md` (arch 调用)
- Read: `skills/guide-plan/SKILL.md` (plan 调用)
- Read: `skills/guide-ship/SKILL.md` (ship 调用)
- Produce: 3×3 调用矩阵 (写入审计报告 §4)

- [ ] **Step 1: Write the failing test (验证条件)**

报告 §4 必须含一个 3×3 矩阵: rows = hook (entry/close/heartbeat), cols = guide skill (arch/plan/ship), cells = `✓ called` / `✗ not called` / `N/A`。

- [ ] **Step 2: Run test to verify it fails**

报告 §4 不存在 (报告未生成)。

- [ ] **Step 3: Write minimal implementation (追踪调用)**

```bash
# 对每个 guide skill grep hook 调用
for skill in guide-arch guide-plan guide-ship; do
  echo "=== $skill ==="
  grep -n 'rddf_session_hook_entry\|rddf_session_hook_close\|rddf_session_hook_heartbeat' \
    "skills/$skill/SKILL.md"
done

# 对每个 hook 检查其 Python 实现内是否调用 attach/detach
grep -n 'attach_change\|detach_change' \
  skills/rddf-session/scripts/rddf_session_hooks.sh
```

- [ ] **Step 4: Run test to verify it passes**

确认矩阵数据完整:
- guide-arch: entry ✓ (L85), close ✓ (L533), heartbeat ✗
- guide-plan: entry ✓ (L86), close ✓ (L477), heartbeat ✗
- guide-ship: entry ✓ (L42), heartbeat ✓ (L506, 含 detach_change), close ✓ (L591)

- [ ] **Step 5: Commit**

数据收集完成, 留待 Task 4 统一写入报告。

---

## Task 3: ADR-0017 契约期望对比

**Files:**
- Read: `docs/adr/ADR-0017-rddf-session.md`
- Read: `docs/v2-multi-session-guide.md` §"自动管理" (L455-461)
- Produce: 期望 vs 实际差异表 (写入审计报告 §5)

- [ ] **Step 1: Write the failing test (验证条件)**

报告 §5 必须含两列对比: 期望行为 (引用 ADR/guide) vs 实际行为 (引用代码 行号)。

- [ ] **Step 2: Run test to verify it fails**

报告 §5 不存在。

- [ ] **Step 3: Write minimal implementation (契约对比)**

读取 `docs/v2-multi-session-guide.md:455-461`:
```
guide-ship 入口 -> 创建 kind=stage_ship, parent=最新 stage_plan
所有 attached_changes archived -> stage_ship -> completed
```

对比实际:
- 期望: ship entry 时 attach 当前 change -> 实际: `rddf_session_hook_entry` (hooks.sh:39-96) 内部 **不调用** attach_change
- 期望: archive 时 detach 已归档 change -> 实际: `rddf_session_hook_heartbeat` (hooks.sh:150-190) 在 archive 后调用, 内部 L184 调用 `coord.detach_change(sid, change_name)` ✓
- 期望: 所有 attached_changes archived -> ship completed -> 实际: ship-done close hook 不检查 attached_changes 是否为空

- [ ] **Step 4: Run test to verify it passes**

确认差异表含至少 3 行 (entry 缺 attach / heartbeat 有 detach ✓ / close 不检查空)。

- [ ] **Step 5: Commit**

数据收集完成, 留待 Task 4 统一写入报告。

---

## Task 4: 生成审计报告 .rddf/state/attach-detach-audit.md

**Files:**
- Create: `.rddf/state/attach-detach-audit.md`

- [ ] **Step 1: Write the failing test (报告存在性 + 章节完整性)**

```bash
test -f .rddf/state/attach-detach-audit.md
# 7 个章节都必须存在
for section in "Executive Summary" "Definitions" "Call Site Inventory" \
               "Hook Call Chain" "Expected vs Actual" "Missing Hooks" \
               "Recommendations"; do
  grep -q "## .*$section" .rddf/state/attach-detach-audit.md || \
    echo "MISSING: $section"
done
```

- [ ] **Step 2: Run test to verify it fails**

Run: `test -f .rddf/state/attach-detach-audit.md && echo EXISTS || echo MISSING`
Expected: `MISSING`

- [ ] **Step 3: Write minimal implementation (生成报告)**

写入 `.rddf/state/attach-detach-audit.md`, 含 7 个章节:

1. **Executive Summary** - 一句话: attach_change 在生产代码中 0 个调用点, detach_change 1 个 (heartbeat hook); ADR-0017 期望的 ship-entry attach 缺失。
2. **Definitions** - 同 design.md §4
3. **Call Site Inventory** - 表格: 文件:行号 | 类型 | 上下文
4. **Hook Call Chain** - 3×3 矩阵 + hook 内部 attach/detach 调用表
5. **Expected vs Actual** - ADR-0017 契约 vs 实际行为 (3 行)
6. **Missing Hooks** - 列出缺失的 attach 时机 + 影响
7. **Recommendations** - 后续修复建议 (非强制)

- [ ] **Step 4: Run test to verify it passes**

Run: 章节完整性测试 (Step 1 命令)
Expected: 全部章节存在, 无 MISSING 输出

- [ ] **Step 5: Commit**

```bash
# 注: .rddf/state/ 是 gitignored, 报告本身不会被 commit
# 但本 change 的 artifacts (proposal/design/tasks) 需要 commit
# 报告副本可考虑放入 openspec/changes/audit-attach-detach-calls/ 留档
cp .rddf/state/attach-detach-audit.md \
   openspec/changes/audit-attach-detach-calls/audit-report.md
git add openspec/changes/audit-attach-detach-calls/
git commit -m "audit(attach-detach): fill proposal/design/tasks + produce audit report"
```

---

## Task 5: 验证 + 提交 + 归档

**Files:**
- Verify: 全 worktree git status
- Run: `pytest tests/unit/test_rddf_session.py -q`

- [ ] **Step 1: Write the failing test (验证条件)**

- git status 仅显示本 change 的 artifacts (无源文件修改)
- pytest test_rddf_session.py 全部通过 (无 regression)
- 报告副本存在于 `openspec/changes/audit-attach-detach-calls/audit-report.md`

- [ ] **Step 2: Run test to verify it fails**

```bash
git status --short
python3 -m pytest tests/unit/test_rddf_session.py -q --tb=short
test -f openspec/changes/audit-attach-detach-calls/audit-report.md
```

- [ ] **Step 3: Write minimal implementation (最终提交)**

```bash
# 确认无源文件修改 (仅本 change artifacts)
git status --short

# 确认 regression 测试通过
python3 -m pytest tests/unit/test_rddf_session.py -q --tb=short

# 已在 Task 4 Step 5 commit, 此处仅确认
git log --oneline -1
```

- [ ] **Step 4: Run test to verify it passes**

Run: 上述 3 条命令
Expected:
- git status: 仅 `openspec/changes/audit-attach-detach-calls/` 下文件
- pytest: 全部通过
- audit-report.md 存在

- [ ] **Step 5: Commit + Archive**

```bash
# 如果 Task 4 已 commit, 此处跳过
git status --porcelain || true

# 归档本 change (轻量模式: 直接在 worktree 内)
# 实际归档由 guide-ship Phase 3 处理, 此处仅标记 tasks.md 完成
```

---

## Self-Review

**1. Spec 覆盖**:
- proposal.md "查找所有调用点" → Task 1 ✓
- proposal.md "确认 hook 调用链" → Task 2 ✓
- proposal.md "依据 ADR-0017 列出缺失 hook" → Task 3 ✓
- proposal.md "输出 audit report" → Task 4 ✓
- proposal.md "不修改代码" → 全 plan 无 .py/.sh 修改 ✓

**2. 占位符扫描**: 无 TBD/TODO; 每个 Step 都有具体命令或内容。

**3. 类型一致性**: 调用点引用的 函数名/文件路径 在所有 Task 中一致 (attach_change / detach_change / rddf_session_hook_entry/_close/_heartbeat)。

**4. 文件路径**: 所有 `**Files:**` 路径均存在或为本 plan 产出 (报告)。
