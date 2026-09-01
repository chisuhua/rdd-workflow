# fix-plan-intake-stale-pre-created-changes

**优先级**: P1 | **来源**: 2026-09-01 guide-plan session — `plan_intake.sh` 误导性计数 + `.design-handoff.json` `changes_pre_created` 永不过期，导致 agent 把已归档 change 当待创建
**阶段**: v2.2 | **分类**: core-impl / workflow-correctness
**类型**: bugfix / 状态机防腐

> **症状**：guide-plan Phase 1 环境检查输出
> `⚠️  proposal-approved.md 中有 225 个已批准提案但无活跃 change（可能需运行 propose）`
> —— 把 223 个已归档的提案（`## 已实施` 区）误算进 pending，导致 agent 试图创建 19 个早已归档到 `openspec/changes/archive/` 的 changes。
>
> **根因**：双重问题：
> 1. `PENDING_PROPOSALS=$(grep -c '| \[' proposal-approved.md)` 统计整个文件，**包括 `## 已实施` 分区**
> 2. `.design-handoff.json` 的 `changes_pre_created` 是 design 阶段写死的快照，**永不过期**；`check_design_handoff()` 读入时不做归档/创建检查

## 架构依据

**症状 (2026-09-01 session)**:

- 调用 `guide-plan`，plan_intake 输出：
  - `📋 当前活跃 changes: 0`
  - `⚠️  proposal-approved.md 中有 225 个已批准提案但无活跃 change（可能需运行 propose）`
  - `✅ design-done handoff 已验证 (v2 schema, 19 个预建 changes)`
- 用户（AI agent）看到 19 个预建 changes + 0 活跃 change，判定"需要 propose 创建"，对 19 个名字批量调用 `propose --create`
- 实际验证后发现：**这 19 个全部位于 `proposal-approved.md` 的 `## 已实施` 分区**，且**全部已归档**到 `openspec/changes/archive/2026-{08,09}-*` 下
- 真正待创建的提案数：**0**

**根因分析**:

`skills/guide-plan/scripts/plan_intake.sh` 第 200-204 行：

```bash
PENDING_PROPOSALS=$(grep -c '| \[' "$PROJECT_ROOT/proposal-approved.md" 2>/dev/null || echo 0)
if [ "$PENDING_PROPOSALS" -gt 0 ] && [ "$ACTIVE_CHANGES" -eq 0 ]; then
    echo "⚠️  proposal-approved.md 中有 $PENDING_PROPOSALS 个已批准提案但无活跃 change（可能需运行 propose）"
fi
```

- `grep -c '| \['` 统计**整个 `proposal-approved.md`** 中 `| [` 开头的表格行
- 文件包含 `## 已批准提案`（仅已批准待实施的）和 `## 已实施`（已归档的）两个分区
- 本 session 文件中已实施区 223 行 + 已批准区 2 行 ≈ 225，**全部被算成 pending**

`skills/guide-plan/scripts/plan_intake.sh` 第 134-146 行（`check_design_handoff`）：

```bash
mapfile -t CHANGES_PRE_CREATED < <(jq -r '.changes_pre_created // [] | .[]' "$handoff_path" 2>/dev/null)
```

- `changes_pre_created` 是 design 阶段落盘的**永久快照**，写完后从不更新
- design 阶段批准 19 个提案 → 写快照 → 后续 plan/ship 把这 19 个 change 创建并归档
- 但 `.design-handoff.json` **不被 archive 阶段触达**（它是 design 阶段的产物，gitignored 状态文件）
- 下次 plan_intake 时，`CHANGES_PRE_CREATED` 仍包含已归档的 19 个名字
- `check_design_handoff` 的"19 个预建 changes"提示就成了误导

**影响范围**:

- **AI agent 决策误导**：看到 19 个预建 changes 名字 → 盲目创建，浪费 token + 制造 stderr 噪声
- **人类用户体验差**：plan_intake 输出让人以为"有大量待办"，实际全是已完成项
- **无数据丢失**（propose 有幂等保护 `create_skeleton_change` 会跳过已存在的），但用户体验**严重退化**
- **下游显示层误导**：guide-plan SKILL.md Phase 2 的"已批准提案列表"逻辑会误标 19 个名字为"待创建"

## 范围

### In Scope

