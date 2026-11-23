# agent-interface-contracts Specification

## Purpose
TBD - created by archiving change fix-agent-interface-contracts. Update Purpose after archive.

## Requirements

### Requirement: stage-recommendation-reads-v4-handoffs

Stage recommendation MUST be derived from `.rddf/state/.planner-handoff.json`, which is the authoritative v4 planner handoff.

A recommendation of `rdd-planner` MUST be produced when `.arch-handoff.json` exists but `.planner-handoff.json` does not.

A corrupt (unparsable) `.planner-handoff.json` MUST be treated as "planner not complete".

#### Scenario: arch done, planner not yet run (all three consumers)

- GIVEN `.rddf/state/.arch-handoff.json` exists with `adr_count >= 1`
- AND `.rddf/state/.planner-handoff.json` does NOT exist
- WHEN `scan_state <repo>`, `guide_cmd._scan_state(<repo>)`, and `synthesize(<repo>)` run
- THEN all three recommend `rdd-planner`

#### Scenario: planner done

- GIVEN `.arch-handoff.json` and `.planner-handoff.json` both exist
- WHEN any of the three consumers runs
- THEN the recommendation is `rdd-builder`
- AND the reason does not contain `设计阶段`

#### Scenario: states without an arch handoff keep their pre-existing behaviour (out of scope)

- GIVEN `.planner-handoff.json` exists but `.arch-handoff.json` does NOT
- WHEN the three consumers run
- THEN each retains its pre-existing behaviour for that state
- AND the known pre-existing divergence remains: `scan-state.sh` and `guide_cmd._scan_state` recommend `rdd-builder`, while `workflow_synthesizer._decision_tree` short-circuits to `rdd-arch`

#### Scenario: v3 handoff states keep their pre-existing behaviour (out of scope)

- GIVEN the effective marker is a v3 handoff (`.plan-handoff.json` / `.design-handoff.json`)
- WHEN the three consumers run
- THEN each retains its pre-v4 behaviour for that state
- AND the known pre-existing divergence remains: `scan-state.sh` and `guide_cmd._scan_state` cross-validate a v3 `.plan-handoff.json` against the filesystem and can recommend `rdd-arch` for a stale handoff, while `workflow_synthesizer._decision_tree` recommends `rdd-builder`

#### Scenario: corrupt planner handoff is not treated as complete

- GIVEN `.planner-handoff.json` contains truncated/invalid JSON
- WHEN any consumer runs
- THEN the recommendation is `rdd-planner`
- AND the corrupt file is not silently accepted as planner-complete

### Requirement: stage-detection-marks-unverified-handoffs

Handoff JSON validity MUST be verified before a handoff is treated as stage-complete. The bash consumer parses handoff JSON through `python3`; when `python3` is unavailable it cannot verify validity, so it MUST NOT present the result as an authoritative stage decision. It MUST either reject the handoff or mark the recommendation explicitly as non-authoritative.

A handoff file whose top-level JSON value is not an object MUST NOT be treated as a valid handoff (the Python consumers require a dict).

#### Scenario: handoff validity cannot be verified

- GIVEN `python3` is NOT available
- WHEN `scan_state` evaluates a handoff file
- THEN the recommendation carries an explicit non-authoritative marker
- AND the result is not presented as a verified stage decision

#### Scenario: handoff content is not a JSON object

- GIVEN `.planner-handoff.json` contains a JSON array
- WHEN any consumer evaluates it
- THEN it is NOT treated as a valid planner handoff

### Requirement: stage-recommendation-consumers-agree

The three stage-recommendation consumers (`scan-state.sh::scan_state`, `guide_cmd._scan_state`, `workflow_synthesizer._decision_tree`) MUST agree on the recommended stage for the same project in every v4 planner-handoff state **where `.rddf/state/.arch-handoff.json` exists**.

They MUST agree on the recommended **stage**; the reason text is implementation-specific and is not required to be byte-identical.

#### Scenario: all three consumers agree in a v4 state

- GIVEN `.arch-handoff.json` exists with `adr_count >= 1`
- AND `.planner-handoff.json` does NOT exist
- WHEN `scan_state <repo>`, `guide_cmd._scan_state(<repo>)`, and `synthesize(<repo>)` run
- THEN all three recommend `rdd-planner`

#### Scenario: all three consumers agree when the planner handoff is corrupt

- GIVEN `.arch-handoff.json` exists and `.planner-handoff.json` contains invalid JSON
- WHEN the three consumers run
- THEN all three recommend `rdd-planner`

### Requirement: active-change-detection-from-filesystem

Active-change detection MUST be derived from `openspec/changes/*/` excluding `archive/`. It MUST NOT depend on an `active_changes` field, because `planner_handoff_schema.json` does not define one (its `required` list is `schema / version / owner / planner_complete_at / current_sprint / recommended_route`).

#### Scenario: active change detected from filesystem

- GIVEN `.planner-handoff.json` exists WITHOUT an `active_changes` key
- AND `openspec/changes/my-change/` exists (not under `archive/`)
- WHEN `rddf guide` runs
- THEN the recommendation reason does NOT claim "no active change"

### Requirement: v3-handoff-fallback-ordering

v3 handoff files (`.design-handoff.json`, `.plan-handoff.json`) MAY be read only as a legacy fallback, only when `.planner-handoff.json` is absent, and MUST emit a `legacy` warning.

