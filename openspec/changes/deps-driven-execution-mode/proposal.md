# deps-driven-execution-mode

## 为什么（Why）

### 当前问题

1. **决策时机滞后**：执行模式在 `guide-ship` Phase 1 才决定，但此时所有 changes 已提交，无法提前优化
2. **决策维度不足**：仅基于"是否有其他 worktree"和"changes 数量"，忽略了依赖关系和文件冲突
3. **批量处理低效**：多个 changes 全部创建 worktree，即使其中部分是小改动且无冲突

### 用户痛点

当前小改动（如 1 行删除、1 个文件修改）也需要走完整的 worktree 创建流程，浪费约 30 秒/次。

## 做什么（What Changes）

**核心思路**：在 plan 阶段的 deps 分析时就决定执行模式，并将决策写入 `.plan-handoff.json`，`guide-ship` 直接读取使用。

### 决策维度

| 信息类型 | 来源 | 对执行模式的影响 |
|---------|------|-----------------|
| **文件冲突** | deps-analysis.json → conflicts | 有冲突 → 强制 worktree |
| **依赖关系** | deps-analysis.json → dependency_graph | 有依赖 → 可能需要 worktree |
| **独立性** | deps-analysis.json → all_independent | 完全独立 → 可轻量模式 |
| **改动量** | design.md + tasks.md | 小改动 → 优先轻量模式 |

### 受影响文件

| 文件 | 改动类型 | 改动量 |
|------|---------|--------|
| `skills/deps/scripts/deps_output.py` | 新增函数 `analyze_execution_mode` | +80 行 |
| `skills/deps/scripts/deps_output.py` | 修改 `render_markdown_report` | +20 行 |
| `skills/_lib/schemas/deps_analysis_schema.json` | 版本 bump + 新字段 | +50 行 |
| `skills/guide-plan/scripts/plan_done_gate.sh` | 写入 execution_mode_decisions | +30 行 |
| `skills/guide-ship/scripts/ship_plan.sh` | 读取并使用决策 | +40 行 |
| `tests/unit/test_deps_output.py` | 新增测试 | +60 行 |