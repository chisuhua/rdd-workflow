# plan-intake-bootstrap Specification

## Purpose
TBD - created by archiving change harden-plan-intake-bootstrap-and-design-gate-tests. Update Purpose after archive.
## Requirements
### Requirement: plan-intake-detects-missing-design-handoff

> **RETIRED (2026-11-20, fix-spec-residue-batch2-dead-intake)** —— 对象 `plan_intake.sh` 已不存在（v4 无此脚本）。它检测的 `.design-handoff.json` 在 v4 亦非主 handoff —— v4 的 handoff 是 `.planner-handoff.json`（`rdd-planner/scripts/planner_stage_exit.sh` 写、`rdd-builder/scripts/phase1_plan.sh` 读）；`_lib/recommender.py:160` 仅作迁移提示读取旧文件。
> 保留原文与 Scenario 作为历史记录。


The plan phase intake (`plan_intake.sh`) MUST detect the absence of `.design-handoff.json` and exit non-zero with a guidance message, not silently passing.

#### Scenario: missing design-handoff

- WHEN a user runs `guide-plan` without first running `guide-design` (no `.rddf/state/.design-handoff.json` exists)
<!-- v4-residue:allow=history -->
- THEN `plan_intake.sh` exits with non-zero status
- AND outputs a guidance message: "Please run `guide-design` first"
<!-- v4-residue:allow=history -->
- AND does NOT silently create changes

### Requirement: plan-intake-tolerates-v2-handoff-missing-field

> **RETIRED (2026-11-20, fix-spec-residue-batch2-dead-intake)** —— 对象 `plan_intake.sh` 已不存在，且本条依赖的 `changes_pre_created` 字段**无活消费者** —— 三个消费函数（`is_design_pre_created` / `get_design_pre_created_label` / `get_fill_artifacts_for`）全仓 0 命中，字段仅存于 `_lib/schemas/design_handoff_schema.json` 作历史契约。
> 保留原文与 Scenario 作为历史记录。


The plan phase intake MUST treat `.design-handoff.json` files with `version: 2` but missing the `changes_pre_created` field as v1-compatible (treat `changes_pre_created` as empty array) with a warning log.

#### Scenario: v2 handoff missing changes_pre_created

- WHEN `.design-handoff.json` has `version: 2` but lacks `changes_pre_created`
- THEN `plan_intake.sh` proceeds with empty `changes_pre_created: []`
- AND logs a warning: "v2 handoff missing changes_pre_created, treating as v1"
- AND does NOT block plan phase entry

### Requirement: plan-intake-detects-stale-handoff

> **RETIRED (2026-11-20, fix-spec-residue-batch2-dead-intake)** —— 对象 `plan_intake.sh` 已不存在；「30 天 stale 检测」在 v4 **无等价承接** （`_lib/cleanup_plan_handoff.py` 清的是 `.planner-handoff.json` 的旧记录，不是 stale 判定）。
> 保留原文与 Scenario 作为历史记录。


The plan phase intake MUST detect stale `.design-handoff.json` (where `design_complete_at` is more than 30 days old) and emit a warning without blocking.

#### Scenario: stale design-handoff

- WHEN `.design-handoff.json` `design_complete_at` is more than 30 days ago
- THEN `plan_intake.sh` outputs "handoff is stale, consider re-running guide-design"
<!-- v4-residue:allow=history -->
- AND continues with plan phase execution (no block)

### Requirement: plan-intake-detects-empty-changes-pre-created

> **RETIRED (2026-11-20, fix-spec-residue-batch2-dead-intake)** —— 对象 `plan_intake.sh` 已不存在，且本条依赖的 `changes_pre_created` 字段无活消费者（同 `plan-intake-tolerates-v2-handoff-missing-field` 条）。
> 保留原文与 Scenario 作为历史记录。


The plan phase intake MUST detect `changes_pre_created: []` (empty array, design phase produced no changes) and exit non-zero with guidance.

#### Scenario: empty changes_pre_created

- WHEN `.design-handoff.json` has `changes_pre_created: []`
- THEN `plan_intake.sh` exits non-zero
- AND outputs "no proposals to plan, exiting. Run `guide-design` first to create proposals"
<!-- v4-residue:allow=history -->

### Requirement: plan-intake-reports-interrupted-trace

