## Implementation Tasks

- [x] 3 个测试用例: cross-repo 提案批准成功 / 本地提案不触发 / gh缺失优雅降级
- [x] 端到端: guide-design approve → Hub issue 自动出现 → 本地状态正确

## 依赖与执行顺序

- 依赖: 见 `.rddf/state/deps-analysis.json` (deps 阶段生成)
- 执行模式: lightweight 或 worktree 由 `.plan-handoff.json` 决定 (per ADR-0024)
