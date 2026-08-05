# subagent-orchestrator-execution-strategy — Implementation Tasks

## 1. Setup & Baseline

- [ ] 1.1 验证 openspec CLI (1.4.1+) 和 git 工具可用
- [ ] 1.2 确认 working tree 干净,创建 worktree `openspec/subagent-orchestrator-execution-strategy`
- [ ] 1.3 读 improvements/subagent-orchestrator-execution-strategy.md 和 proposal.md 完整内容

## 2. Write Failing Tests

- [ ] 2.1 识别需要 TDD 测试覆盖的关键功能点 (从 验收 段提取)
- [ ] 2.2 写 failing 测试 (Bats/Python/TypeScript,根据项目主语言)
- [ ] 2.3 验证测试在无实现时 FAIL (RED 阶段)

## 3. Implementation

- [ ] 3.1 实现核心功能(从 范围.In Scope 拆解)
- [ ] 3.2 添加错误处理 + 日志记录(若适用)
- [ ] 3.3 文档化(AGENTS.md / SKILL.md / 配置说明)

## 4. Verify Pass

- [ ] 4.1 跑测试,验证 2.1 写的测试现在 PASS (GREEN 阶段)
- [ ] 4.2 跑完整测试套件,确认无回归
- [ ] 4.3 验证 验收 段所有标准达成
- [ ] 4.4 跑 lsp_diagnostics 确认无 lint 错误

## 5. Commit & Archive

- [ ] 5.1 按仓库约定写 commit message (feat/fix/refactor/chore scope)
- [ ] 5.2 在 worktree 内 commit working tree
- [ ] 5.3 通过 guide-ship Phase 3 archive (merge → archive → cleanup)

---

## Acceptance Criteria (from proposal)

- 配额充足场景:子代理执行时间 ≤ 直接执行的 1.5x(超时则切到 orchestrator)
- 配额耗尽场景:重试 1 次后自动降级到 orchestrator,无用户介入
- 决策矩阵文档化在 `skills/rdd-workflow-writing-plans/SKILL.md` 或新建 `skills/subagent-strategy/`
- 5 次连续测试中,决策正确率 > 90%
- `.rddf/state/quota_failures.json` 在降级时自动记录
