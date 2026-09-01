# fix-design-done-gate-status-prefix-match

**优先级**: P0 | **来源**: 2026-08-31 design 阶段发现 — `bypass-audit-mechanism` 状态为 `延迟 (2026-08-28, 维持 v3.2 deferred 决策)` 被 design-done gate 误判为"无决策"
**阶段**: v2.2 | **分类**: design
**类型**: bug fix

> **症状**：`guide-design` Phase 4 的 `check_design_done_gate()` 用精确字符串匹配状态列（`"$status" != "已批准"`），但真实状态常带后缀（如 `延迟 (2026-08-28, 维持 v3.2 deferred 决策)`），导致含后缀的有效决策被误报为"无决策"，design-done 门控失败。
> **根因**：`check_design_done_gate()` 内联在 `skills/guide-design/SKILL.md` Phase 4（约 L490-510 区域），使用 bash 精确字符串比较而非前缀/子串匹配。
> **临时绕过**：本次会话用 Python `startswith` 重新实现门控检查绕过内联 bash bug。

## 架构依据

**症状 (2026-08-31 design 阶段, 2 个 P1 change 触发)**:

- 2 个新提案 `reduce-rdd-workflow-tool-call-friction` + `worktree-context-persistence` 已批准（status `已批准`）
- 1 个旧提案 `bypass-audit-mechanism` 状态为 `延迟 (2026-08-28, 维持 v3.2 deferred 决策)`
- design-done gate 检查遍历 `proposal-suggestions.md`，对每行 status 列做精确比较：
  ```bash
  if [ "$status" != "已批准" ] && [ "$status" != "已拒绝" ] && [ "$status" != "延迟" ]; then
    echo "$status"
  fi
  ```
- `bypass-audit-mechanism` 的 status 为 `延迟 (2026-08-28, 维持 v3.2 deferred 决策)`，不等于 `延迟` → 被误报为 `尚无决策`
- 本次会话需用 Python `startswith` 模式手动重写 gate 才通过：
  ```python
  if not any(status.startswith(v) for v in ("已批准", "已拒绝", "延迟")):
      pending.append(status)
  ```
- **注意**：后续 design session 若严格依赖内联 bash gate，将再次卡住（每次 3-5 分钟人工绕过）

**根因分析**:

`skills/guide-design/SKILL.md` Phase 4 `check_design_done_gate()` 内联 bash（提取自 v2.1 设计阶段的实现）：

```bash
local pending=$(grep -E '^\s*\|\s*\[' "$PROJECT_ROOT/proposal-suggestions.md" 2>/dev/null | \
    while IFS='|' read -r _ _ _ _ _ status _; do
      status=$(echo "$status" | xargs)
      if [ "$status" != "已批准" ] && [ "$status" != "已拒绝" ] && [ "$status" != "延迟" ]; then
        echo "$status"
      fi
    done)
```

问题：`[ "$status" != "已批准" ]` 是精确字符串比较。但 `proposal-suggestions.md` 的状态列会带人工追加的决策后缀（如日期、理由），如 `延迟 (2026-08-28, 维持 v3.2 deferred 决策)` 或 `已批准 (2026-09-01)`。

**这不仅是理论风险**：proposal-suggestions.md 的状态列没有 schema 约束，用户/工具可以自由追加决策上下文（如 `已批准 (2026-08-30, 关联 phase-4)`）。任何带后缀的条目都会让 gate 误报。

**影响范围**:

- 所有带决策后缀的 proposal 状态（延迟/已批准/已拒绝 + 括号备注）都会让 design-done gate 失败
- 触发时每次需人工绕过（3-5 分钟）
- 未来 `bypass-audit-mechanism`（延迟）这类带后缀的提案只要还在 suggestions 中，design-done 就持续失败

## 范围

### In Scope

**A. 修复内联 bash gate（`skills/guide-design/SKILL.md` Phase 4）**:

- 将 `check_design_done_gate()` 的精确比较改为前缀匹配：
  ```bash
  case "$status" in
    已批准*|已拒绝*|延迟*) : ;;  # valid decision (with optional suffix)
    *) echo "$status" ;;        # pending/unknown
  esac
  ```
  或 bash 参数扩展：
  ```bash
  if [[ "$status" != 已批准* && "$status" != 已拒绝* && "$status" != 延迟* ]]; then
    echo "$status"
  fi
  ```
