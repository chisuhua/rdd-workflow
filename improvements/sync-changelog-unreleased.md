# sync-changelog-unreleased

## 背景

`CHANGELOG.md` `[Unreleased]` 段最后更新于 `afc369a` (test(reporter): add e2e integration + docs for ADR-0027 change-c)。
此后累积 **20+ commits** 未记录：
- `feat(archive): wire close_issues_for_change_hook in lightweight mode` (582a6f1)
- `feat(env-check): add gh_available field (15th) for ADR-0027 reporter prereq` (61a6d2a)
- `test(e2e): add temp-project orchestrator tests for realistic scenarios` (056177c)
- `fix(orchestrate): sweep always reports, even when last subprocess returned 0` (214137b)
- `fix(cli): rename argv → args in cmd_orchestrate + add orchestrate to ALL_SUBCOMMANDS` (b64b68e)
- `merge: Python orchestrator for phase subprocess detection (B1-B4 fix)` (9968b43)
- `docs: update historical-evolution + ADR-0027 with orchestrator rollout` (db355a0)
- `test(integration): verify RDDF_USE_ORCHESTRATOR env var toggles behavior` (02a1aa8)
- `feat(scripts): integrate orchestrator_entry.sh into 4 phase entry scripts` (ed503cd)
- `test(integration): add 5 end-to-end tests for rddf orchestrate` (fdf1f09)
- `docs(skills): replace Phase Exit prose in 4 SKILL.md with 3-rule checklist` (fdebcf6)
- `feat(orchestrate): implement stale-trace sweep + GC (B4 fix - centerpiece)` (8539bdc)
- `feat(post-flow-analysis): add analyze_phase_trace for orchestrator finalize` (3ebe519)
- `feat(post-flow-wrap): add single-writer guard for orchestrator coexistence` (d771201)
- `feat(orchestrator): add bash wrapper + __main__ entry point` (666d258)
- `feat(orchestrate): implement --mark-checkpoint + --finalize + trace reuse` (4be2749)
- `feat(orchestrate): implement --subprocess with tempfile streams + sanitize` (0f8925d)
- `feat(orchestrate): add trace file management (open/append/read)` (388b97c)
- `feat(cli): add rddf orchestrate subcommand skeleton` (ff094b5)
- `fix(state-reader,state-schema-check): update tests for v6 migration + isolate env var` (4657834)

**这是 ADR-0027 §1.0 "Detect" 阶段应该 catch 的真实 drift —— reporter 设计目的就是检测此类文档/代码不一致。**

## 范围

- **In Scope**:
  - 在 `CHANGELOG.md` `[Unreleased]` 段新增 3 个分组：
    - `### rddf orchestrate (Python orchestrator for phase subprocess detection)` — 11 commits
    - `### env-check gh_available field` — 1 commit
    - `### archive close hook: lightweight mode` — 1 commit
  - 同步 `docs/adr/ADR-0027-continuous-evolution-feedback-loop.md` 参考列表（arch_drift 已记录 db355a0，但 CHANGELOG 未同步）
  - 不修改 `roadmap.md` / `docs/architecture/*` 历史记录（已正确）
- **Out of Scope**:
  - 不重写 CHANGELOG 历史段（已正确）
  - 不重构 CHANGELOG 结构（保持当前格式）
  - 不追写 git-blame 早期 commits（仅 `[Unreleased]` 段）

## 关键场景

- **GIVEN** `git log --oneline CHANGELOG.md` 显示最后 commit 为 `afc369a`,
  **WHEN** 跑 `git log --oneline --since="2026-08-12"`,
  **THEN** 应返回 ≥ 20 commits 中有 ≥ 20 个未在 CHANGELOG 中记录
- **GIVEN** `CHANGELOG.md [Unreleased]` 段已填充上述 3 个分组,
  **WHEN** 跑 `git diff --stat CHANGELOG.md`,
  **THEN** diff 显示新增行数 ≥ 30

## 技术约束

- MUST 保持当前 CHANGELOG 格式（与 ADR-0027 段对齐）
- MUST NOT 删除或重写 `[v3.0.0]` 历史段
- SHOULD 按主题分组（orchestrator / env-check / archive），不按 commit 顺序
- MUST 同步 ADR-0027 已记录的 `db355a0` 引用

## 验收标准

- `CHANGELOG.md [Unreleased]` 段新增 ≥ 30 行
- 3 个 feature 分组（orchestrator / env-check / archive）
- 20+ commits 全部覆盖
- `git diff CHANGELOG.md` 0 冲突
- `python3 -m pytest tests/unit/` 0 regression
- `bash tests/scripts/report_regression.sh` 0 新增失败

## 优先级

P1 — 文档 drift 影响下游用户 + 测试 ADR-0027 reporter 检测能力

## 估计

30-60 分钟

## Dogfooding 关联

此 change 是 **ADR-0027 完整链路 dogfooding** 的故意 planted drift：
1. 提交此 change 之前 → reporter 应在 archive 后报告 "CHANGELOG drift: N commits unrecorded"
2. 提交此 change 之后 → reporter 不应再 catch（gap 已修复）
3. 验证 reporter 的 Detect → Buffer → Report → Triage → Close 完整链路
