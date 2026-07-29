# deps-driven-execution-mode — 设计文档

## 架构概述

在 plan 阶段的 deps 分析时就决定执行模式，将决策写入 `.plan-handoff.json`，`guide-ship` 直接读取使用。

## 详细设计

### Phase 1: deps 输出扩展

在 `deps_output.py` 中新增 `analyze_execution_mode()` 函数，基于以下维度分析：

```
              deps 分析
                 │
      ┌──────────┴──────────┐
      │                     │
 文件冲突检测            改动量评估
      │                     │
  ┌───┴───┐          ┌─────┴─────┐
  │       │          │           │
 有冲突  无冲突     小改动     大改动
  │       │          │           │
worktree  继续判断  lightweight  worktree
          │
          │
     依赖关系检测
          │
      ┌───┴───┐
      │       │
   有依赖  无依赖
      │       │
  worktree  lightweight
```

### Phase 2: deps 输出写入 JSON

在 `deps` Step 5b 中写入结构化 JSON，包含 `execution_mode_recommendations` 字段。

### Phase 3: plan-handoff 扩展

在 `guide-plan` Phase 5 (plan-done) 时，将执行模式建议写入 `.plan-handoff.json`。

### Phase 4: guide-ship 使用决策

修改 `ship_plan.sh` 的 `detect_execution_mode()`，优先读取 plan-handoff 中的决策。