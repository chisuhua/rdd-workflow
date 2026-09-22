---
id: objective-onboard-new-skill
status: active
created: 2026-09-22
last_revised: 2026-09-22
review_by: 2026-12-21
owner: rdd-planner
priority: P1
manual_deps: []
supersedes: null
theme: 新增 skill 的标准化 onboarding 流程
---

# Objective: objective-onboard-new-skill

## 1. 驱动诊断（Why now）
rdd-workflow 当前有 27+ skills（per AGENTS.md "目录结构" 段），但新增 skill 的 onboarding 流程散落：INSTALL.md / rdd-arch / rdd-planner 各自有零散的 checklist（如 `add-skill-registration-checklist.md` 提案），缺少统一入口。Phase 3 已 ship `rdd-env-bootstrap`（per ADR-0053），新增 skill 的环境引导骨架已就位，缺的是从「idea → proposal → install → first-use」的端到端 onboarding ritual。适用场景：新增任何 skill（含 v0.x 实验）；不适用场景：纯 bugfix / refactor（走 rdd-quick 旁路即可）。

## 2. 目标愿景 + 完成判据
- 新增 1 个 skill 平均时长 ≤ 30 分钟（含 INSTALL + proposal + 第一次跑通）
- 新增 skill 自动注册到 `install.sh` 全局安装清单
- 完成判据（done-when）：
  - [ ] `skill_use("add-skill-onboarding")` 一句话入口可调用
  - [ ] 自动生成 `.rddf/improvements/<skill-name>.md` 5 段草稿（template + 当前 best practice）
  - [ ] 自动跑 `bash skills/<skill>/scripts/install.sh --global` 验证全局可用

## 3. 架构依据
- **ADR-0028** — role-model（每个 skill 都有 role.boundaries）
- **ADR-0042** — planner↔builder feedback channel（onboarding 完成度回写）
- **ADR-0053** — rdd-env-bootstrap（onboarding 编排层）
- `skills/INSTALL.md` — 当前第一入口
- `skills/add-improve/SKILL.md` — proposal 创建入口（可复用）

## 5. 反例
- 不要让 onboarding 自动 commit 到 git（违反 planner 单门控）
- 不要在 onboarding 阶段自动 run `openspec change`（应该是 planner 后续单独决策）
- 不要把 onboarding 与 rdd-quick 混淆——onboarding 是「加新能力」，rdd-quick 是「用现有能力做小改动」

## 9. 目标依赖与 Decision Gate

### 9.1 前置 objective 依赖
无

### 9.2 Go / No-Go Decision Gate
- **Go 判据**（全部 3 条 → 转 completed）：
  - [ ] 1 个真实新增 skill 走通 onboarding ritual 端到端
  - [ ] 平均时长 ≤ 30 分钟（用 stopwatch 测）
  - [ ] 自动注册到全局安装清单

### 9.3 跨 objective 影响
- 受此 objective 影响的下游：未来所有 v0.x 实验 skill 的 onboarding 都走此流程
- 受上游 objective 影响：`objective-bypass-audit-hub-governance`（audit log 设计可参考——onboarding 完成后应自动写 audit event）

### 9.5 DAG snapshot (2026-09-22)

> Snapshot derived at 2026-09-22, regenerate: rddf deps objective-onboard-new-skill

```
(Phase 1 stub) — manually inspect objective-onboard-new-skill §9.1 manual_deps and features linked via objective_ref.
```

## 10. next_sprint_candidates
- [ ] 起草 `skill_use("add-skill-onboarding")` 入口 SKILL.md + 5 段 improvement 草稿
- [ ] 复用 `add-improve/SKILL.md` 的 pre_create_brainstorm_check.sh HARD-GATE
- [ ] 与 `rdd-env-bootstrap` 的 guided-fix 阶段对接（onboarding 完成 → env-bootstrap 跑一次 sanity check）

## 11. 跟踪台账（append-only）
| Sprint | kind | 内容 | Decision/调整 | 原因 |
|--------|------|------|---------------|------|
| sprint-2026-09 | sprint-review | objective 创建 + DAG snapshot 写入 §9.5 | — | PoC #2 for add-objective-tracking（active 小目标，验证台账 append + 候选填充） |
