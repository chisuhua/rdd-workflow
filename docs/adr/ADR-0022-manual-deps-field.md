# ADR-0022: Manual Deps Field for roadmap-meta.yaml

> **状态**: 已采纳
> **日期**: 2026-07-20
> **作者**: sisyphus (with Oracle analysis of `.rddf/orch_plans/` necessity)
> **evolved-from**: ADR-0016 §1（arch-artifact-discovery-contract - "extend not replace"）, ADR-0020（incremental-skeleton-planning - planned status for progressive filling）

## Context

spec-workflow 存在一个缺口：deps 分析（3 轴静态：文件冲突、ADR 引用、接口依赖）纯粹是派生的。用户无法声明"change A 必须在 change B 之前运行"，即便静态分析检测不到任何文件级冲突。`deps-analysis.json` 中的 `parallel_group` 字段是拓扑计算的——用户无法覆盖它。

现有的编排机制（`roadmap.md`、`proposal-suggestions.md`、`iteration.json.feature_view`）要么太粗，要么太派生。所需要的是字段级的表达能力：让 `roadmap-meta.yaml` 承载人工编写的依赖声明。

本 ADR 由 Oracle 在评估是否需要 `.rddf/orch_plans/`（新的编排计划目录）时的分析触发。Oracle 的结论是：**不需要新目录**——只需向 `roadmap-meta.yaml` 添加 `manual_deps` 字段并让 `deps` 合并它们。本 ADR 记录该决策。

**架构依据**:
- ADR-0016 §1 - arch-artifact-discovery-contract: "extend not replace" 原则
- ADR-0020 - incremental-skeleton-planning: planned 状态支持渐进填充

## Decision

在每个 change 的 `roadmap-meta.yaml` 中添加两个可选字段：

```yaml
roadmap:
  manual_deps: []      # list[str]: 必须先于本 change 完成的 change 列表
  manual_blocks: []    # list[str]: 本 change 必须先于其完成的 change 列表
```

这些是人工编写的覆盖。当 `deps` 运行其 3 轴分析时，它在计算 `parallel_group` 和 `execution_order` **之前**将 `manual_deps` 合并进依赖图。**人工意图优先于静态分析**：如果 `manual_deps` 声明 A->B 但静态分析未发现证据，`deps` 尊重人工声明，并标注 `recommendation: "manual override, no static evidence"`。

### 读取端变更

- `deps_output.py`：新增 `merge_manual_deps(changes, project_root)` 函数，读取每个 change 的 `roadmap-meta.yaml`，在 `build_analysis()` 之前将 `manual_deps` / `manual_blocks` 合并进 change 记录。
- `iteration_schema.json` v3 -> v4：`changes[]` 获得 `manual_deps` 和 `manual_blocks` 镜像字段（只读，由 deps 同步）。
- `iteration.py::set_deps_info()`：扩展以接受 `manual_deps` / `manual_blocks` 参数。
- `propose_change.py`：在新的 `roadmap-meta.yaml` 文件中写入空的 `manual_deps: []` 和 `manual_blocks: []`。

### 向后兼容

现有 `roadmap-meta.yaml` 中缺失 `manual_deps` 字段 -> 视为 `[]`（无 manual deps）。旧 deps 输出在没有此字段的情况下仍可工作。

### 备选方案

| 备选 | 理由 |
|------|------|
| **(A) `roadmap-meta.yaml` 添加 `manual_deps` 字段（采纳）** | 最小改动：2 个新字段于现有文件，遵循 ADR-0016 "extend not replace" 原则；无新目录、无新 schema |
| **(B) 新增 `.rddf/orch_plans/` 目录（拒绝）** | 引入新目录 + 新 schema + 新写入方，违反"extend not replace"；Oracle 结论：不必要 |
| **(C) 在 `roadmap.md` 中编码（拒绝）** | `roadmap.md` 是粗粒度的 phase/category 视图，无字段级表达能力 |
| **(D) 在 `iteration.json.feature_view` 中编码（拒绝）** | `feature_view` 是派生视图，非人工编辑入口；写入会被下一次 hook 覆盖 |

## Consequences

### 正面

- 用户可以表达静态分析无法检测的串行化意图（如"先部署基础设施再部署应用代码"，即便无文件重叠）
- 最小改动：现有文件中加 2 个新字段，无新目录、无新 schema
- 遵循 ADR-0016 原则：扩展现有工件而非创建新工件
- 面向未来：当 ADR-0010 v2.1 实现 `DependencyScheduler` 时，`manual_deps` 可直接喂入调度器

### 负面 / 风险

- 人工编写的 deps 可能产生不可行图（环）。`deps` 应检测并警告（不报错——让人工修复）
- 如果 `manual_deps` 与静态证据矛盾，recommendation 应注明覆盖但不阻塞执行

### 中性

- `roadmap-meta.yaml` 从 7 个字段增长到 9 个字段
- `iteration_schema.json` 版本从 v3 升至 v4

## References

- `docs/adr/ADR-0016-arch-artifact-discovery-contract.md` §1 - "extend not replace" 原则
- `docs/adr/ADR-0020-incremental-skeleton-planning.md` - planned 状态支持渐进填充
- `docs/adr/ADR-0010-multi-session-management.md` - v2.1 `DependencyScheduler` 的未来消费者
- `skills/deps/scripts/deps_output.py` - `merge_manual_deps()` 的实现位置
- `skills/_lib/schemas/iteration_schema.json` - v3 -> v4 schema 升级
- `skills/propose/scripts/propose_change.py` - 空 `manual_deps: []` 写入位置