**A. `plan_intake.sh::run_plan_intake` 修正 `PENDING_PROPOSALS` 计数**:

- 只统计 `## 已实施`**之前**的章节（即"已批准提案"区）
- 在已批准区中**排除** `openspec/changes/<name>` 存在的（已创建 change）
- 在已批准区中**排除** `openspec/changes/archive/*-<name>` 存在的（已归档 change）
- 输出修正：
  - 之前：`225 个已批准提案但无活跃 change`
  - 之后：`0 个真正待创建提案（已排除 223 个已归档 + 2 个已批准但暂无 change）` 或简化为无警告

**B. `plan_intake.sh::check_design_handoff` 过滤过期 `changes_pre_created`**:

- 读入 `changes_pre_created` 数组后，对每个名字做存在性检查：
  - 已创建（`openspec/changes/<name>/` 存在）→ 从展示中移除（已隐含"活跃"）
  - 已归档（`openspec/changes/archive/*-<name>` 存在）→ 从展示中移除，**不**报错
- 报告区分显示：
  - `🆕 待处理预建: N`
  - `✅ 已归档预建: M`（信息性，不触发警告）
- 行为契约：`CHANGES_PRE_CREATED` 内部数组保留所有名字（不删，幂等检查下游），但展示层分两类

**C. 复用 `is_design_pre_created` helper**:

- 现有的 `is_design_pre_created()` 保持不变（仅判断名字是否在数组中）
- 新增 `is_design_pre_created_pending()`：返回 0 当且仅当「名字在数组中**且**未创建**且**未归档」
- 在 plan_intake 的展示和警告逻辑中使用新 helper

**D. 导出 Python helper 供下游消费**:

- `plan_intake.sh` 内置 Python 一次性计算：`pending_changes` / `archived_changes` / `active_changes`
- 导出为 `CHANGES_PENDING_COUNT` / `CHANGES_ARCHIVED_COUNT` 环境变量（与 `CHANGES_PRE_CREATED` 一致）
- 让 guide-plan Phase 2 / 2.5 的展示层能直接消费

### Out Scope

- **不修改** `.design-handoff.json` 的 schema（v2 仍然记录"当时预建了哪些"，是历史审计所需）
- **不删除** 已归档 change 在 `changes_pre_created` 中的记录（保留"设计阶段曾经预建过"的审计线索）
- **不修改** proposal-approved.md 的 `## 已实施` 区结构（这是 `archive_change()` 的契约）
- **不修改** `propose` 的幂等保护（已有，按设计工作）
- **不引入** 自动清理/截断 `.design-handoff.json` 的机制（archive 阶段不触达 design handoff 是设计选择，保留这一边界）

## 关键场景

### 场景 1: 全部预建 changes 已归档（本次实际场景）

- **GIVEN** `.design-handoff.json` v2 schema，`changes_pre_created: [A, B, C]` 3 个名字
- **AND** `openspec/changes/archive/*-A` / `*-B` / `*-C` 全部存在
- **AND** `proposal-approved.md` 包含 `## 已实施` 区有 A/B/C 3 行
- **WHEN** 调用 `run_plan_intake`
- **THEN**
  - 不再输出"X 个已批准提案但无活跃 change"误导警告
  - 输出 `✅ design-done handoff 已验证 (v2 schema, 3 个预建 changes: 3 已归档, 0 待处理)`
  - `CHANGES_PRE_CREATED` 数组内部仍为 `[A, B, C]`（保留审计）

### 场景 2: 部分预建 changes 待处理

- **GIVEN** `changes_pre_created: [X, Y, Z]` 3 个名字
- **AND** `X` 已创建（`openspec/changes/X/` 存在），Y/Z 未存在
- **WHEN** 调用 `run_plan_intake`
- **THEN**
  - 输出 `✅ design-done handoff 已验证 (v2 schema, 3 个预建 changes: 2 待处理, 1 已创建)`
  - `CHANGES_PRE_CREATED` 仍为 `[X, Y, Z]`，但展示给用户的"待处理"列表只含 Y/Z

### 场景 3: 全部预建 changes 待处理

- **GIVEN** `changes_pre_created: [A, B]` 2 个名字
- **AND** A 和 B 都不存在于 `openspec/changes/` 或 `archive/`
- **WHEN** 调用 `run_plan_intake`
- **THEN**
  - 输出 `✅ design-done handoff 已验证 (v2 schema, 2 个预建 changes: 2 待处理)`
  - 提示 `guide-plan Phase 2.5 fill 会消费这些 change`

