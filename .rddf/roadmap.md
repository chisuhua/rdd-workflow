# Roadmap

## Phase Skeleton
| Phase | Theme | Status | Started | Done |
|-------|-------|--------|---------|------|
| phase-1 | 完整多会话支持 | active | | |
| phase-1 | 定时循环与事件触发 | active | | |
| phase-1 | 提案生成阶段 — 自动跨仓分析 (A1/A2/A3) | active | | |
| phase-1 | 2026-08-26 文档与代码一致性审计后续修复 | active | | |
| phase-2 | 审批交互阶段 — 引导式 RFC 内容确认 (B1/B3/D2) | active | | |
| phase-2 | 编排能力完善 | active | | |
| phase-2 | 阶段步骤化执行 | active | | |
| phase-3 | 审批后自动发 RFC (C1/C2) | active | | |
| phase-3 | 流程定制层 | active | | |
| phase-4 | 多方对称 + 回归 (P1-P3, 后续) | active | | |
<!-- AUTO-INDEX -->

## Fragment Index (auto-generated)

### Phases
- `phase-1` — 完整多会话支持
- `phase-2` — 审批交互阶段 — 引导式 RFC 内容确认
- `phase-3` — 审批后自动发 RFC
- `phase-4` — 多方对称与回归

### Features
- `feat-fix-agent-interface-contracts` — 对外契约修复（v4 handoff 识别 / owns 可机读 / design.md 归属 / P2 commit gate 删除 / status 暴露 builder phase） (refs: phase-4)
- `feat-fix-archive-gaps-v2` — 第二波归档治理改进（ADR 索引自动同步 / CHANGELOG-USAGE 同步 / verifier-archive-gate 边界明确化 / 第 3 波 doc drift 清理） (refs: phase-1, phase-2, phase-3, phase-4)
- `feat-fix-audit-findings` — 2026-08-26 文档与代码一致性审计后续修复 (refs: phase-1, phase-2, phase-3, phase-4)
- `feat-fix-skill-manifest-drift` — 消除 skill 清单漂移与断言硬编码 —— manifest 三向对齐 + 7 个 identity-merge shim 的 __spec__ + 日期无关的 sprint 断言 (refs: phase-4)
- `feat-fix-test-isolation-and-hygiene` — 测试隔离与仓库卫生 — 测试零污染 + 根解析统一到 canonical resolver + 状态快照/worktree 垃圾清理 + doctor plan-tdd 降噪 (refs: phase-4)
- `feat-fix-v4-residue-contract` — 契约面 v4 残留修复 — 失败路由统一 rdd-builder + feedback schema 对齐 + 用户可见文案 + v4-residue 守卫 + schema 路径扫描扩展到代码 (refs: phase-4)
- `feat-rdd-doctor-coverage-completion` — rdd-doctor coverage completion — lazy-import refactor + CI 护送 14/22 + review-debt/roadmap-backup 新 category (refs: phase-2)
- `feat-remove-dead-dup-layer` — 删除 skills/_lib 陈旧重复层 — iteration 副本 + 20 个 schema 副本 + 3 个失效代理 + 8 条死 dash 注册 + 修 populate 路径恢复被静默跳过的校验 (refs: phase-4)

<!-- AUTO-SPRINT-START -->
## Current Sprint: sprint-2026-09

| Project | Phase | Priority | Feedback | Proposal |
|---------|-------|----------|----------|----------|
| 流程定制层 | phase-3 | P1 | none | add-env-bootstrap-skill |
| 流程定制层 | phase-3 | P2 | none | add-objective-evidence-v02-llm-synthesis |
| 流程定制层 | phase-3 | P2 | none | add-objective-tracking |
| 流程定制层 | phase-3 | P1 | none | fix-skill-post-install-discoverability |
| rdd-workflow | phase-3 | P1 | none | rdd-builder-auto-pick-mode |
| rdd-workflow | phase-3 | P2 | none | rdd-builder-phase0-llm-integration |

### Unmapped (243)
- RDDF-0001-fix-rddf-session-import-path
- add-archive-post-commit-hook-and-force-flag
- add-auto-rfc-from-approve
- add-brainstorm-hardgate-enforcement
- add-change-content-review
- add-cli-coverage-rdd-doctor-roadmap-rdd-hub
- add-config-validation
- add-contract-lint-ci-gate
- add-cross-repo-deps-orchestration
- add-cross-repo-impact-detection
- ... and 233 more

<!-- AUTO-SPRINT-END -->
