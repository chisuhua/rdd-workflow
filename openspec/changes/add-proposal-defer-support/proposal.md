# Add proposal defer support — persist defer decision across Phase 5.5 sessions

**优先级**: P1
**阶段**: default
**分类**: general
**类型**: feature

## 概要

guide-arch Phase 5.5 的 `d`（延迟）选项交互时标记了 `proposal-suggestions.md` 中的状态，但延迟的提案每次进入 Phase 5.5 都会重新出现——因为 `arch_proposal_review.sh` 的提案列表构建逻辑从 `improvements/` 目录全局扫描，不读取 `proposal-suggestions.md` 中的延迟状态。

同时，`improvements/<name>.md` 元数据中缺少 `**状态**` 字段，无法在文件级别持久化延迟决策和原因。

## 背景

- guide-arch Phase 5.5 UI 中 `d`（延迟）选项已在 `arch_proposal_review.sh` 中实现（L318-L325），会在 `proposal-suggestions.md` 标记 `⏳ 已延迟 (日期)`
- 但 Step 2 构建待审查列表时（L130-L133），只检查 `proposal-suggestions.md` 中的状态——如果提案只存在于 `improvements/` 中（未在 suggestions.md 注册），则延迟状态不会被检查
- 实际案例：`split-cpptlm-core-minimal` 经 Oracle 评估后结论为"维持现状，推迟到触发条件"。但 guide-arch 无法自动跳过，每次 Phase 5.5 都会提示审查
- 根本原因：`list_improvements()` 和 `arch_proposal_review.sh` 的候选列表构建逻辑不读取持久化延迟状态

## 范围

### In Scope

- 在 `improvements/<name>.md` 元数据中增加可选 `**状态**: 待讨论 | 已推迟 | 已完成` 行（位于 `**类型**` 行之后）
- 增加可选 `**推迟原因**: ...` 行（位于 `**状态**` 行之后）
- 更新 `list_improvements()` 在 `state.sh` 中输出状态字段（`name|priority|source|status`）
- 更新 `arch_proposal_review.sh` 的提案列表构建逻辑，读取 `improvements/` 文件中的 `**状态**` 字段
- guide-arch Phase 5.5 默认跳过已推迟提案，显示 `⏸️ N 个已推迟（按 a 查看全部）`
- 提供 `a`（show all）选项展示包括已推迟在内的全部提案
- 推迟提案在列表中显示 `⏸️` 前缀

### Out Scope

- 不修改 proposal-approved.md 格式（推迟不等于批准）
- 不做自动归档（推迟是人工决策）
- 不修改 guide-plan / guide-ship 的消费逻辑（它们只读 proposal-approved.md）
- 不修改 `proposal-suggestions.md` 格式（向后兼容，suggestions 中的状态标记只作为辅助）

## 关键场景

- GIVEN `improvements/split-cpptlm-core-minimal.md` 含 `**状态**: 已推迟`, WHEN guide-arch Phase 5.5 运行, THEN 默认不展示该提案，显示 `⏸️ 1 个已推迟（按 a 查看全部）`
- GIVEN 用户按 `a` 查看全部, WHEN 展示推迟提案, THEN 显示 `[P2] ⏸️ split-cpptlm-core-minimal`，支持重新审查
- GIVEN 新提案 `improvements/add-foo.md` 无 `**状态**` 字段, WHEN Phase 5.5 运行, THEN 正常展示（向后兼容）

## 验收标准

| # | 标准 | 验证方式 |
|---|------|----------|
| 1 | `improvements/<name>.md` 支持可选 `**状态**: 待讨论 | 已推迟 | 已完成` 元数据 | bats：创建含状态文件，断言 grep 可读 |
| 2 | `list_improvements()` 输出追加状态字段（`name|priority|source|status`） | bats：含状态文件输出 4 段，无状态文件输出 4 段尾部为空 |
| 3 | guide-arch Phase 5.5 默认隐藏推迟提案，显示 `⏸️ N 个已推迟` | bats：1 个推迟 + 1 个待讨论 → 只显示待讨论 |
| 4 | 按 `a` 展示全部时推迟提案以 `⏸️` 前缀标识 | bats：全部展示时推迟行含 ⏸️ |
| 5 | 无状态字段的旧提案行为不变（视为待讨论） | bats：无状态文件正常展示 |