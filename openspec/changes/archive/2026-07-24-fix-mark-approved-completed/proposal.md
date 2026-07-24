# Proposal: fix-mark-approved-completed

## Why

`skills/_lib/state.sh` 的 `mark_approved_completed` 函数在移动条目到 `## 已实施` 表格时，Python 逻辑产生了重复的 `| 提案 | 优先级 | 实施时间 |` 表头行，需手动 `edit` 工具修复，影响审批流程的自动化程度。函数缺少幂等性检查：如果条目已在 completed 表格中，应直接返回成功。

来源: 会话复盘 2026-07-23

## What Changes

- 修复 `mark_approved_completed` 函数中 `content.replace` 逻辑，确保不产生重复表头
- 增加幂等性检查：检测目标条目是否已在 `## 已实施` 表格中，若是则直接返回
- 增加单元测试覆盖
- 不修改 `append_approved` 函数
- 不修改 proposal-approved.md 格式

## Capabilities

### New Capabilities: fix-mark-approved-completed

修复 `mark_approved_completed` 函数的重复表头 bug 并增加幂等性检查。使用 Python 标准库 `re` 模块确保正确插入行到 `## 已实施` 表头下方而非重复表头。保持与 `append_approved` / `list_approved` 的调用约定一致。

## Impact

**受影响文件:**
- `skills/_lib/state.sh` — `mark_approved_completed` 函数修复

**不受影响:**
- `append_approved` 函数
- proposal-approved.md 格式
