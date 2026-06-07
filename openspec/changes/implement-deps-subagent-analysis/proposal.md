## Why

- skills/deps.md:345:`<!-- TODO: 子代理语义分析尚未实现。当前仅执行 Step 2 静态分析。后续可由独立 change 实现完整 subagent 调用。 -->`
- docs/audit/2026-06-05-workflow-audit.md:490:L320 TODO 同源
- 3 处文档(deps.md L345/L499/L566)明确标注占位符待实现

## What Changes

- **In Scope**:
- 在 skills/deps.md Step 3 实现子代理语义分析
- 调用 subagent 读取各 change 的 proposal.md/design.md/tasks.md
- 输出补充的依赖关系到 .zcf/.deps-output.md
- **Out Scope**:
- 不修改 Step 2 静态三轴分析逻辑
- 不改 .zcf/.deps-candidates.json 格式

## Capabilities

### New Capabilities
- `general`: implement-deps-subagent-analysis 实施的功能能力

### Modified Capabilities
<!-- Existing capabilities whose REQUIREMENTS are changing. Leave empty if no requirement changes. -->

## Impact

- **代码影响**: skills/*.md (新增/修改)
- **依赖影响**: 2-3天
- **来源**: 代码 TODO (skills/deps.md:345)
