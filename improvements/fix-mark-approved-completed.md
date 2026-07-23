# fix-mark-approved-completed

**优先级**: P1 | **来源**: 会话复盘 2026-07-23 — proposal-approved.md 表头重复 bug
**阶段**: v2.1 | **分类**: core
**类型**: feature

## 架构依据

- `skills/_lib/state.sh` 的 `mark_approved_completed` 函数在移动条目到 `## 已实施` 表格时，Python 逻辑产生了重复的 `| 提案 | 优先级 | 实施时间 |` 表头行
- 需手动 `edit` 工具修复，影响审批流程的自动化程度
- 函数缺少幂等性检查：如果条目已在 completed 表格中，应直接返回成功

## 范围

- **In Scope**:
  - 修复 `mark_approved_completed` 函数中 `content.replace` 逻辑，确保不产生重复表头
  - 增加幂等性检查：检测目标条目是否已在 `## 已实施` 表格中，若是则直接返回
  - 增加单元测试覆盖
- **Out Scope**:
  - 不修改 `append_approved` 函数
  - 不修改 proposal-approved.md 格式

## 关键场景

- GIVEN approved.md 有 `## 已实施` 表头, WHEN mark_approved_completed 执行, THEN 新行插入在表头下方而非重复表头
- GIVEN 条目已在 `## 已实施` 表格, WHEN 再次调用 mark_approved_completed, THEN 幂等返回 success

## 技术约束

- MUST 使用 Python 标准库 `re` 模块，不引入新依赖
- MUST 保持与 `append_approved` / `list_approved` 的调用约定一致
- SHOULD 测试覆盖：正常路径 + 重复调用幂等 + 已实施条目跳过

## 验收标准

- `mark_approved_completed` 不产生重复表头
- 幂等调用返回 success 且不修改文件
- 3 个单元测试通过