### 场景 4: 无 design pre-created（v1 schema 兼容）

- **GIVEN** `.design-handoff.json` v1 schema（无 `changes_pre_created` 字段）
- **OR** v2 schema 但 `changes_pre_created: []`
- **WHEN** 调用 `run_plan_intake`
- **THEN**
  - 行为与现状完全一致：`✅ design-done handoff 已验证 (v1 schema)` 或 `✅ ... (v2 schema, 0 个预建 changes)`
  - 不影响 `is_design_pre_created` 等既有 helper

### 场景 5: `proposal-approved.md` 计数修正

- **GIVEN** 文件含 223 行 `## 已实施` + 2 行 `## 已批准提案`
- **AND** 2 个已批准提案都不在 `openspec/changes/` 中（也未归档）
- **WHEN** `PENDING_PROPOSALS` 重新计算
- **THEN** 返回 `2`（仅已批准且未创建/未归档的），不再返回 225
- **AND** 不再触发"X 个已批准提案但无活跃 change"误导警告（改为：`📋 待创建 proposal 数: 2`）

### 场景 6: SKIP_DESIGN_HANDOFF=yes 兼容性

- **GIVEN** `SKIP_DESIGN_HANDOFF=yes`
- **WHEN** 调用 `run_plan_intake`
- **THEN** 跳过 `check_design_handoff` 全部逻辑（包括新加的归档过滤），保持向后兼容
- `CHANGES_PRE_CREATED` 为空数组（新 helper 也都返回 false/0）

## 技术约束

- **MUST NOT**: 修改 `.design-handoff.json` 的 schema v2（向后兼容契约）
- **MUST NOT**: 引入新依赖（仅 bash + python3 + jq 即可）
- **MUST NOT**: 在 archive 阶段触达 `.design-handoff.json`（保留设计/执行阶段边界）
- **MUST**: 默认行为向后兼容（v1 handoff / `SKIP_DESIGN_HANDOFF=yes` / 空 `changes_pre_created` 三种情况保持原行为）
- **MUST**: 修正后的 `PENDING_PROPOSALS` 必须是「真正待创建」的计数（排除已创建/已归档）
- **SHOULD**: 复用既有 `is_design_pre_created` helper，新增 `is_design_pre_created_pending` 增量
- **SHOULD**: 把归档检查的 Python 逻辑抽到 `_lib/state.sh` 或独立 helper 供多处复用
- **MUST**: 新增的测试覆盖全部 6 个关键场景 + SKIP_DESIGN_HANDOFF 兼容性

## 验收标准

### 单元与集成测试

- [ ] `tests/integration/test_plan_intake_archived_filtering.bats` 新增 4 个测试：
  - [ ] `plan_intake-archived-filter: 全部预建已归档 → 不输出 pending 警告`
  - [ ] `plan_intake-archived-filter: 部分预建待处理 → 正确分类展示`
  - [ ] `plan_intake-archived-filter: PENDING_PROPOSALS 排除已实施区`
  - [ ] `plan_intake-archived-filter: SKIP_DESIGN_HANDOFF=yes 跳过新逻辑`
- [ ] `tests/integration/test_plan_intake_design_pre_created.bats` 扩展 2 个测试：
  - [ ] `is_design_pre_created_pending: 名字在数组 + 已归档 → 返回 1`
  - [ ] `is_design_pre_created_pending: 名字在数组 + 未归档 → 返回 0`
- [ ] `tests/unit/test_plan_intake_archived_filter.py`（如新增 Python helper）覆盖 6 个场景

### 端到端验证

- [ ] `./test.sh --quick` 通过（包含现有 plan_intake 测试 + 新增测试）
- [ ] `./test.sh --unit` 通过（Python 单测全绿）
- [ ] `./test.sh --bats` 通过（bats 全量无新增失败）
- [ ] 在本仓库实际跑 `run_plan_intake`：不再输出"225 个已批准提案"误导；输出"0 个待创建"

### 兼容性验证

- [ ] v1 schema design-handoff（无 `changes_pre_created`）行为不变
- [ ] `SKIP_DESIGN_HANDOFF=yes` 行为不变
- [ ] 空 `changes_pre_created: []` 行为不变
- [ ] `is_design_pre_created` 既有 8 个测试全绿（语义不变）

