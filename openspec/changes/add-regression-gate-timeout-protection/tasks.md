# Tasks: add-regression-gate-timeout-protection

## Implementation Tasks

- [ ] Task 1: `tests/unit/test_test_sh_flags.py`（或 bats）覆盖 `--max-duration` 参数解析
- [ ] Task 2: `tests/integration/test_regression_timeout.bats` 新增 3 个测试
- [ ] Task 3: `regression-timeout: --max-duration=1 times out gracefully`
- [ ] Task 4: `regression-timeout: partial results saved on timeout`
- [ ] Task 5: `regression-timeout: default behavior unchanged (no timeout)`
- [ ] Task 6: 进度透传测试：`bats --report-formatter` 输出逐步可见
- [ ] Task 7: `./test.sh --full --regression --max-duration=5` 5 秒后优雅超时 + 保存 partial
- [ ] Task 8: 正常全量跑（无超时）behavior 不变
- [ ] Task 9: 中断后 `--reuse-partial` 复用已通过文件（跑完未完成部分）
- [ ] Task 10: `docs/change-quality-guide.md` 加"回归门超时与进度"段
- [ ] Task 11: `AGENTS.md` 快速命令段补 `--max-duration` 示例
- [ ] Task 12: 与 `report_regression.sh` 既有逻辑不冲突（summary 输出不变）
- [ ] Task 13: 与 `--regression` / `--stop-on-failure` 组合可用
- [ ] Task 14: 与 P0-2（`report_regression.sh` sed bug 修复）不冲突（独立改动）
- [ ] Task 15: ship 后 30 天：回归门平均等待时间下降（可观测进度 + 复用 partial）
- [ ] Task 16: 不引入新的 KNOWN_FAILURES 条目
