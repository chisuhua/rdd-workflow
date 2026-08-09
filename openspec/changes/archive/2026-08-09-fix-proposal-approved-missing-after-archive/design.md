# Design — fix-proposal-approved-missing-after-archive

## 1. 背景与目标

`archive-cleanup-plan-files-extension` 完整 lifecycle (design → plan → ship → archive) 后, dashboard 仍报该提案为 📋 待讨论。Root cause 是 **proposal-approved.md 的 plan-phase commit 漏档**:

```
26e30e9 feat(plan): add archive-cleanup-plan-files-extension change
   ⚠️  git add: openspec/changes/<name>/ + openspec/specs/ + improvements/<name>.md
   ❌  漏 add: proposal-approved.md (design 阶段 approve_proposal.sh 写入的行)
```

Dashboard 后续基于 `proposal-approved.md` 的 regex 提取, 漏档条目无法被识别, 报为 pending。

**目标**: 让 4 处潜在的"同步失败"路径全部硬化:
1. `approve_proposal.sh` 写完后立即 `git add`
2. `mark_approved_completed` archive/ fallback
3. dashboard pending filter 加 archive/ bypass
4. plan-done gate warning (soft block)

## 2. 设计概述

### 2.1 Source 修改版图

```
skills/guide-design/scripts/approve_proposal.sh
  └─ L62-66: append_approved 之后
  └─ 新增: git add proposal-approved.md (fail-fast)
  └─ 新增: echo "git add proposal-approved.md done"

_lib/state.sh::mark_approved_completed
  └─ 末尾: 检测 main table 缺行时, compgen -G archive/<date>-<name>
  └─ 若命中: append 到 ## 已实施 section
  └─ 若未命中: emit warning + return 1

_lib/dashboard/__init__.py::collect
  └─ L414-441 段 (Pending): 在 `approved` set 完成后
  └─ 新增: 二次过滤 — compgen -G archive/<date>-<name> for each suggestion
  └─ 命中: skip from data.suggestions / pending_suggestions -= 1

skills/guide-plan.md / guide-plan/scripts/plan_done_gate.sh
  └─ plan-done 末尾 (写 handoff 之前)
  └─ 新增: git status --porcelain proposal-approved.md check
  └─ 命中: emit warning to stderr (no block)
```

### 2.2 关键决策

**Q1: Why not auto-commit proposal-approved.md in approve_proposal.sh?**

A: AI orchestrator 可能在 cascade 调用 — `git add` 不引发 commit, 但 commit 行为可能影响并行 agent。`git add` 是 staging (atomic, recoverable), 不会污染 history。

**Q2: Why compgen -G pattern, not [ -d ] check?**

A: 模式需要匹配 `YYYY-MM-DD-<name>/` 任意日期前缀。`compgen -G` + glob 比 `find` 更轻量, 且在 macOS bash 3.2 和 Linux bash 5.x 都一致 (find 的 `-name` 语法在 macOS 不支持 `+`/`-type` 复杂组合)。

**Q3: Should dashboard filter verify both archive/ and changes/ consistency?**

A: 不需要。`archive/<date>-<name>/` 存在 === 已归档 (这是 arch 阶段事实)。简化判定逻辑: archive 命中 → skip pending。

**Q4: Why warning, not error, in plan-done gate?**

A: plan-done 与 git state 是 orthogonal concerns。该 warning 提示 orchestrator 修复同步, 但不阻断 (因 archive 阶段仍可 fallback 修复)。Hardest-block 反而失败模式变多。

## 3. 影响面与回归风险

### 3.1 正面影响

- ✅ proposal-approved.md 永远不会因漏档 commit 出现 stale 状态
- ✅ dashboard "Pending" 段只显示真正的待审提案
- ✅ 三重 fallback (approve → plan → archive) 任意单点失败可恢复
- ✅ AI orchestrator 在 plan 阶段有显式 warning 提示

### 3.2 防御性测试

| Test | 维度 | 期望 |
|------|------|------|
| `test_approve_proposal_stages_proposal_approved` | approve 后 git status | `M proposal-approved.md` |
| `test_mark_approved_completed_archive_fallback` | archive 存在 + 主表格缺 | append 到 已实施 |
| `test_mark_approved_completed_no_evidence` | archive 不存在 + changes 不存在 | warning + return 1 |
| `test_dashboard_pending_skips_archived` | archive 存在 + 未在 approved | 不在 pending |
| `test_dashboard_pending_keeps_orphan_approval` | 主表格有 + 未在 archive | 不在 pending |
| `test_plan_done_gate_warns_on_dirty` | proposal-approved.md 脏 | warning to stderr |
| `test_plan_done_gate_no_warn_on_clean` | proposal-approved.md clean | no warning |

### 3.3 Out of Scope

- ❌ 不修 `proposal-suggestions.md` 同步 (design 阶段另一回事)
- ❌ 不修 `iteration.json` 同步 (deps 阶段另一回事)
- ❌ 不动 `archive-cleanup-plan-files-extension` 已归档 history (手动补行已足够)

## 4. 验证矩阵

```bash
# 1. 单元测试 (新增 2 个)
python3 -m pytest tests/unit/test_dashboard_pending_filter.py -v
bats tests/integration/test_approve_proposal_staging.bats

# 2. 现有 dashboard 测试
python3 -m pytest tests/unit/test_dashboard_renderer.py -v

# 3. 回归
./test.sh --full --regression
```

## 5. Worktree 流程

```
1. 创建 worktree (.rddf/wt/fix-proposal-approved-missing-after-archive)
2. 修改 4 处 source (approve_proposal.sh / state.sh / dashboard / plan_done_gate)
3. 添加 2 个测试
4. 跑回归
5. 单个聚合 commit (convention: fix(rdd-workflow): auto-stage proposal-approved.md)
6. archive 到 openspec/changes/archive/<date>-fix-proposal-approved-missing-after-archive/
```
