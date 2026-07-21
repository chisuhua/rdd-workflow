# add-parent-feature-param

**Priority**: P0
**Phase**: v2.1
**Status**: skeleton

## Why

## 架构依据
- Oracle 审查结论: iteration_schema.json 中 parent_feature 字段已定义 (L99-102) 但从未被任何代码写入 — 是 dead field
- 当前所有 7 个 changes 全在 __ungrouped__，因为没有 feature- 前缀也没有 parent_feature
- 激活 parent_feature 字段即可让 change 归入 feature 组，无需新增 feature 状态机
- 与 ADR-0016 "extend not replace" 原则一致 — 扩展已有字段而非新建结构
- Schema 零变更 (字段已存在)，只需修复写入端

## 范围
- **In Scope**:
  - propose_change.py::create_skeleton_change + update_iteration_proposed 加 parent_feature 可选参数
  - propose_change.sh bash wrapper 加 --parent-feature 参数解析
  - propose.md Phase 3 菜单交互: 可选 "归属 feature" 输入
  - 拒绝 parent_feature=__ungrouped__ (保留字)
  - 前向声明语义: parent_feature 指向不存在的 feature 时视为定义新 feature
  - unit test + bats integration test
- **Out Scope**:
  - 不写 feature_view (保持纯派生，feature 命令自动重算)
  - 不新增 feature create 命令
  - 不自动从命名约定推导 feature 并提示

## 关键场景
- GIVEN propose --parent-feature feature-rddf, WHEN 创建 change, THEN iteration.json 该 change 的 parent_feature 字段 = "feature-rddf"
- GIVEN parent_feature 已设置, WHEN 运行 feature summary, THEN 该 change 显示在对应 feature 组下 (非 __ungrouped__)
- GIVEN 第一个 change 使用 parent_feature="new-feat", WHEN 第二个 change 也使用 parent_feature="new-feat", THEN 两个 change 自动归入同一组

## 技术约束
- MUST 拒绝 parent_feature=__ungrouped__ (保留字)
- MUST 不校验 parent_feature 是否已存在 (前向声明)
- MUST 显式 parent_feature 优先于 feature- 命名约定 (derive_feature_name 既有优先级)
- SHOULD 保持向后兼容 (不传 --parent-feature 时行为不变)

## 验收标准
- --parent-feature <name> 参数可用
- iteration.json change 条目含 parent_feature 字段
- feature summary 显示正确的 feature 分组
- parent_feature=__ungrouped__ 被拒绝
- 4 个 unit test + 2 个 integration test
- 所有现有测试通过

## What Changes

- TODO: define specific changes during fill phase

## Impact

- Affected specs: TBD
- Affected code: TBD
