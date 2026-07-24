# Proposal: update-guide-plan-format

## Why

proposal-suggestions.md 已从 JSON 切换为 Markdown 表格索引，proposal-approved.md 为 plan 阶段输入。但 `guide-plan/SKILL.md` 的 Phase 1 scan 和 Phase 2 propose 代码块仍引用 `json.load(proposal-suggestions.md)`，造成文档与实际代码行为不一致，后续开发者/AI 会被误导。

来源: 会话复盘 2026-07-23

## What Changes

- 更新 `guide-plan/SKILL.md` Phase 1: scan 委托改为读取 `proposal-approved.md` 表格
- 更新 Phase 2: propose 的候选展示代码块，从 JSON 解析改为 Markdown 表格解析
- 更新 Phase 2.5: fill 的 suggestion 读取改为 `improvements/` 文件扫描
- 更新文档中的"职责边界"描述：proposal-suggestions.md 不再属于 plan 端
- 不修改 guide-plan 的实际执行逻辑（消费者代码已在之前适配）
- 不修改 guide-arch 或 guide-ship

## Capabilities

### New Capabilities: update-guide-plan-format

更新 `guide-plan/SKILL.md` 文档使其与实际代码行为一致：Phase 1 scan 读取 `proposal-approved.md` 表格，Phase 2 propose 使用 `grep`/`sed` 解析 Markdown 表格，Phase 2.5 fill 扫描 `improvements/` 目录。更新"职责边界"描述移除 proposal-suggestions.md 的 plan 端归属。

## Impact

**受影响文件:**
- `skills/guide-plan/SKILL.md` — Phase 1/2/2.5 代码块 + 职责边界描述

**不受影响:**
- guide-plan 实际执行逻辑（消费者代码已适配）
- guide-arch / guide-ship
