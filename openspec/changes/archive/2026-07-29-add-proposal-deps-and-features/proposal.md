## Why

ADR-0022（manual_deps 字段）定义了 change 级的 `manual_deps`，但缺少向上游 proposal 级的扩展链路。feature skill 已具有 `parent_feature` 分组机制，但 `parent_feature` 只在 propose 创建 change 后才有来源——proposal 阶段没有 feature 标签可附着。18 个现有改进提案的正文中提及了依赖关系，但没有结构化字段承载。

## What Changes

**范围已缩小**（原提案部分已实现）：
- `improvements/<name>.md` 新增两个可选元数据字段：`**依赖**: [name1, name2]` 和 `**特性**: feature-name`
- `proposal-approved.md` 新增两个可选列：`依赖`、`特性`（缺省为空）
- 新增 Python 模块 `skills/propose/scripts/proposal_deps_analyzer.py`：解析显式 `**依赖**` 字段 + 自动检测提案正文中的引用
- `guide-plan` propose 阶段增强：按拓扑排序创建 changes

## Capabilities

### New Capabilities
- `proposal-deps-analyzer`: 提案级依赖分析和拓扑排序
- `proposal-feature-metadata`: 提案级 feature 标签元数据

### Modified Capabilities
- `propose-flow`: 在 propose 阶段消费依赖和 feature 元数据

## Impact

- 新建文件：skills/propose/scripts/proposal_deps_analyzer.py
- 修改文件：skills/guide-plan/SKILL.md, proposal-approved.md 格式
- 已实现部分（不在本 change 范围）：`parent_feature` 字段已完整实现，`manual_deps` 已写入 roadmap-meta.yaml
