## Why

`CHANGELOG.md` `[Unreleased]` 段最后更新于 `afc369a` (test(reporter): add e2e integration + docs for ADR-0027 change-c)。此后累积 **20+ commits** 未记录：
- `582a6f1` feat(archive): wire close_issues_for_change_hook in lightweight mode
- `61a6d2a` feat(env-check): add gh_available field (15th) for ADR-0027 reporter prereq
- `fdf1f09` test(integration): add 5 end-to-end tests for rddf orchestrate
- `056177c` test(e2e): add temp-project orchestrator tests for realistic scenarios
- `214137b` fix(orchestrate): sweep always reports, even when last subprocess returned 0
- `b64b68e` fix(cli): rename argv → args in cmd_orchestrate + add orchestrate to ALL_SUBCOMMANDS
- `9968b43` merge: Python orchestrator for phase subprocess detection (B1-B4 fix)
- `db355a0` docs: update historical-evolution + ADR-0027 with orchestrator rollout
- `02a1aa8` test(integration): verify RDDF_USE_ORCHESTRATOR env var toggles behavior
- `ed503cd` feat(scripts): integrate orchestrator_entry.sh into 4 phase entry scripts
- `fdebcf6` docs(skills): replace Phase Exit prose in 4 SKILL.md with 3-rule checklist
- `8539bdc` feat(orchestrate): implement stale-trace sweep + GC (B4 fix - centerpiece)
- `3ebe519` feat(post-flow-analysis): add analyze_phase_trace for orchestrator finalize
- `d771201` feat(post-flow-wrap): add single-writer guard for orchestrator coexistence
- `666d258` feat(orchestrator): add bash wrapper + __main__ entry point
- `4be2749` feat(orchestrate): implement --mark-checkpoint + --finalize + trace reuse
- `0f8925d` feat(orchestrate): implement --subprocess with tempfile streams + sanitize
- `388b97c` feat(orchestrate): add trace file management (open/append/read)
- `ff094b5` feat(cli): add rddf orchestrate subcommand skeleton
- `4657834` fix(state-reader,state-schema-check): update tests for v6 migration + isolate env var

**这是 ADR-0027 §1.0 "Detect" 阶段应该 catch 的真实 drift —— reporter 设计目的就是检测此类文档/代码不一致。**

## What Changes

- 在 `CHANGELOG.md` `[Unreleased]` 段新增 3 个主题分组：
  - `### rddf orchestrate (Python orchestrator for phase subprocess detection)` — 11 commits
  - `### env-check gh_available field` — 1 commit
  - `### archive close hook: lightweight mode` — 1 commit
- 同步 `docs/adr/ADR-0027-continuous-evolution-feedback-loop.md` 已记录的 `db355a0` 引用
- 添加 ADR-0027 dogfooding 关联说明：此 change deliberately 暴露 reporter 检测能力

## Capabilities

### New Capabilities
<!-- Doc-only change: no new capability contracts -->

### Modified Capabilities
<!-- Doc-only change: no requirement changes (only changelog text) -->

## Impact

- **Affected files**: `CHANGELOG.md` (添加 ~30 行), `docs/adr/ADR-0027-continuous-evolution-feedback-loop.md` (添加 1 行 cross-reference)
- **No code change**: 0 行 Python/Bash 修改
- **No API change**: 0 公开接口变更
- **No test change**: 0 测试修改
- **Downstream**: git-release 流程 (`openspec validate` 不会因 CHANGELOG 改变而失败)
- **ADR-0027 reporter contract**: 此 change **故意** 暴露 reporter 在 archive 后检测 CHANGELOG drift 的能力
