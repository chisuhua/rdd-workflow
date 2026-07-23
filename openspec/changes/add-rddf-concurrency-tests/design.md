## Context

`rddf_session.py` 使用 `_with_file_lock` 配合 `LOCK_NB`（非阻塞 fail-fast）实现文件级并发控制。但当前并发语义未经过验证——没有测试覆盖 100 级并发 session 创建、超时恢复、孤儿 session 清理等场景。多 agent 或多 OpenCode session 并行使用时存在静默数据损坏风险。

## Goals / Non-Goals

**Goals:**
- 并发测试：`multiprocessing.Pool` 并发 100 次 `create_session`，验证 LOCK_NB fail-fast 语义（无排队、无无限重试、无数据损坏）
- 跨 session 恢复测试：模拟 session 超时 → 孤儿 session → `find_next_recommendation` + `transfer_ownership` 恢复链
- 测试文件置于 `tests/integration/` 目录

**Non-Goals:**
- 不改动 `rddf_session.py` 生产代码（纯测试变更）

## Decisions

- **`multiprocessing.Pool` 而非 `threading`**：`multiprocessing` 使用独立进程，更能模拟真实并发竞争条件（GIL 不干扰文件锁行为）
- **测试置于 `tests/integration/`**：依赖完整文件系统状态，不属于纯单元测试
- **断言策略**：不依赖精确超时窗口，而是用 `LOCK_NB` 的 `EWOULDBLOCK` 行为 + 最终状态一致性来验证

## Risks / Trade-offs

- **低风险**：纯测试变更，不修改生产代码
- **测试执行时间**：100 并发进程 + 文件锁竞争，单次运行约 3-5 秒，CI 可接受
- **无新依赖**：仅使用 Python 内置 `multiprocessing` 和 `os`、`fcntl` 模块