## Implementation Tasks

- [x] 3 reference plugins 端到端测试通过
- [x] plugin manifest schema 测试 (5 个 invalid case reject)
- [x] plugin 隔离性测试 (mock plugin 抛异常不影响主流程)

## 依赖与执行顺序

- 依赖: 见 `.rddf/state/deps-analysis.json` (deps 阶段生成)
- 执行模式: lightweight 或 worktree 由 `.plan-handoff.json` 决定 (per ADR-0024)
