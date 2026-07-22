## Why

- docs/adr/ 目录不存在
- docs/proposal-suggestions-format.md 假设存在 ADR 引用
- 9 个 skill 中隐含架构决策未结构化记录

## What Changes

- **In Scope**:
- 创建 docs/adr/ 目录结构
- 添加 ADR 模板(ADR-0000-template.md)
- 编写首个 ADR(rdd-workflow 架构选型)
- **Out Scope**:
- 不迁移现有 skill 中的隐含决策
- 不修改 proposal-suggestions-format.md 引用规则

## Capabilities

### New Capabilities
- `general`: init-adr-directory 实施的功能能力

### Modified Capabilities
<!-- Existing capabilities whose REQUIREMENTS are changing. Leave empty if no requirement changes. -->

## Impact

- **代码影响**: skills/*.md (新增/修改)
- **依赖影响**: 0.5-1天
- **来源**: 扫描缺口(Phase 1a)
