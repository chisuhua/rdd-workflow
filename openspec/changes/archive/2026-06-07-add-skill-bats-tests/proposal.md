## Why

- README.md 前置条件:bats-core 1.10+ 是测试基础设施
- USAGE.md §3 描述测试驱动开发
- 9 个 skill 全部无 bats 单元测试(高风险回归)

## What Changes

- **In Scope**:
- 为 skills/*.md 中的每个 skill 添加 bats 测试文件
- 测试覆盖:9 个 skill(INSTALL, deps, execute, guide, guide-ship, guide-spec, propose, roadmap, status)
- 在 tests/ 下建立 _lib 共享辅助函数
- **Out Scope**:
- 不修改 skill 内容本身
- 不替换 bats 框架

## Capabilities

### New Capabilities
- `general`: add-skill-bats-tests 实施的功能能力

### Modified Capabilities
<!-- Existing capabilities whose REQUIREMENTS are changing. Leave empty if no requirement changes. -->

## Impact

- **代码影响**: skills/*.md (新增/修改)
- **依赖影响**: 3-5天
- **来源**: 测试覆盖缺口扫描(Phase 1d)
