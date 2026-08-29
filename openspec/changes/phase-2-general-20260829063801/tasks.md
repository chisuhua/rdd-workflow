## Implementation Tasks

- [ ] 10 change × 3 wave 端到端测试 (生成 → execute → archive 全程)
- [ ] 失败回滚测试 (mock wave 2 失败)
- [ ] wave 计算性能测试 < 100ms

## 依赖与执行顺序

- 依赖: 见 `.rddf/state/deps-analysis.json` (deps 阶段生成)
- 执行模式: lightweight 或 worktree 由 `.plan-handoff.json` 决定 (per ADR-0024)