- 保留 `xargs` trim（去首尾空白）
- 保留 4-option 软提示流程（approve/reject/defer/skip）不变

**B. 提取内联 bash 到 helper（推荐，对齐 Round A/B/C 模式）**:

- 新建 `skills/guide-design/scripts/design_done_check.sh`（public function `check_design_done_gate <project_root>`）
- 复刻现有逻辑 + 前缀匹配修复
- `skills/guide-design/SKILL.md` Phase 4 改为 `source` 该 helper 并调用（与 ship_plan.sh 的 `run_ship_phase1` 模式一致）
- 保留现有 Hub gates（`check-hub-pending` / `check-cross-repo-approvals`）接线在 helper 中

**C. 测试**:

- `tests/unit/test_design_done_gate.sh` 单元测试（bash，模拟 proposal-suggestions.md 不同状态变体）
  - `design-done: 已批准 exact pass`
  - `design-done: 已批准 with suffix pass`
  - `design-done: 延迟 with suffix pass` ← 本 bug 的回归测试
  - `design-done: 待审查 fails (pending)`
  - `design-done: empty status fails`
- `tests/integration/test_design_done_gate.bats` 集成测试
  - `design-done: SKILL.md calls helper (not inline)`
  - `design-done: end-to-end with 延迟 (suffix) proposal passes`

### Out Scope

- **不修改** `proposal-suggestions.md` 状态列格式（带后缀是合法用法，由 gate 适配而非限制用户）
- **不修改** `approve_proposal.sh` / `design_proposal_review.sh` 的审批逻辑
- **不修改** Hub gates（`design_done_gate.py`）— 独立 Python 实现，无此 bug
- **不修改** `bypass-audit-mechanism` 提案本身（状态已延迟，可保留）

## 关键场景

### 场景 1: 延迟状态带后缀（本 bug 的直接触发）

- **GIVEN** `proposal-suggestions.md` 有一行状态 `延迟 (2026-08-28, 维持 v3.2 deferred 决策)`
- **WHEN** 用户选择"完成设计阶段 → 进入设计门控"
- **THEN**
  - gate 检查该行 status，前缀匹配 `延迟*` 通过
  - 不报 `❌ design-done 失败: 以下提案尚无决策:`
  - gate 继续，输出 `✅ 所有提案已有决策，design-done 门控通过`

### 场景 2: 已批准带后缀

- **GIVEN** 状态 `已批准 (2026-08-30, 关联 phase-4 多方对称与回归)`
- **WHEN** gate 检查
- **THEN** `已批准*` 前缀匹配通过，不误报

### 场景 3: 待审查（真正的 pending）

- **GIVEN** 状态 `待审查`（无决策）
- **WHEN** gate 检查
- **THEN** 前缀匹配 `待审查*` 不匹配任何有效决策 → 被列出为 `尚无决策`，gate fail，符合预期

### 场景 4: 空状态 / 空白行

- **GIVEN** `proposal-suggestions.md` 某行状态列空白（`| |`）
- **WHEN** gate 检查
- **THEN** trim 后为空字符串，不匹配任何有效前缀 → 被列为 pending，gate fail（符合预期，提示需要决策）

### 场景 5: 混合状态（部分带后缀部分无）

- **GIVEN** 3 行：`已批准`（无后缀） + `延迟 (2026-08-28)`（带后缀） + `待审查`
- **WHEN** gate 检查
- **THEN** 前 2 行通过（已批准 + 延迟带后缀），第 3 行 `待审查` 被列 pending → gate fail 仅列 1 个

## 技术约束

- **MUST NOT**: 改 `proposal-suggestions.md` 的 schema/状态词汇（`已批准`/`已拒绝`/`延迟`/`待审查` 保持）
- **MUST NOT**: 改 design-done gate 的通过条件（所有提案必须有决策才通过）
- **MUST NOT**: 引入新依赖（bash 原生参数扩展 / case 语句即可）
- **MUST**: 保留 4-option 审批流程（approve/reject/defer/skip）语义不变
- **SHOULD**: 与既有 helper 提取模式（Round A/B/C）一致，避免内联 bash 再次 drift
- **SHOULD**: `check_design_done_gate` 提取后 SKILL.md 中保留同构逻辑（供无 helper 环境降级）

## 验收标准

### 单元与集成测试

