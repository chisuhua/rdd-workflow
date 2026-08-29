## Implementation Tasks

- [ ] 3 路并行 rddf-session 实测通过,bash test 覆盖
- [ ] crash → resume 路径测试通过 (用 SIGKILL 模拟)
- [ ] sessions.json v2 schema 测试覆盖 (新增字段解析 + 旧 v1 兼容读)

## 依赖与执行顺序

- 依赖: 见 `.rddf/state/deps-analysis.json` (deps 阶段生成)
- 执行模式: lightweight 或 worktree 由 `.plan-handoff.json` 决定 (per ADR-0024)
