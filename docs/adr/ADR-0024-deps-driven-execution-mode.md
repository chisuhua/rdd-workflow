# ADR-0024: deps 阶段驱动执行模式决策

> **状态**: 已采纳
> **日期**: 2026-07-24
> **决策者**: sisyphus

## Context

当前 `guide-ship` 在 Phase 1 通过 `detect_execution_mode()` 检测并行冲突（worktree 数量 + changes 数量）来决定执行模式。这种方式存在两个问题：

1. **小改动也创建 worktree**：单文件修改、简单 typo 修复仍然创建 worktree，增加开销
2. **信息不对称**：deps 分析已经收集了文件冲突、依赖关系等信息，但这些信息没有传递给 ship 阶段

**架构依据**:
- ADR-0003 §2.1: 三阶段架构（arch → plan → ship）
- ADR-0019: change 与架构对齐检查
- .rddf/improvements/deps-driven-execution-mode.md: 完整问题分析和解决方案

## Decision

**在 plan 阶段的 deps 分析时就决定执行模式**，并将决策写入 `.plan-handoff.json`，`guide-ship` 直接读取使用。

### 影响范围

**In Scope**:
- `skills/deps/scripts/deps_output.py` - 新增执行模式分析函数
- `skills/guide-plan/scripts/plan_done_gate.py` - 写入执行模式决策到 handoff
- `skills/guide-ship/scripts/ship_plan.sh` - 从 handoff 读取决策
- `skills/_lib/schemas/deps_analysis_schema.json` - 新增 ExecutionModeRecommendation 定义

**Out Scope**:
- `detect_execution_mode()` 的 fallback 逻辑（保留向后兼容）
- 手动 override 机制（保留 `FORCE_WORKTREE=yes` 环境变量）

### 决策维度

| 信息类型 | 来源 | 对执行模式的影响 |
|---------|------|-----------------|
| **文件数** | design.md (Create/Modify/Delete 行) | ≤2 → lightweight |
| **任务数** | tasks.md (checkbox 行) | ≤3 → lightweight |
| **风险关键词** | proposal.md | refactor/migration/breaking → worktree |
| **文件冲突** | deps-analysis.json → conflicts | 有冲突 → worktree |

### 决策阈值

```python
if is_risky:
    return "worktree"  # 高风险操作
elif file_count <= 2 and task_count <= 3:
    return "lightweight"  # 小改动
elif file_count <= 5 and task_count <= 6:
    return "lightweight"  # 中等改动 - 优化小改动开销
else:
    return "worktree"  # 大改动
```

**关键设计**：中等改动（3-5 文件，4-6 任务）也优先 lightweight，这是优化小改动开销的核心目标。

### 数据流

```
deps 分析 → deps-analysis.json (execution_mode_recommendations)
           ↓
plan-done → .plan-handoff.json (execution_mode_decisions)
           ↓
guide-ship → detect_execution_mode() 读取 handoff 决策
```

### 备选方案

| 备选 | 理由 |
|------|------|
| **当前方案（deps 分析决策）** | 接受 - 信息完整、决策提前、数据流清晰 |
| 在 ship 阶段分析 | 拒绝 - 信息不对称、重复分析 |
| 基于并行冲突检测 | 拒绝 - 粒度粗糙、无法识别小改动 |

## Consequences

### 正面

- **减少开销**：小改动（≤2 文件，≤3 任务）直接在 main repo 分支工作，跳过 worktree 创建
- **决策提前**：在 plan 阶段就有明确的执行模式建议，方便用户规划
- **信息完整**：利用 deps 分析已有的文件冲突、依赖关系信息
- **向后兼容**：保留 fallback 逻辑，handoff 缺失时使用旧逻辑

### 负面 / 风险

- **新增依赖**：plan_done_gate.py 现在依赖 deps-analysis.json
- **Schema 变更**：deps-analysis.json 新增 `execution_mode_recommendations` 字段
- **测试成本**：需要新增集成测试验证完整数据流

### 后续待办

- [x] 实现 `analyze_execution_mode()` 和 `compute_execution_mode_recommendations()`
- [x] 更新 `build_analysis()` 写入 execution_mode_recommendations
- [x] 更新 `plan_done_gate.py` 写入 execution_mode_decisions
- [x] 更新 `detect_execution_mode()` 读取 handoff
- [x] 更新 schema（deps_analysis_schema.json）
- [x] 添加单元测试（6 个测试用例）
- [ ] 实战验证（在真实项目上测试）

## References

- `.rddf/improvements/deps-driven-execution-mode.md` — 完整问题分析和解决方案
- `skills/deps/scripts/deps_output.py` — 执行模式分析实现
- `skills/guide-plan/scripts/plan_done_gate.py` — handoff 写入逻辑
- `skills/guide-ship/scripts/ship_plan.sh` — handoff 读取逻辑
- `tests/unit/test_execution_mode.py` — 单元测试
