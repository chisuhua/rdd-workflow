---
id: objective-bypass-audit-hub-governance
status: deferred
created: 2026-09-22
last_revised: 2026-09-22
review_by: 2026-12-21
owner: rdd-planner
priority: P2
manual_deps: []
supersedes: null
theme: 统一 bypass audit + hub federation governance
---

# Objective: objective-bypass-audit-hub-governance

## 1. 驱动诊断（Why now）
2026-08-28 HANDOFF.md Phase D 评估：bypass-audit-mechanism（统一 audit log）维持 deferred 决策（per `feat-fix-archive-gaps-v2` §22），理由是「价值清晰但当前 SKIP 使用频率低，留作 v3.2 follow-up」。该决议与 hub-federation governance 共享 audit log 设计，因此两个治理项被同步推迟。2026-09-22 重新评估：v3.2 启动窗口临近（per AGENTS.md v4.0+ 时间线），需先把 governance 骨架就位才能让 Wave 3（ADR-0078 Model-RSI pilot）的 audit 链可追溯。适用场景：cross-repo change 含 bypass-audit 触发的治理；不适用场景：纯本地 change（已有 rdd-doctor 巡检足够）。

## 2. 目标愿景 + 完成判据
- v3.2 release 时 bypass-audit 月度触发 ≤ 1 次
- Hub issue → spoke change → spoke archive 全链路 audit trail 可追溯
- 1 个真实 cross-repo change 走完完整路径作为验证
- 完成判据（done-when）：
  - [ ] `.bypass-audit.jsonl` 与 `.cross-repo-pending.json` 共享 schema 字段定义
  - [ ] `rddf doctor --category bypass-audit` 输出包含 hub 路径统计
  - [ ] 1 个真实 cross-repo change 走通完整 audit 链

## 3. 架构依据
- **ADR-0030** — hub-spoke federation 协议
- **ADR-0031** — cross-repo human-in-loop 审批
- **ADR-0053** — rdd-env-bootstrap orchestrator（hub 端引导式修复）
- `docs/spoke-system-prompt.md` — 联邦协议注入规范
- `feat-fix-archive-gaps-v2` §22 — 原始 deferral 决议

## 5. 反例
- 不要把 bypass-audit 与 hub-federation 合并成单 ADR（违反 ADR-0048 scope discipline，会重复 Wave 3 hard removal 教训）
- 不要在 objective §6 写执行指令（违反 planner/builder 边界）
- 不要假设 bypass-audit 高频使用就能 justify 提前实施——事实是「使用频率低」（per 原始 deferral 理由）

## 9. 目标依赖与 Decision Gate

### 9.1 前置 objective 依赖
无（独立 objective）

### 9.2 Go / No-Go Decision Gate
- **Go 判据**（满足全部 3 条 → 转 completed）：
  - [ ] `.bypass-audit.jsonl` 与 `.cross-repo-pending.json` schema 统一（schema 版本号一致）
  - [ ] `rddf doctor --category bypass-audit` 输出跨 hub 路径统计
  - [ ] 1 个真实 cross-repo change 走通完整 audit 链（不是 mock）

### 9.3 跨 objective 影响
- 受此 objective 影响的下游：`objective-onboard-new-skill`（audit log 设计可参考）
- 受上游 objective 影响：无

## 10. next_sprint_candidates
N/A — objective 维持 v3.2 deferred 决策（per `feat-fix-archive-gaps-v2` §22 + HANDOFF.md Phase D）；待 hub-federation governance 立项后重新评估激活窗口。

## 11. 跟踪台账（append-only）
| Sprint | kind | 内容 | Decision/调整 | 原因 |
|--------|------|------|---------------|------|
| sprint-2026-09 | deferral-rationale | 维持 v3.2 deferred 决策（per feat-fix-archive-gaps-v2 §22） | 推迟至 hub-federation 立项后激活 | 跨 sprint 治理依赖 |
| sprint-2026-09 | sprint-review | objective 创建 | — | PoC #1 for add-objective-tracking |