The legacy check MUST be evaluated **before** the v4 arch-done branch when selecting the effective marker; otherwise the arch-done branch matches first and the fallback can never run.

The legacy check MUST NOT short-circuit the remaining branches (worktree / roadmap / proposal detection).

#### Scenario: v3 legacy project still supported

- GIVEN only `.plan-handoff.json` (or `.design-handoff.json`) exists, and `.planner-handoff.json` does NOT
- WHEN any consumer runs
- THEN the recommendation is `rdd-builder`
- AND the output contains `legacy`

#### Scenario: v3 legacy project keeps its downstream branches

- GIVEN only `.plan-handoff.json` exists (v3 plan semantics)
- AND the project has a worktree with incomplete tasks
- WHEN a consumer runs
- THEN it evaluates the worktree branch
- AND it does NOT stop at the legacy check

#### Scenario: v3 design handoff and v3 plan handoff denote different stages

- GIVEN only `.design-handoff.json` exists (v3 design semantics: design reviewed, changes not generated yet)
- WHEN a consumer runs
- THEN the recommendation reason says change generation is next
- AND it does NOT report a "plan-handoff leftover" cleanup state

#### Scenario: v4 project is not misclassified as legacy

- GIVEN `.arch-handoff.json` and `.planner-handoff.json` both exist
- WHEN any consumer runs
- THEN the output does not contain `legacy`

### Requirement: status-exposes-builder-phase

`_lib/cli/status_cmd.py::_mode_a` MUST render a `BUILDER` column (in the **active changes** table) populated from `.rddf/state/builder/<name>.json::current_phase`. The column MUST NOT be named `PHASE`, and MUST live in a **separate table** from the 改进提案 table's `PHASE` column (the two tables are rendered separately, so the names do not collide). Archived changes are not listed in the active changes table at all; for an archived change `cmd_status_detail` MUST display `-` in its `Builder phase:` line. Missing or unparsable builder state MUST degrade to `-` without raising. `cmd_status_detail` MUST print a `Builder phase:` line.

#### Scenario: builder column populated for an active change

- GIVEN `.rddf/state/builder/my-change.json` contains `"current_phase": "phase-2"`
- AND `openspec/changes/my-change/` exists on disk
- WHEN `rddf status` runs
- THEN the `BUILDER` column shows `phase-2` for `my-change`

#### Scenario: archived change shows dash

- GIVEN a change is archived (its directory lives under `openspec/changes/archive/<date>-<name>/`) and still has `.rddf/state/builder/<name>.json`
- WHEN `rddf status <name>` runs
- THEN the `Builder phase:` line shows `-`

#### Scenario: missing state degrades gracefully

- GIVEN no builder state file for an on-disk change
- WHEN `rddf status` runs
- THEN the `BUILDER` column shows `-`
- AND the command exits 0

#### Scenario: corrupt state degrades gracefully

- GIVEN the builder state file contains invalid JSON
- WHEN `rddf status` runs
- THEN the `BUILDER` column shows `-`
- AND the command does not raise

#### Scenario: existing single-change entry point unchanged

- GIVEN `rddf builder status <change>` is used
- WHEN the change has a builder state
- THEN it still prints `phase: <current_phase>` (no regression)

### Requirement: phase2-execute-does-not-gate-on-commit

`skills/rdd-builder/scripts/phase2_execute.sh` MUST NOT gate Phase 2 on the git working-tree state. The former repository-wide `git status --porcelain` check is removed. No new environment variable is introduced for bypassing a commit check.

Commit semantics for a change remain enforced upstream by `_lib/archive.sh::check_worktree_commits` before archive.

#### Scenario: unrelated dirty file does not block Phase 2

- GIVEN the change's artifacts are committed
- AND an unrelated file (e.g. `.rddf/state/role.json`) is modified
- WHEN `phase2_execute.sh <change>` runs
- THEN it proceeds past the former gate location

#### Scenario: uncommitted artifacts do not block Phase 2

- GIVEN `openspec/changes/<name>/tasks.md` has unstaged modifications
- WHEN `phase2_execute.sh <change>` runs
- THEN it proceeds (no exit 3 from a commit gate)

#### Scenario: change artifacts are carried into the worktree

- GIVEN the change's artifacts exist in the main repo but are not committed
- AND `phase2_execute.sh` runs in `worktree` execution mode
- WHEN the worktree is created
- THEN `openspec/changes/<name>/` and `.rddf/plans/<name>.md` are present inside the worktree

#### Scenario: carry-over does not create a nested directory

- GIVEN the change's artifacts ARE committed, so the new worktree already contains `openspec/changes/<name>/`
- WHEN the carry-over runs
- THEN the worktree contains no `openspec/changes/<name>/<name>/` sub-directory

#### Scenario: carry-over is skipped when source and target are the same location

- GIVEN worktree creation failed and execution falls back to the main repo
- WHEN the carry-over runs
- THEN it MUST skip the copy instead of aborting Phase 2

#### Scenario: archive-time commit gate still applies

- GIVEN `openspec/<name>` branch has no commits ahead of the default branch
- WHEN `check_worktree_commits <name>` runs
- THEN it returns non-zero
- AND `rddf archive <name>` refuses to merge
