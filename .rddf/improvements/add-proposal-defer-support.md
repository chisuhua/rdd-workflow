# add-proposal-defer-support

**优先级**: P1 | **来源**: PTX-EMU 2026-07-28 实战 — split-cpptlm-core-minimal 已评估推迟但 guide-arch 无法跳过
**阶段**: default | **分类**: general
**类型**: feature

## 架构依据

- guide-arch Phase 5.5 UI 描述中存在 `d`（延迟）选项，但**未在实现中持久化任何状态**（skills/guide-arch/SKILL.md:704-706）
- 当前 Phase 5.5 审查循环：遍历 `improvements/` 下所有不在 `proposal-approved.md` 中的 .md 文件，逐一展示（skills/guide-arch/SKILL.md:616-640）
- 无标记机制意味着：被延迟的提案每次进入 Phase 5.5 都会重新出现，用户无法区分「新提案」和「已评估推迟」
- 实际案例：`split-cpptlm-core-minimal` 经 Oracle 评估后结论为"维持现状，推迟到触发条件"。但 guide-arch 无法自动跳过，每次 Phase 5.5 都会提示审查

## 范围

- **In Scope**:
  - 在 `improvements/<name>.md` 元数据中增加可选 `**状态**: 推迟 | **推迟原因**: ...` 行（位于 `**类型**` 行之后）
  - guide-arch Phase 5.5 读取状态字段，已推迟的提案默认折叠/跳过，提供 `a`（显示全部）选项展示
  - `proposal-suggestions.md` 可选增加 `状态` 列（向后兼容，缺省视为"待讨论"）
  - `list_improvements()` 在 `state.sh` 中增加状态字段输出
  - 推迟提案在 Phase 5.5 列表中以 `⏸️` 前缀标识
- **Out Scope**:
  - 不修改 proposal-approved.md 格式（推迟不等于批准）
  - 不做自动归档（推迟是人工决策）
  - 不修改 guide-plan / guide-ship 的消费逻辑（它们只读 proposal-approved.md）

## 关键场景

- GIVEN `improvements/split-cpptlm-core-minimal.md` 含 `**状态**: 推迟`, WHEN guide-arch Phase 5.5 运行, THEN 默认不展示该提案（`⏸️ 1 个已推迟`），用户可按 `a` 查看全部
- GIVEN 用户选择查看全部, WHEN 展示推迟提案, THEN 显示 `[P2] ⏸️ split-cpptlm-core-minimal — ADR-0022 (推迟原因: 维持现状，等待触发条件)`，支持重新审查
- GIVEN 新提案 `improvements/add-foo.md` 无状态字段, WHEN Phase 5.5 运行, THEN 正常展示（向后兼容）

## 技术约束

- MUST 向后兼容：无 `**状态**` 字段的现有提案行为不变
- MUST 不修改 `list_improvements()` 现有输出格式（仅追加状态字段，以 `|` 分隔：`name|priority|source|status`）
- MUST `list_improvements()` 的调用方（Phase 5.5）处理 `status` 为空的旧提案
- SHOULD `proposal-suggestions.md` 表头可选增加 `状态` 列（不强制，缺省 `待讨论`）

## 验收标准

- [ ] `improvements/<name>.md` 支持可选 `**状态**: 推迟 | **推迟原因**: ...` 元数据
- [ ] guide-arch Phase 5.5 默认隐藏推迟提案，显示 `⏸️ N 个已推迟（按 a 查看全部）`
- [ ] 按 `a` 展示全部时推迟提案以 `⏸️` 前缀标识
- [ ] 无状态字段的旧提案行为不变
- [ ] `list_improvements()` 输出向后兼容（调用方不依赖新字段也能工作）
