## Implementation Tasks

- [ ] 3 个测试用例:纯本地提案无 RFC 占位 / 跨仓提案含占位 / 跨仓提案缓存命中跳过重新生成
- [ ] 端到端: propose → design → plan 全程0 手工 cross-repo 调用

## 依赖与执行顺序

- 依赖: 见 `.rddf/state/deps-analysis.json` (deps 阶段生成)
- 执行模式: lightweight 或 worktree 由 `.plan-handoff.json` 决定 (per ADR-0024)
