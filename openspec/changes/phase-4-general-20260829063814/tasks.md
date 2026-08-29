## Implementation Tasks

- [ ] 3 stakeholder 场景测试 (1 owner + 2 hub) 全流程
- [ ] baseline 管理: 新增/移除/失效 3 个测试
- [ ] 对称 verify: 本地 + Hub 失败分别正确处理

## 依赖与执行顺序

- 依赖: 见 `.rddf/state/deps-analysis.json` (deps 阶段生成)
- 执行模式: lightweight 或 worktree 由 `.plan-handoff.json` 决定 (per ADR-0024)
