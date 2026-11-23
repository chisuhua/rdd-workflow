# iterative-plan-fill Specification

## Purpose
TBD - created by archiving change add-incremental-skeleton-planning. Update Purpose after archive.
## Requirements
### Requirement: fill-phase-in-guide-plan
<!-- v4-residue:allow=history -->

> **PARTIAL (2026-11-20, fix-spec-residue-batch2-dead-intake)** —— 部分退役。**保留**：`fill` 阶段「为 skeleton change 补 `tasks.md`」这一子句 —— v4 由 `skills/rdd-builder/scripts/phase1_plan.sh` 承担（`SKILL.md:17`「design.md and tasks.md are P1 fill outputs」，但 `:53` 澄清 `design.md` 实由执行 agent 撰写）。**退役**其余子句：① 「Display all changes in `planned` status sorted by deps-recommended order」（v4 P1 是单 change，`phase1_plan.sh:6` `CHANGE_NAME="${1:-}"`）；② 「Allow user to select one or more planned changes」（同上，无多选）；③ 「invoking `openspec instructions` for **design.md and tasks.md**」（design.md 不在 P1）；④ 「Transition the change status from `planned` to `proposed`」（v4 用 builder state machine，无该状态迁移）；⑤ 「Update `improvement-suggestions.md` entry status from `skeleton` to `已完成`」（v4 的 `sync_suggestions` 用 `approved`/`completed`/`deferred`/`rejected`，`skeleton` 不是 suggestions 状态值）。
> 保留原文与 Scenario 作为历史记录（被退役的子句见上）。

The system SHALL add a `fill` sub-phase to guide-plan, accessible after deps analysis.
<!-- v4-residue:allow=history -->

The fill phase SHALL:
- Display all changes in `planned` status sorted by deps-recommended execution order
- Allow user to select one or more planned changes for filling
- Fill each selected change by invoking `openspec instructions` for design.md and tasks.md
- Transition the change status from `planned` to `proposed` after successful fill
- Update `improvement-suggestions.md` entry status from `skeleton` to `已完成`

#### Scenario: User enters fill phase
- **WHEN** user selects "填充骨架 change" from guide-plan menu
<!-- v4-residue:allow=history -->
- **THEN** system displays a table of `planned` status changes with their deps info (blocker, parallel_group, phase)
- **AND** changes with no blockers are listed first (sorted by recommended order)

#### Scenario: User fills a skeleton change
- **WHEN** user selects a planned change "fix-tcgen05-coverage" for filling
- **THEN** system reads the change's `roadmap-meta.yaml` for phase/category
- **AND** reads `improvement-suggestions.md` for the original `description` field (full requirement text)
- **AND** uses `description` as context for `openspec instructions design --change "fix-tcgen05-coverage"`
- **AND** creates `design.md` and `tasks.md` sequentially
- **AND** updates iteration.json status to `proposed`
- **AND** commits all new artifacts

#### Scenario: Fill fails gracefully
- **WHEN** openspec instructions fails for a skeleton change
- **THEN** fill SHALL skip that change and continue to the next
- **AND** the skipped change remains in `planned` status
- **AND** an error message is displayed with the failure reason

### Requirement: fill-trigger-from-deps

> **RETIRED (2026-11-20, fix-spec-residue-batch2-dead-intake)** —— 对象 `guide-plan` 的 fill 推荐机制已不存在。`skills/rdd-builder/scripts/phase1_5_deps.sh` 对 `fill` / `planned` / `recommend` **零命中** —— 它是单 change 的 strict-deps gate + execution_mode 决策，**没有**「展示全部 planned changes 的 fill 推荐顺序 / blocked-by 状态」的行为。本条 Scenario 里「`guide-ship` archive hook SHALL suggest calling guide-plan fill」同样无承接 （`wave_scheduler_post_archive` 存在但 v4 archive 流程未接线，见 `post-archive-fill-suggestion` 条）。
<!-- v4-residue:allow=history -->
> 保留原文与 Scenario 作为历史记录。

The system SHALL recommend fill candidates based on deps output.

Changes that are eligible for fill SHALL satisfy ALL of:
- Status is `planned`
- No blocker in `planned` or `in_worktree` status (all blockers are `completed` or `archived`)

#### Scenario: deps-recommended fill order
- **WHEN** deps analysis shows: A blocks B, B blocks C, all in `planned` status
- **THEN** fill phase SHALL recommend filling A first
- **AND** B and C SHALL show "blocked by A" with A's current status

#### Scenario: Blocker cleared after archive
- **WHEN** change A is archived (completed → archived) and B is `planned` with blocker=A
- **THEN** B SHALL appear as "ready to fill" (no active blockers)
- **AND** guide-ship archive hook SHALL suggest calling guide-plan fill
<!-- v4-residue:allow=history -->

### Requirement: mixed-plan-done-gate

> **RETIRED (2026-11-20, fix-spec-residue-batch2-dead-intake)** —— v4 的 `plan_done` gate（`_lib/gate.py:378`）检查 `artifacts_complete`（proposal/design/tasks 三件齐全）+ `openspec_validate`，**没有**「允许 planned 与 proposed 状态混合通过」这一判据 ⇒ 无等价承接。
> 保留原文与 Scenario 作为历史记录。

The system SHALL allow guide-plan plan-done to pass with a mix of `planned` and `proposed` status changes.
<!-- v4-residue:allow=history -->

