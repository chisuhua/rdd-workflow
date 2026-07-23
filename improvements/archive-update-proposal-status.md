# archive-update-proposal-status

**优先级**: P1 | **来源**: Session 复盘 2026-07-21
**阶段**: v2.1 | **分类**: planning
**类型**: feature

## 架构依据
- 复盘发现：8 个 P0 全部归档后，proposal-suggestions.md 中仍标记为 "skeleton"，未更新为 "已完成"
- 根因：archive 流程缺少 proposal-suggestions.md 状态同步钩子

## 范围
- **In Scope**:
  - archive.sh::archive_change() 成功后自动调用 update_proposal_status(name, "已完成")
  - 函数实现：读取 proposal-suggestions.md JSON → 匹配 name → 更新 status → 写回
  - 3 个 bats 测试：正常更新、条目不存在时跳过、写入失败容错
- **Out Scope**:
  - 不修改 proposal-suggestions.md 格式

## 关键场景
（无）

## 技术约束
（无）

## 验收标准
- archive 后 proposal-suggestions.md 中对应条目 status 变为 "已完成"
- 3 个 bats 测试通过
