## Context

**背景**: 改进 change 质量计划 (`.omo/plans/improve-change-quality-index.md`) 的 Plan C 要求刷新 propose 阶段的输入源。当前 `roadmap.md` 已经包含基础的 v2.1/v3.0 框架，但需要确认全部 6 个 planned changes 都有完整映射，并运行 gap-analysis 以补充未跟踪的 ADR/TODO/test 缺口到 `proposal-suggestions.md`。

**当前状态**:
- `roadmap.md` 已包含 v2.1 Phase 1 (6 changes) + Phase 2 (1 change) + v3.0 Phase 1-3 (3 changes) 的表格。
- `proposal-suggestions.md` 当前 12 条：8 已完成 + 4 skeleton (含本 change)。
- 4 个 skeleton change (`refresh-input-sources`, `refine-adr-0015-wiring`, `add-propose-output-validation`, `add-change-quality-guide`) 均已注册到 `iteration.json` (status=planned)。
- ADR-0014 (Review 阶段债务回流) 与 ADR-0015 (openspec validate as plan-critic) 仍为 `待定` 状态；ADR-0009 (定时触发器) 为 `模板` 占位状态。

**约束**:
- MUST 保持 `roadmap.md` 向后兼容（roadmap_state.py、scan-state.sh 等下游消费者仍可解析）。
- MUST 不引入新 ADR 引用（避免触发 ADR-0018 arch_alignment warning；ADR-0015 状态更新归 Plan A 负责）。
- MUST NOT 修改测试文件、不创建 `openspec/changes/refresh-input-sources/` 之外的新目录。
- MUST NOT 修改 propose 技能本身。

## Goals / Non-Goals

**Goals (In Scope)**:
- 校验/补全 `roadmap.md` 的 v2.1 Phase 1 (5 changes + `add-manual-deps-field`) + Phase 2 (`add-manual-deps-field`) 映射，确保 4 个新 skeleton change 被引用。
- 运行 gap-analysis 扫描：
  - 源码中未解决 `TODO` / `FIXME` / `HACK` / `XXX` 注释（`skills/` + `docs/`）。
  - ADR 状态差距（`待定` / `模板` 的 ADR 是否有对应 change 推进）。
  - 测试覆盖缺口（无 dedicated unit test 的 Python 模块）。
- 将新发现的 gap 写入 `proposal-suggestions.md` (status=`pending`, source=`gap-analysis: refresh-input-sources`)。

**Non-Goals (Out Scope)**:
- 不创建新 change。
- 不修改 `propose` 技能扫描逻辑。
- 不更新 ADR-0015 状态（归 Plan A: `refine-adr-0015-wiring`）。
- 不为发现的 gap 编写实现代码（仅记录到 suggestions）。

## Decisions

### 决策 1: roadmap.md 保持现有表格格式 + 仅校验补全
- **理由**: `roadmap.md` 已被 `roadmap_state.py`、`scan-state.sh`、`guide-arch/SKILL.md` 等多个消费者解析。当前表格列 `Change | Priority | Effort | Wave | Manual Deps | 描述` 已是稳定契约。仅校验条目完整性，不改格式。
- **替代方案**: 引入 YAML frontmatter / 改用 JSON -> 拒绝，会破坏向后兼容且超出 Plan C 范围。

### 决策 2: gap-analysis 使用 grep literal pattern 扫描
- **理由**: ADR-0019 §2 警告扩展 TODO/FIXME 模式到工作代码会高误报率。本 change 采用保守策略：
  - 仅扫描 `skills/_lib/` + `tests/` 下 `# TODO` / `# FIXME` / `# HACK` 注释 (Python/shell 注释前缀)。
  - 排除文档中"TODO"作为单词出现的位置（如 ADR-0014 讨论债务时引用 TODO 一词）。
  - 排除测试中的 placeholder 文本。
- **替代方案**: 扫描所有 .md 文档中的 TODO -> 拒绝，误报过多。

### 决策 3: 测试缺口检测以 dedicated unit test 缺失为准
- **理由**: `tests/unit/` 当前 59 个文件覆盖大部分 `_lib/` 模块。检测标准：模块 `foo.py` 是否有 `tests/unit/test_foo.py`。已知缺口：
  - `trigger_registry.py` (无 dedicated test)
  - `session_base.py` (无 dedicated test)
  - `loop/event_queue.py` (无 dedicated test，被 integration 覆盖)
  - `loop/loop_state.py` (无 dedicated test，被 integration 覆盖)
  - `schedulers/fs_watcher.py` / `git_hook.py` / `webhook_receiver.py` (schedulers 子目录集成度低)
- **策略**: 仅将 `trigger_registry` + `session_base` + `schedulers/` 三个写入 suggestions（loop 子目录的 2 个模块被 integration 覆盖充分，不强制 dedicated unit test，避免 over-engineering）。

### 决策 4: gap-analysis 发现的 gap 数量上限
- **理由**: proposal.md 验收标准要求"新发现的 gap 条目 ≤ 5 个"。本 change 仅记录明确可执行的 gap，避免噪音。
- **入选标准**: 每个 gap 必须有明确 scope + 可量化验收标准。

### 决策 5: 不修改 ADR-0014 / ADR-0015 / ADR-0009 状态
- **理由**: Plan A (`refine-adr-0015-wiring`) 明确负责 ADR-0015 状态更新，Plan C 删除了 ADR-0015 状态更新以避免冲突（见 `.omo/plans/improve-change-quality-index.md` "Plan C 关键修正"）。ADR-0014 / ADR-0009 状态更新不在 Plan C 范围内。

## Risks / Trade-offs

- **风险**: gap-analysis 漏报真实缺口 -> **缓解**: 保守策略优先，漏报可在后续 change 中补；误报会污染 suggestions 队列。
- **权衡**: roadmap.md 表格 vs 结构化格式 -> 选表格，保持向后兼容。
- **权衡**: 测试覆盖检测标准（dedicated unit test vs integration 覆盖）-> 选 dedicated unit test，更明确可执行。

## Verification

- `roadmap.md` 包含 v2.1 Phase 1 的 5 个基础 change + `add-manual-deps-field` 共 6 条，Phase 2 的 `add-manual-deps-field` 1 条。
- `proposal-suggestions.md` 总条目数 ≤ 17 (12 已有 + 5 新发现上限)。
- `iteration.json` 中 `refresh-input-sources` 的 status 从 `planned` 改为 `proposed`。
- `python3 -m pytest tests/unit/ -q --tb=short` 全部通过（663 tests）。
