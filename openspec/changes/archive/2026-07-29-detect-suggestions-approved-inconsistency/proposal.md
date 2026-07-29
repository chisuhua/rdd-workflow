# Detect suggestions-approved inconsistency — 审计追溯保护

**优先级**: P3  
**阶段**: v2.1  
**分类**: planning  

## 概要

`proposal-suggestions.md` 中的条目可能被标记为 `status: "已完成"`（在时间列），但 `proposal-approved.md` 中不存在对应的批准记录。这导致审计者无法区分"已完成"的 suggestion 是通过正规 approve 流程完成还是绕过流程直接完成，丧失了 workflow 的治理能力。

## 背景

- 会话复盘 2026-07-26 发现：`proposal-suggestions.md` 有 10 项全部标记为 `status: "已完成"` 或 `"已评估，不需要"` 或 `"暂缓"`，但 `proposal-approved.md` 从未被创建
- 根因：项目历史中 changes 被直接创建并归档，绕过了 proposal → approved → change 的标准流程
- workflow 无检测此不一致的机制

## 范围

### In Scope

- 在 `guide_entry.sh` 入口扫描中新增一致性检测：当 `proposal-suggestions.md` 有 "completed" 状态条目但 `proposal-approved.md` 不存在或对应条目缺失时，输出警告
- 检测函数放在 `_lib/state.sh` 中，作为 `check_*` 系列函数之一
- 警告格式：`⚠️  N 个 suggestions 标记已完成但无 approved 记录 — 建议审计或自动恢复`

### Out Scope

- 不修改 `proposal-suggestions.md` 或 `proposal-approved.md` 的内容
- 不自动创建 approved 条目（留给用户手动处理）
- 不影响正常的 approve → propose 流程

## 验收标准

- `guide_entry` 检测到不一致时输出 `⚠️` 警告
- 正常项目（suggestions 和 approved 一致）无 false positive
- 新增 bats 测试覆盖一致性检测