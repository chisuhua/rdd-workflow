# rddf-sessions-gc

**Priority**: P2
**Phase**: v2.1
**Status**: proposed

## Why

## 架构依据
- 复盘发现：sessions.json 中有 1 个 owner="current"（字面字符串）的废弃 session，且本次 8-P0 全流程从未被记录
- 根因：session 创建时 owner_opencode_session_id 使用了占位符 "current" 而非真实 session ID，且无 GC 机制

## 范围
- **In Scope**:
  - `./rddf sessions gc` 子命令：扫描并清理 owner 为字面字符串 "current"、状态 abandoned/orphaned 超 7 天的 session
  - `./rddf sessions gc --dry-run` 预览模式
  - 修复 session 创建逻辑：确保 owner 获取真实 session ID（从环境变量 OPENAICODE_SESSION 或 guidgen 生成）
  - 2 个 bats 测试：GC 清理废弃 session、dry-run 不实际删除
- **Out Scope**:
  - 不修改 session 数据模型

## 验收标准
- `./rddf sessions gc --dry-run` 能找到 "current" owner 的废弃 session
- `./rddf sessions gc` 清理后 sessions.json 干净
- 2 个 bats 测试通过
