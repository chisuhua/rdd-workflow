# archive-history-keep-semantics

**优先级**: P2 | **来源**: Session 复盘 2026-08-04 — orphaned session 清理受阻
**阶段**: v2.1 | **分类**: core
**类型**: fix

## 架构依据
- 实测：`archive_history(keep=20)` 对 11 个 terminal sessions 返回 0 移动——keep 预算（20）大于现有 terminal 数量，全部保留
- 打印信息"kept 20 recent + active/orphaned"有误导性：orphaned 属于 terminal 状态，不因该提示而单独保留
- 2026-08-04 会话中 5 个 orphaned sessions 无法用默认 keep 清理，必须用 `keep=0` 强制归档——用户无从得知该参数语义
- 同类问题已有先例：`HydraForge 案例 2026-07-31 — archive-history 不能清理孤儿 session`（P1 已记录）

## 范围
- **In Scope**:
  - `archive_history` 支持 `--orphans` 或 `--archive-orphans` 显式清理 orphaned 状态的 session（不受 keep 预算影响）
  - 输出信息区分"保留的 active"、"保留的 terminal"与"已归档"，去掉误导性措辞
  - 文档（SKILL.md 子命令说明）补充 keep 语义与 orphaned 清理用法
  - 1-2 个 Python/unit 测试：orphaned 显式清理、keep 语义边界
- **Out Scope**:
  - 不改变 schema / 状态机
  - 不引入自动清理（保持显式操作）

## 关键场景
- **GIVEN** sessions.json 存在 5 个 orphaned sessions 且 terminal 总数小于 keep
  **WHEN** 运行 `rddf-session archive-history --archive-orphans`
  **THEN** 5 个 orphaned sessions 移入 .archive.json，其余 active 保留

## 技术约束
- 与既有 `_TERMINAL_STATES` 定义保持一致

## 验收标准
- `--archive-orphans` 能清理 orphaned sessions 而不触碰 active
- 输出信息准确反映保留/归档数量
- 测试锁定 keep 边界与 orphaned 清理
