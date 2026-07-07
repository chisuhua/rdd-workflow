# 项目路线图

## 元信息
- **版本**: 2
- **创建时间**: 2026-06-07T09:16:26+08:00
- **最后更新**: 2026-06-28
- **当前阶段**: v2.0 (已完成)

## v2.0 已完成 (2026-06-26)

v2.0.0-beta 已发布。包含 5 个 Phase，8 个 ADR (ADR-0002~0008) 已全部实施。

详见 `docs/v2-implementation-plan.md`。

## v2.1 规划

### Phase 1: 完整多会话支持
**目标**: 完成 ADR-0010 的完整实现（并行会话、依赖调度）
**状态**: 📋 待启动
**对应 Change**: `v2-multi-session`
**预计工作量**: 中型 (2-3 周)

## v3.0 规划

### Phase 1: 定时循环与事件触发
**目标**: 实现 ADR-0009 定时触发器
**状态**: 📋 待规划
**对应 Change**: `v3-scheduled-triggers`
**预计工作量**: 小型 (1-2 周)

### Phase 2: 阶段步骤化执行
**目标**: 实现 ADR-0011 步骤化执行模型
**状态**: 📋 待规划
**对应 Change**: `v3-step-pipeline`
**预计工作量**: 大型 (3-4 周)

### Phase 3: 流程定制层
**目标**: 实现 ADR-0012 自定义流程
**状态**: 📋 待规划
**对应 Change**: `v3-flow-customization`
**预计工作量**: 大型 (3-4 周)
**依赖**: Phase 2 (步骤化执行模型为基础)

<!-- AUTO-SPRINT-START -->
_Phase: `v3.0` · Active: 1 · Archived: 0 · Last deps: never_

| Change | Phase | Cat | Status | Blocker | Group | Conflicts | Tasks | Plan |
|--------|-------|-----|--------|---------|-------|-----------|-------|------|
| v3-scheduled-triggers | v3.0 | loop-engin | 📋 proposed | — | — | — | 0/5 | — |
<!-- AUTO-SPRINT-END -->
