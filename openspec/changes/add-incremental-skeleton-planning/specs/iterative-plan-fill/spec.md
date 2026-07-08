# iterative-plan-fill Specification

## Purpose
Define the guide-plan fill phase: progressive content filling of skeleton changes into complete proposals, driven by dependency analysis results.

## MODIFIED Requirements

### Requirement: fill-phase-in-guide-plan
The system SHALL add a `fill` sub-phase to guide-plan, accessible after deps analysis.

The fill phase SHALL:
- Display all changes in `planned` status sorted by deps-recommended execution order
- Allow user to select one or more planned changes for filling
- Fill each selected change by invoking `openspec instructions` for design.md and tasks.md
- Transition the change status from `planned` to `proposed` after successful fill
- Update `proposal-suggestions.md` entry status from `skeleton` to `已完成`

#### Scenario: User enters fill phase
- **WHEN** user selects "填充骨架 change" from guide-plan menu
- **THEN** system displays a table of `planned` status changes with their deps info (blocker, parallel_group, phase)
- **AND** changes with no blockers are listed first (sorted by recommended order)

#### Scenario: User fills a skeleton change
- **WHEN** user selects a planned change "fix-tcgen05-coverage" for filling
- **THEN** system reads the change's `roadmap-meta.yaml` for phase/category
- **AND** reads `proposal-suggestions.md` for the original `description` field (full requirement text)
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

### Requirement: mixed-plan-done-gate
The system SHALL allow guide-plan plan-done to pass with a mix of `planned` and `proposed` status changes.

The relaxed gate SHALL require:
- At least 1 change in `proposed` status (ready for guide-ship)
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

### Requirement: post-archive-fill-suggestion
The system SHALL suggest next fill candidates after guide-ship completes archive of a change.

After archive:
- guide-ship SHALL scan iteration.json for `planned` changes whose blocker has transitioned to `archived`
- If candidates exist, guide-ship SHALL output a suggestion message with the candidate list
- guide-ship SHALL NOT automatically invoke guide-plan fill

#### Scenario: Archive triggers fill suggestion
- **WHEN** guide-ship archives change "A" successfully
- **THEN** system scans iteration.json for changes with blocker="A" and status="planned"
- **AND** if "B" has blocker="A" and status="planned", output: "💡 Change 'B' 的阻塞已解除，建议运行 guide-plan fill 填充"
- **AND** if multiple candidates exist, list all of them

#### Scenario: No candidates after archive
- **WHEN** guide-ship archives change "A" with no dependent planned changes
- **THEN** no fill suggestion is displayed
- **AND** archive output is unchanged from current behavior