# 项目路线图

## 元信息
- **版本**: 2
- **创建时间**: 2026-06-07T09:16:26+08:00
- **最后更新**: 2026-07-20 (Plan C: refresh-input-sources)
- **当前阶段**: v2.0 (已完成)

## v2.0 已完成 (2026-06-26)

v2.0.0-beta 已发布。包含 5 个 Phase，8 个 ADR (ADR-0002~0008) 已全部实施。

详见 `docs/v2-implementation-plan.md`。

## v2.1 规划

### Phase 1: 完整多会话支持
**目标**: 完成 ADR-0010 的完整实现（并行会话、依赖调度）
**状态**: 📋 待启动
**Changes**:
| Change | Priority | Effort | Wave | Manual Deps | 描述 |
|--------|----------|--------|------|-------------|------|
| `v2-multi-session` | P0 | 2-3w | 1 | — | 多会话协调 + 依赖图调度器 (ADR-0010 §4) |
| `add-review-phase-debt-reflow` | P1 | 1-2w | 1 | — | Review 阶段债务回流机制 (ADR-0014) |
| `add-openspec-validate-critic` | P1 | 2-3h | 2 | `add-review-phase-debt-reflow` | openspec validate 集成为 plan-critic (ADR-0015) |
| `add-arch-artifact-discovery` | P1 | 1-2w | 1 | — | Arch 工件发现契约 (ADR-0016) |
| `add-incremental-skeleton-planning` | P2 | 1w | 2 | `add-arch-artifact-discovery` | 增量 skeleton planning (ADR-0020) |
| `add-manual-deps-field` | P1 | 1-2d | 1 | — | manual_deps 人工依赖声明 (ADR-0022) ✅ |
| **预计总计** | | **6-10w** | | | |

### Phase 2: 编排能力完善
**目标**: 补齐人工编排意图表达 + roadmap 格式升级 (ADR-0022)
**状态**: ✅ 部分完成
**Changes**:
| Change | Priority | Effort | Wave | Manual Deps | 描述 |
|--------|----------|--------|------|-------------|------|
| `add-manual-deps-field` | P1 | 1-2d | 1 | — | manual_deps 字段 + iteration_schema v4 + deps 合并 (ADR-0022) ✅ |
| **预计总计** | | **1-2d** | | | |

## v3.0 规划

### Phase 1: 定时循环与事件触发
**目标**: 实现 ADR-0009 定时触发器
**状态**: 📋 待规划
**Changes**:
| Change | Priority | Effort | Wave | Manual Deps | 描述 |
|--------|----------|--------|------|-------------|------|
| `v3-scheduled-triggers` | P1 | 1-2w | 1 | — | 定时循环 + 事件触发 (ADR-0009) |
| **预计总计** | | **1-2w** | | | |

### Phase 2: 阶段步骤化执行
**目标**: 实现 ADR-0011 步骤化执行模型
**状态**: 📋 待规划
**Changes**:
| Change | Priority | Effort | Wave | Manual Deps | 描述 |
|--------|----------|--------|------|-------------|------|
| `v3-step-pipeline` | P1 | 3-4w | 1 | — | 阶段步骤化执行模型 (ADR-0011) |
| **预计总计** | | **3-4w** | | | |

### Phase 3: 流程定制层
**目标**: 实现 ADR-0012 自定义流程
**状态**: 📋 待规划
**依赖**: Phase 2 (步骤化执行模型为基础)
**Changes**:
| Change | Priority | Effort | Wave | Manual Deps | 描述 |
|--------|----------|--------|------|-------------|------|
| `v3-flow-customization` | P1 | 3-4w | 1 | - | 流程定制层 (ADR-0012) |
| **预计总计** | | **3-4w** | | | |

## v2.1 质量改进计划

> 来源: `.omo/plans/improve-change-quality-index.md` (Plan A/B/C/D)
> 执行顺序: Wave 1 (C ∥ A) -> Wave 2 (B) -> Wave 3 (D)
> 不引入新 ADR 引用，仅在现有架构上提升 change 质量与可观测性。

| Change | Priority | Effort | Wave | Manual Deps | 描述 |
|--------|----------|--------|------|-------------|------|
| `refresh-input-sources` | P0 | 1-2h | 1 | - | Plan C: 扩展 roadmap + gap-analysis + TODO 扫描 |
| `refine-adr-0015-wiring` | P0 | 2-3h | 1 | - | Plan A: 补完 ADR-0015 plan-critic 链路 (状态 待定 -> 已采纳) |
| `add-propose-output-validation` | P1 | 6-8h | 2 | `refine-adr-0015-wiring` | Plan B: iteration_schema v3->v4 + 5 个 check + STRICT_PROPOSE_GATE |
| `add-change-quality-guide` | P1 | 2-3h | 3 | `add-propose-output-validation` | Plan D: docs/change-quality-guide.md + AGENTS.md/propose.md 引用 |
| **预计总计** | | **11-16h** | | | |
