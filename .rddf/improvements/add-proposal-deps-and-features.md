# add-proposal-deps-and-features

**优先级**: P1 | **来源**: 用户实战讨论 2026-07-28
**阶段**: v2.1 | **分类**: planning
**类型**: feature
**依赖**: | **特性**:

## 架构依据

1. **ADR-0022（manual_deps 字段）** 定义了 change 级的 `manual_deps`，但缺少向上游 proposal 级的扩展链路。提案依赖关系和 change 级依赖之间没有自动传递机制。
2. **feature skill** 已具有 `parent_feature` 分组机制和 `__ungrouped__` 兜底，但 `parent_feature` 只在 propose 创建 change 后才有来源——proposal 阶段没有 feature 标签可附着。
3. **实际痛点**：18 个现有改进提案的正文中提及了依赖关系（如 `add-openspec-gate` 的依赖建议 `add-full-regression-gate` 优先落地），但没有结构化字段承载；所有 proposal 在 `proposal-approved.md` 中是平铺列表，无法按 feature 分组规划。
4. **dependency（依赖排序）和 feature（分组管理）是正交但互补的维度**——前者决定创建顺序，后者决定归属视图。两者都通过扩展 proposal 元数据 + 在 `guide-plan` propose 阶段消费实现。合成一个提案减少改动点。

## 范围

- **In Scope**:
  - `improvements/<name>.md` 新增两个可选元数据字段：
    - `**依赖**: [name1, name2]` — 显式声明前置提案
    - `**特性**: feature-name` — feature 标签（空=小改动/ungrouped）
  - `proposal-approved.md` 新增两个可选列：`依赖`、`特性`（缺省为空）
  - 新增 Python 模块 `skills/propose/scripts/proposal_deps_analyzer.py`：
    - 解析显式 `**依赖**` 字段
    - 自动检测提案正文中匹配 `improvements/<name>` / `ADR-NNNN` 的引用
    - 合并两个来源生成完整依赖图
  - `guide-plan` propose 阶段增强：
    - 按拓扑排序创建 changes（依赖排序）
    - 将 feature 标签写入 `iteration.json` 的 `parent_feature`
    - 将依赖关系自动写入 `roadmap-meta.yaml` 的 `manual_deps`
  - 单元测试 + bats 集成测试
- **Out Scope**:
  - 不修改 `deps` skill（已有 change 级依赖处理）
  - 不修改 `feature` skill 已有视图逻辑（它已能消费 `parent_feature`）
  - 不做跨提案的语义相似度分析（仅做精确引用匹配）
  - 不自动阻断（依赖只是排序建议，不强制创建顺序）
  - 不修改 `proposal-suggestions.md` 格式

## 关键场景

- GIVEN `improvements/add-foo.md` 含 `**依赖**: [add-bar]` 且 `**特性**: wave-core`, WHEN `guide-plan` propose 运行, THEN add-bar 的 change 先创建，add-foo 后创建；add-foo 的 `parent_feature=wave-core` 写入 iteration.json，`manual_deps=[add-bar]` 写入 roadmap-meta.yaml
- GIVEN `improvements/add-qux.md` 无 `**特性**` 字段, WHEN propose 创建 change, THEN `parent_feature` 为空，`feature` skill 将其归入 `__ungrouped__`（小改动）
- GIVEN `improvements/add-quux.md` 的架构依据中引用 `improvements/add-foo.md` 但无显式 `**依赖**`, WHEN `proposal_deps_analyzer` 运行, THEN 自动识别该引用并建议依赖，标注 `auto-detected`
- GIVEN 两个提案无任何引用关系且属于同一 feature, WHEN propose 运行, THEN 两者可并行创建，共享同一 feature 分组

## 技术约束

- MUST `**依赖**` 和 `**特性**` 字段向后兼容：缺失视为无依赖/无 feature
- MUST 自动检测结果标注 `auto-detected` 来源，与显式声明区分
- MUST 拓扑排序遇到环形依赖时输出警告并回退到优先级排序
- MUST NOT 修改现有 `deps` skill 或 `feature` skill 的输入/输出格式
- SHOULD `proposal-approved.md` 新增的 `依赖` / `特性` 列缺省显示 `-`
- SHOULD `proposal_deps_analyzer.py` 复用 `deps_output.py` 中的 `merge_manual_deps()` 模式

## 验收标准

- [ ] `improvements/<name>.md` 支持可选 `**依赖**: [name1, name2]` 和 `**特性**: feature-name` 元数据
- [ ] `proposal_deps_analyzer.py` 正确合并显式声明 + 自动检测引用
- [ ] `proposal-approved.md` 可选显示 `依赖` / `特性` 列（缺省 `-`）
- [ ] `guide-plan` propose 阶段按拓扑排序创建 changes
- [ ] feature 标签自动写入 `iteration.json` 的 `parent_feature`
- [ ] 依赖自动写入 `roadmap-meta.yaml` 的 `manual_deps`
- [ ] 环形依赖检测输出警告，回退到优先级排序
- [ ] 向后兼容：无新字段的现有提案行为不变