The relaxed gate SHALL require:
- At least 1 change in `proposed` status (ready for guide-ship)
<!-- v4-residue:allow=history -->
- All `proposed` changes have 3 artifacts committed (proposal.md, design.md, tasks.md)
- All `planned` changes have skeleton artifacts committed (.openspec.yaml, roadmap-meta.yaml, minimal proposal.md)
- Deps analysis has been run and covers all changes (both planned and proposed)

#### Scenario: Mixed state passes plan-done
- **WHEN** project has 2 `proposed` changes (full artifacts committed) and 3 `planned` changes (skeletons committed)
- **THEN** plan-done gate passes
- **AND** handoff output shows: "planned=3, proposed=2"

#### Scenario: Only planned changes fails plan-done
- **WHEN** project has only `planned` changes and zero `proposed` changes
- **THEN** plan-done gate fails
- **AND** message: "至少需要一个 proposed 状态 change 才能交接给 guide-ship"
<!-- v4-residue:allow=history -->

### Requirement: post-archive-fill-suggestion

> **RETIRED (2026-11-20, fix-spec-residue-batch2-dead-intake)** —— archive 后「扫描 iteration.json 找 blocker 已解除的 planned change 并建议 fill」的行为**无承接**：`_lib/wave_scheduler_hooks.sh:11` 的 `wave_scheduler_post_archive` 虽存在，但 **v4 archive 流程未接线** —— `skills/rdd-builder/scripts/phase3_archive.sh:277` 只调 `post_archive_cleanup`，全仓除定义与 bats 直测外零调用 ⇒ 用户可见行为暂无承接。
> 保留原文与 Scenario 作为历史记录。

The system SHALL suggest next fill candidates after guide-ship completes archive of a change.
<!-- v4-residue:allow=history -->

After archive:
- guide-ship SHALL scan iteration.json for `planned` changes whose blocker has transitioned to `archived`
<!-- v4-residue:allow=history -->
- If candidates exist, guide-ship SHALL output a suggestion message with the candidate list
<!-- v4-residue:allow=history -->
- guide-ship SHALL NOT automatically invoke guide-plan fill
<!-- v4-residue:allow=history -->

#### Scenario: Archive triggers fill suggestion
- **WHEN** guide-ship archives change "A" successfully
<!-- v4-residue:allow=history -->
- **THEN** system scans iteration.json for changes with blocker="A" and status="planned"
- **AND** if "B" has blocker="A" and status="planned", output: "💡 Change 'B' 的阻塞已解除，建议运行 guide-plan fill 填充"
<!-- v4-residue:allow=history -->
- **AND** if multiple candidates exist, list all of them

#### Scenario: No candidates after archive
- **WHEN** guide-ship archives change "A" with no dependent planned changes
<!-- v4-residue:allow=history -->
- **THEN** no fill suggestion is displayed
- **AND** archive output is unchanged from current behavior

### Requirement: intake 消费 changes_pre_created

> **RETIRED (2026-11-20, fix-spec-residue-batch2-dead-intake)** —— 本条依赖的 `changes_pre_created` 字段**无活消费者** —— 三个消费函数（`is_design_pre_created` / `get_design_pre_created_label` / `get_fill_artifacts_for`）与 `plan_intake.sh` 全仓 0 命中，字段仅存于 `_lib/schemas/design_handoff_schema.json` 作历史契约（同第一批 `skills-and-handoff.md` 的 Path A 结论）。
> 保留原文与 Scenario 作为历史记录。


guide-plan SHALL read `changes_pre_created` from the design-handoff (v2) and skip change creation for those names, proceeding directly to roadmap-meta backfill and fill. Re-creation of a pre-created change MUST NOT occur (idempotent).
<!-- v4-residue:allow=history -->

#### Scenario: 预建 change 跳过创建

- GIVEN design-handoff v2 contains `changes_pre_created: ["foo"]` and `openspec/changes/foo/` exists with a complete proposal.md
- WHEN guide-plan runs its propose phase
<!-- v4-residue:allow=history -->
- THEN `foo` is marked as design-pre-created and no new change is created for it
- AND roadmap-meta backfill (`update_roadmap_meta`) still runs for `foo`

### Requirement: fill 范围收缩为 specs/design/tasks

> **RETIRED (2026-11-20, fix-spec-residue-batch2-dead-intake)** —— v4 的 P1（`skills/rdd-builder/scripts/phase1_plan.sh`）**只补 `tasks.md`** —— `skills/rdd-builder/SKILL.md:53` 明确「`design.md` 不由本 skill 生成，由执行该 change 的 agent 撰写」⇒ 与「fill 创建 design.md + tasks.md + specs/」不等价。
> 保留原文与 Scenario 作为历史记录。


The fill phase SHALL only create `specs/`, `design.md`, and `tasks.md` for changes whose `proposal.md` is already complete (as reported by `openspec status --change <name> --json` showing the proposal artifact as done). Fill MUST NOT rewrite an existing complete `proposal.md`.

#### Scenario: 完整 proposal 不被重写

- GIVEN a change pre-created in the design phase with a complete `proposal.md`
- WHEN the fill phase processes it
- THEN fill creates only `design.md` and `tasks.md` (and specs deltas where applicable)
- AND the existing `proposal.md` content is unchanged