> **RETIRED (2026-11-20, fix-spec-residue-batch2-dead-intake)** —— 对象 `plan_intake.sh` 已不存在；本条依赖的 `finalize_at` 字段 **全仓 0 命中** ⇒ v4 零承接。
> 保留原文与 Scenario 作为历史记录。


The plan phase intake MUST detect interrupted traces (missing `finalize_at` field in `.rddf/state/trace/*.json`) and emit a warning without blocking.

#### Scenario: interrupted trace

- WHEN `.rddf/state/trace/<phase>.json` lacks `finalize_at`
- THEN `plan_intake.sh` outputs "interrupted trace from <timestamp>, run `rddf orchestrate show <phase>` to triage"
- AND does NOT block plan phase entry

### Requirement: plan-intake-marks-abandoned-sessions

> **RETIRED (2026-11-20, fix-spec-residue-batch2-dead-intake)** —— 对象 `plan_intake.sh` 已不存在。用户可见子目标（把废弃 session 标 orphan）由 `rddf sessions gc` 承接 —— `_lib/cli/sessions_cmd.py:17,381` 以 **30 分钟 heartbeat 超时**判 orphaned，而本条判据是 `end_reason: user-abandoned-via-guide-design-transition` 枚举值 ⇒ 判据不同，非等价承接。
> 保留原文与 Scenario 作为历史记录。


The plan phase intake MUST detect abandoned rddf-sessions in `.rddf/state/sessions.json` and mark them as orphans without blocking.

#### Scenario: abandoned session

- WHEN `sessions.json` contains a session with `end_reason: user-abandoned-via-guide-design-transition`
- THEN `plan_intake.sh` marks the session as orphan
- AND outputs a hint to run `rddf-session archive-history` for cleanup
- AND does NOT block plan phase entry

### Requirement: plan-intake-skip-propose-for-design-precreated

> **RETIRED (2026-11-20, fix-spec-residue-batch2-dead-intake)** —— 对象 `plan_intake.sh` 已不存在，且本条依赖的 `changes_pre_created` 字段无活消费者（同 `plan-intake-tolerates-v2-handoff-missing-field` 条）。
> 保留原文与 Scenario 作为历史记录。


The plan phase MUST skip the propose step for changes listed in `.design-handoff.json::changes_pre_created`.

#### Scenario: design-pre-created change

- WHEN `improvement-approved.md` lists `name=X` AND `.design-handoff.json::changes_pre_created` contains `X`
- THEN `guide-plan` Phase 2 (propose) does NOT call `propose --create X`
<!-- v4-residue:allow=history -->
- AND `guide-plan` Phase 2.5 (fill) writes `design.md` and `tasks.md` for `X`
<!-- v4-residue:allow=history -->
- AND `guide-plan` does NOT modify `proposal.md` (Path A invariant)
<!-- v4-residue:allow=history -->

### Requirement: design-content-review-characterization-baseline

The pytest unit tests for `propose_quality_check.py::run_design_checks` MUST lock the **current behavior** as a characterization baseline, regardless of whether the current behavior is correct.

#### Scenario: characterization test on known edge case

- WHEN a test improvement file with head field `**类型**` missing is processed by `run_design_checks`
- THEN the characterization test asserts whatever the CURRENT behavior is (pass or fail)
- AND the test is marked with `@pytest.mark.characterization`
- AND the test does NOT fail or expect a specific outcome (only documents reality)

### Requirement: plan-intake-stale-handoff-with-empty-changes-folder

> **RETIRED (2026-11-20, fix-spec-residue-batch2-dead-intake)** —— 对象 `plan_intake.sh` 已不存在；本条同时依赖「30 天 stale 检测」（v4 无等价）与 `changes_pre_created`（无活消费者）⇒ 两个前提都失效。
> 保留原文与 Scenario 作为历史记录。


The plan phase intake MUST handle the case where `.plan-handoff.json` references a `current_change` that has been archived while `openspec/changes/` is empty.

#### Scenario: stale plan-handoff referencing archived change

- WHEN `.plan-handoff.json::current_change = "some-archived-change"` AND `openspec/changes/` has no such directory
- THEN `plan_intake.sh` detects the inconsistency
- AND emits a warning suggesting re-running `guide-plan` from fresh state
<!-- v4-residue:allow=history -->
- AND does NOT silently proceed with stale state