- [ ] `tests/unit/test_design_done_gate.sh` 5 个单元测试 PASS（含延迟带后缀回归测试）
- [ ] `tests/integration/test_design_done_gate.bats` 2 个集成测试 PASS
- [ ] 复测 `proposal-suggestions.md` 当前含 `延迟 (2026-08-28...)` 状态时 gate 通过

### 端到端验证

- [ ] 模拟 2 个带后缀状态 + 1 个待审查：gate 正确列出仅 1 个 pending
- [ ] 模拟全部带后缀（已批准* / 延迟* / 已拒绝*）：gate 通过
- [ ] 与 `fix-specs-auto-generate-in-design-precreated` (P0-1) 无交互：approve 流程不变，仅 gate 检查修复

### 文档化

- [ ] `skills/guide-design/SKILL.md` Phase 4 更新为 source helper（或明确前缀匹配语义注释）
- [ ] `docs/change-quality-guide.md` 加"proposal 状态后缀"说明段（状态可带 `(日期, 理由)` 后缀，gate 用前缀匹配）

### 兼容性验证

- [ ] 复测 `bypass-audit-mechanism`（延迟 + 后缀）design-done 通过，无需人工 Python 绕过
- [ ] 复测 `proposal-approved.md` 的 `已实施` 状态不受影响（那是 approve 后的归档状态，不走 design-done）
- [ ] 与 `design_done_gate.py`（Hub gates）不冲突：check-hub-pending / check-cross-repo-approvals 仍接线

### 副作用监测

- [ ] ship 后 30 天观察期：design-done gate 人工绕过次数降至 0（历史：每次 3-5 分钟）
- [ ] 不引入新的 KNOWN_FAILURES 条目

## Why

- **现状痛点**：`proposal-suggestions.md` 的状态列支持人工追加决策上下文（后缀），但 gate 用精确匹配，导致任何带后缀的有效决策被误报"无决策"。本次会话 1 个 `延迟 (2026-08-28...)` 就触发，需人工 Python 绕过。
- **修复价值**：让 design-done gate 对真实状态鲁棒（前缀匹配），消除这类误报。低成本（bash case/参数扩展 3 行）+ 高价值（所有带后缀决策不再卡 gate）。
- **Why now**: 2026-08-31 session 首次真实触发；`bypass-audit-mechanism`（延迟带后缀）持续存在于 suggestions 中，未来每次 design session 都会触发。P0 而非 P1 因为它阻塞 design 阶段的正常退出（design-done 是 plan 的前置），且触发概率随带后缀提案积累而线性上升。

## What Changes

- `skills/guide-design/SKILL.md`: Phase 4 `check_design_done_gate()` 前缀匹配修复（~5 行 bash）
- `skills/guide-design/scripts/design_done_check.sh`: 新 helper（提取内联逻辑，推荐方案）
- `tests/unit/test_design_done_gate.sh`: 新单元测试（5 cases）
- `tests/integration/test_design_done_gate.bats`: 新集成测试（2 cases）
- `docs/change-quality-guide.md`: 新增"proposal 状态后缀"说明段

## Capabilities

- MUST: design-done gate 接受 `已批准*` / `已拒绝*` / `延迟*` 前缀（含后缀）
- MUST NOT: 接受 `待审查` / 空 / 未知状态（保持 pending 语义）
- MUST NOT: 改变 design-done 通过条件（所有提案有决策）

## Impact

- MUST: gate 通过条件不变（所有提案有决策，只是匹配更宽容）
- MUST: 与 `proposal-suggestions.md` 状态机（`已批准`/`已拒绝`/`延迟`/`待审查`）向后兼容
- SHOULD: 与 `bypass-audit-mechanism`（延迟）无交互：该提案状态已定，gate 只判断是否"有决策"
- MUST NOT: 改变 `design_done_gate.py` 的 Hub gates 行为（独立实现，不受本修复影响）

## Acceptance

- [ ] `tests/unit/test_design_done_gate.sh` 5 个 test PASS（含 `延迟 (suffix)` 回归）
- [ ] `tests/integration/test_design_done_gate.bats` 2 个 test PASS
- [ ] `proposal-suggestions.md` 含 `延迟 (2026-08-28...)` 时 gate 通过（无需 Python 绕过）
- [ ] 混合状态（已批准 + 延迟带后缀 + 待审查）时仅列待审查为 pending
- [ ] SKILL.md 内联逻辑或 helper 已更新为前缀匹配
- [ ] 文档同步更新（状态后缀说明）