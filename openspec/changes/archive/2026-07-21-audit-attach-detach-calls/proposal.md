# audit-attach-detach-calls

**Priority**: P0
**Phase**: v2.1
**Status**: filled

## Why

## 架构依据
- 不清楚 attach_change/detach_change 是否被 guide 技能实际调用
- ADR-0017 + v2-multi-session-guide §"自动管理" 规定 ship entry 应 attach,
  archive 应 detach, 但实际调用链未经验证

## 范围
- **In Scope**:
  - 查找所有调用 attach_change / detach_change 的位置
  - 确认 guide-arch/guide-plan/guide-ship 的 hook 调用链
  - 依据 ADR-0017 契约列出缺失的 hook
  - 输出 audit report 到 .rddf/state/attach-detach-audit.md
- **Out Scope**:
  - 不修改代码（仅 audit, 修复留待后续 change）

## 验收标准
- audit report 列出所有调用点（精确 文件:行号）
- audit report 区分 production / test / definition / doc-reference
- audit report 引用 ADR-0017 / v2-multi-session-guide 作为期望来源
- audit report 列出缺失的 hook + 影响评估
- 无源文件被修改（仅本 change artifacts + 报告）

## What Changes

- Add: `openspec/changes/audit-attach-detach-calls/design.md` (审计方法论)
- Add: `openspec/changes/audit-attach-detach-calls/tasks.md` (5 任务分解)
- Add: `.rddf/state/attach-detach-audit.md` (审计报告, gitignored 但保留副本)
- No source code modifications

## Impact

- Affected specs: none (audit-only)
- Affected code: none (read-only audit)
- Downstream: 后续修复 change 将基于本报告的发现
