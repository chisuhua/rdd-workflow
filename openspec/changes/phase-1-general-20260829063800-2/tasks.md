## Implementation Tasks

- [x] 4 scheduler × 3 场景 = 12 测试用例全部 pass
- [x] `install.sh --git-hooks` 安装后 hooks 生效实测
- [x] webhook HMAC 验签单元测试覆盖4 种异常路径

## 依赖与执行顺序

- 依赖: 见 `.rddf/state/deps-analysis.json` (deps 阶段生成)
- 执行模式: lightweight 或 worktree 由 `.plan-handoff.json` 决定 (per ADR-0024)
