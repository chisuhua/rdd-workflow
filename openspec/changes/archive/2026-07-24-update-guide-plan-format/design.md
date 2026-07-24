# Design: update-guide-plan-format

## Context

proposal-suggestions.md 已从 JSON 切换为 Markdown 表格索引，proposal-approved.md 为 plan 阶段输入。`guide-plan/SKILL.md` 的 Phase 1/2 代码块仍引用 `json.load(proposal-suggestions.md)`，文档与实际代码行为不一致。

## Goals / Non-Goals

### Goals

- Phase 1 scan 委托改为读取 `proposal-approved.md` 表格
- Phase 2 propose 代码块从 JSON 解析改为 Markdown 表格解析（`grep`/`sed`）
- Phase 2.5 fill 的 suggestion 读取改为 `improvements/` 文件扫描
- 更新"职责边界"描述：proposal-suggestions.md 不再属于 plan 端
- 代码块与实际 `scan-state.sh` / `state.sh` 实现一致

### Non-Goals

- 不修改 guide-plan 的实际执行逻辑（消费者代码已在之前适配）
- 不修改 guide-arch 或 guide-ship

## Decisions

保持文档结构不变（bash 代码块 + 注释），仅替换代码块内容：

- Phase 1: `json.load()` -> `grep '^|' proposal-approved.md | tail -n +3`（跳过表头）
- Phase 2: JSON 字段访问 -> `sed`/`awk` 提取 Markdown 表格列
- Phase 2.5: `improvements/*.md` 文件扫描替代 JSON 条目查找

## Implementation

**关键修改文件:**

- `skills/guide-plan/SKILL.md`
  - Phase 1 scan 代码块更新
  - Phase 2 propose 代码块更新
  - Phase 2.5 fill 代码块更新
  - "职责边界"章节移除 proposal-suggestions.md 归属说明
