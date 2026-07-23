# guide-cross-validate

**优先级**: P1 | **来源**: Session 复盘 2026-07-21
**阶段**: v2.1 | **分类**: planning
**类型**: feature

## 架构依据
- 复盘发现：`./rddf guide` 推荐 guide-ship 处理 add-rddf-cli-v1，但它已在 3 天前归档
- 根因：guide 推荐器只读 plan-handoff.committed_changes，未交叉验证 openspec/changes/archive/ 目录

## 范围
- **In Scope**:
  - guide.md 推荐逻辑增加交叉验证步骤：对比 committed_changes 与 archive 目录
  - 自动跳过已归档的 change，不将其纳入 active_changes 计数
  - 2 个 bats 测试：有 stale handoff 时的推荐、handoff + archive 交叉验证
- **Out Scope**:
  - 不修改 plan-handoff 文件本身（那是 guide-plan plan-done 的职责）

## 关键场景
（无）

## 技术约束
（无）

## 验收标准
- `./rddf guide` 不推荐已归档的 change
- 2 个 bats 测试通过