### 文档化

- [ ] `skills/guide-plan/SKILL.md` Phase 1 段补充：plan_intake 现在排除已归档
- [ ] `docs/adr/` 新增 ADR-0036 描述「design-handoff 持久化 + 运行时过滤」分离原则（如需要）
- [ ] AGENTS.md "关键目录" 段补充 `.design-handoff.json` v2 + 归档过滤说明

### 副作用监测

- [ ] ship 后：plan_intake 第一屏不再让 AI agent 盲目创建已归档 change
- [ ] 不引入新依赖
- [ ] 不修改 `.design-handoff.json` schema
- [ ] 不破坏 v1 schema 兼容性

## Why

- **现状痛点**：plan_intake 误导输出 + design handoff 永不过期导致 AI agent 决策错误。本 session 实际触发：被诱导对 19 个已归档 change 调用 `propose --create`，浪费 ~5 分钟 bash 循环 + 制造 stderr 噪声。
- **修复价值**：让 plan_intake 第一屏**真实反映**"哪些 change 待处理"，不再误导用户/agent。低成本（仅 plan_intake.sh 内的 grep 修正 + Python 一次性计算 + 展示层分类）。
- **Why now**: 2026-09-01 session 实际暴露。P1 因为它直接影响 AI agent 决策正确性，但**不阻塞** rdd-workflow 核心流（propose 幂等保护兜底）。P1 而非 P0 是因为 bug 触发需要特定前置条件（design 已批准 + archive 已完成 + agent 不做归档检查），不是每次必现。

## What Changes

- `skills/guide-plan/scripts/plan_intake.sh`:
  - `run_plan_intake` 的 `PENDING_PROPOSALS` 计算：Python 一次性扫文件 + 排除已实施区 + 排除已创建/已归档
  - `check_design_handoff` 读入 `CHANGES_PRE_CREATED` 后，新增分类计算（待处理/已创建/已归档）
  - 导出新 helper：`is_design_pre_created_pending`、env vars `CHANGES_PENDING_COUNT` / `CHANGES_ARCHIVED_COUNT`
- `tests/integration/test_plan_intake_archived_filtering.bats`: 新增 4 个 bats 测试
- `tests/integration/test_plan_intake_design_pre_created.bats`: 扩展 2 个测试覆盖新 helper
- `skills/guide-plan/SKILL.md`: Phase 1 段补充归档过滤说明
- `docs/adr/ADR-0036-design-handoff-runtime-filter.md`: 新增 ADR（设计选择）

## Capabilities

- MUST: `plan_intake` 真实反映「待创建」提案数（排除已归档/已创建）
- MUST: `check_design_handoff` 分类展示预建 changes（待处理 / 已创建 / 已归档）
- MUST: 既有 helper `is_design_pre_created` 语义不变
- MUST NOT: 修改 `.design-handoff.json` v2 schema
- MUST NOT: 在 archive 阶段触达 design handoff
- MUST NOT: 删除已归档 change 在 `changes_pre_created` 中的记录（审计价值）

## Impact

- MUST: plan_intake 第一屏输出不再误导 AI agent
- MUST: v1 schema + SKIP_DESIGN_HANDOFF=yes + 空数组 三种兼容路径保持原行为
- SHOULD: AI agent 决策正确性提升（不再盲目创建已归档 change）
- MUST NOT: 引入新依赖
- MUST NOT: 改变 proposal-approved.md 文件结构

## Acceptance

- [ ] `./test.sh --quick` 全绿（含新增测试）
- [ ] `./test.sh --unit` Python 单测全绿
- [ ] `./test.sh --bats` bats 全量无新增失败
- [ ] 在本仓库跑 `run_plan_intake` 验证：不再输出 "X 个已批准提案但无活跃 change" 误导
- [ ] 输出新格式：`📋 待创建 proposal: N` + `✅ design-done handoff 已验证 (v2 schema, K 个预建 changes: P 待处理, M 已创建/已归档)`
- [ ] `is_design_pre_created` 既有 8 个测试全绿
- [ ] 4 个新增 bats 测试 + 2 个扩展测试 PASS
- [ ] ADR-0036 落盘（设计选择记录）
