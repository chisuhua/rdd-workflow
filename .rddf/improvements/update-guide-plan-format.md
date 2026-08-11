# update-guide-plan-format

**优先级**: P1 | **来源**: 会话复盘 2026-07-23 — guide-plan SKILL.md 仍引用旧 JSON 格式
**阶段**: v2.1 | **分类**: docs
**类型**: feature

## 架构依据

- proposal-suggestions.md 已从 JSON 切换为 Markdown 表格索引，proposal-approved.md 为 plan 阶段输入
- `guide-plan/SKILL.md` 的 Phase 1 scan 和 Phase 2 propose 代码块仍引用 `json.load(proposal-suggestions.md)`
- 造成文档与实际代码行为不一致，后续开发者/AI 会被误导

## 范围

- **In Scope**:
  - 更新 `guide-plan/SKILL.md` Phase 1: scan 委托改为读取 `proposal-approved.md` 表格
  - 更新 Phase 2: propose 的候选展示代码块，从 JSON 解析改为 Markdown 表格解析
  - 更新 Phase 2.5: fill 的 suggestion 读取改为 `improvements/` 文件扫描
  - 更新文档中的"职责边界"描述：proposal-suggestions.md 不再属于 plan 端
- **Out Scope**:
  - 不修改 guide-plan 的实际执行逻辑（消费者代码已在之前适配）
  - 不修改 guide-arch 或 guide-ship

## 关键场景

- GIVEN 开发者阅读 guide-plan SKILL.md, WHEN 看到 Phase 2 代码示例, THEN 示例使用 Markdown 表格解析而非 `json.load`
- GIVEN AI 被分配 guide-plan 任务, WHEN 按照文档执行, THEN 代码块可直接运行

## 技术约束

- MUST 保持文档结构与现有格式一致（bash 代码块 + 注释）
- MUST 更新的代码块与实际 `scan-state.sh` / `state.sh` 实现一致
- SHOULD 更新"职责边界"中关于 proposal-suggestions.md 的说明

## 验收标准

- guide-plan SKILL.md 中无 `json.load(proposal-suggestions.md)` 引用
- Phase 2 代码块示例使用 `grep`/`sed` 解析 Markdown 表格
- 文档中的消费者列表与实际一致
