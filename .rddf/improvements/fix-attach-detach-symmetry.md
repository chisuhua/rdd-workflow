# fix-attach-detach-symmetry

**优先级**: P1 | **来源**: .omo/plans/rddf-session-improvement-plan.md — W1-3
**阶段**: v2.1 | **分类**: core
**类型**: feature

## 架构依据
- attach_change/detach_change 调用点不对称（基于 W0-2 audit）

## 范围
- **In Scope**:
  - rddf_session_hooks.sh 新增 rddf_session_hook_attach
  - guide-plan Phase 2 完成后调用 attach
  - guide-ship Phase 1 plan 生成后调用 attach
- **Out Scope**:
  - 不修改 detach 逻辑（heartbeat hook 不变）

## 关键场景
（无）

## 技术约束
（无）

## 验收标准
- attach/detach 调用对称
- 4 个测试（attach 正常/idempotent/detach/hook 集成）
