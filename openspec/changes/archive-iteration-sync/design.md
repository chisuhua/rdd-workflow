## Context

复盘发现 `archive.sh` 归档时没有同步 iteration.json 的 `archived_at` 时间戳和 `status == "archived"` 状态，导致 `feature_view.archived_count` 与实际值不一致。

### 现有实现

`mark_iteration_archived()` 函数已在 `skills/_lib/archive.sh` 中实现（L331-377）：

- 通过 Python `skills._lib.iteration` 模块的 `mark_archived()` 写入 `archived_at` 时间戳和 `status = "archived"`
- 在 `archive_change()`（worktree 模式，L305-306）和 `archive_change_for_mode()` 轻量模式（L196）均已调用
- 使用 `os.environ` 传递变量（安全模式，无 bash 注入风险）
- 错误容忍：失败时打印警告但不阻塞归档流程

### 根因分析

复盘发现 5/8 个 change 缺少 `archived_at`，可能原因：
1. 在 `mark_iteration_archived` 实现**之前**归档的 change（老版本）
2. skeleton→archive 快速路径可能跳过 iteration 同步
3. 缺少回归测试导致回归未被捕获

### 需要修复的内容

**确认已有实现正确**：`mark_iteration_archived` 在两种模式下都调用。但需要：
1. 补充 3 个 bats 回归测试锁定行为
2. 验证 `feature_view.archived_count` 动态计算（不依赖缓存字段）

## Goals / Non-Goals

**Goals:**
- 3 个 bats 回归测试覆盖 `mark_iteration_archived` 核心行为
- 确认 `feature_view` 的 `archived_count` 是动态计算而非缓存

**Non-Goals:**
- 不修改 `mark_iteration_archived` 实现（已有正确实现）
- 不修改 `feature_view.py` 或 `feature_cli.py`（纯衍生视图，自动工作）
- 不为 skeleton→archive 路径增加额外逻辑（仅测试验证）

## Decisions

### Decision 1: 测试放在 `tests/integration/test_archive_iteration_sync.bats`

- **Why**: 集成测试需要真实的 `archive.sh` 环境和 `iteration.json` 文件操作，不适合单元测试
- **How**: 新文件，独立于现有 `test_archive.sh.bats` 和 `test_guide_ship_archive.bats`
- **Alternative**: 追加到 `test_archive.sh.bats`
- **Rejected**: 已有文件测试 `archive.sh` 的完整归档流程，本 test 文件专注 iteration 同步一个维度

### Decision 2: 使用 `mark_iteration_archived` 直接测试而非完整归档流程

- **Why**: 完整归档需要 `openspec archive`、`git worktree` 等外部依赖，测试复杂且缓慢
- **How**: 直接 source `archive.sh` 并调用 `mark_iteration_archived`，在临时目录中创建 `iteration.json` 测试
- **Alternative**: 完整集成测试（从 worktree 创建到归档）
- **Rejected**: 慢、依赖多、不聚焦于 iteration 同步行为

### Decision 3: `feature_view.archived_count` 已正确动态计算

- **Why**: `skills/_lib/iteration/store.py` 的 `feature_progress()` 函数（L470-482）每次调用时从 `changes` 数组动态计算。`archived_count` 是 `sum(1 for c in changes if c.get("status") == "archived")`，不依赖缓存字段
- **How**: 无需修改代码，仅需在测试中验证
- **Alternative**: 增加缓存字段
- **Rejected**: 动态计算是正确的设计，无需缓存

## API

无 API 变更。`mark_iteration_archived` 签名不变：

```bash
mark_iteration_archived <name> <main_root>
```

## Test Plan

### 3 bats 回归测试（在 `tests/integration/test_archive_iteration_sync.bats`）

| Test | Setup | Expected |
|------|-------|----------|
| 正常归档 | 创建 iteration.json 含 1 个 proposed change，调用 `mark_iteration_archived` | `archived_at` ISO 时间戳存在，`status == "archived"` |
| 重复归档幂等 | 对已归档的 change 再次调用 | 不报错，`archived_at` 不变（或更新为最新时间戳均可接受） |
| archive 失败不写入 | 模拟 `openspec archive` 失败（不调用 `mark_iteration_archived`），检查 iteration.json | `status` 不变，`archived_at` 不存在 |

### 1 个验证（`feature_progress` 动态计算）

手动验证 `feature_progress()` 实现：确认 `archived_count` 是 `sum(1 for c in changes if c.get("status") == "archived")`，不依赖缓存字段。