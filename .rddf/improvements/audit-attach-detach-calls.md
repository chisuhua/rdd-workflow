# audit-attach-detach-calls

**优先级**: P0 | **来源**: .omo/plans/rddf-session-improvement-plan.md — W0-2
**阶段**: v2.1 | **分类**: core
**类型**: feature

## 架构依据
- 不清楚 attach_change/detach_change 是否被 guide 技能实际调用

## 范围
- **In Scope**:
  - 查找所有调用 attach_change / detach_change 的位置
  - 确认 guide-arch/guide-plan/guide-ship 的 hook 调用链
  - 输出 audit report
- **Out Scope**:
  - 不修改代码（仅 audit）

## 关键场景
（无）

## 技术约束
（无）

## 验收标准
- audit report 列出所有调用点 + 缺失的 hook
