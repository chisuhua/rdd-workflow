# skeleton-planning Specification

## Purpose
TBD - created by archiving change add-incremental-skeleton-planning. Update Purpose after archive.
## Requirements
### Requirement: planned-status-lifecycle
The system SHALL support a `planned` status in the change lifecycle, distinct from `proposed`.

The `planned` status SHALL indicate that a change has been registered with a name, phase, category, and minimal proposal (Why + What Changes), but has NOT yet had design.md or tasks.md created.

The lifecycle transition SHALL be: `planned → proposed → in_worktree → review → completed → archived`. A change in `planned` status SHALL NOT be classified `executable`.

#### Scenario: Change created as skeleton
- **WHEN** user invokes `propose --skeleton` for change "fix-tcgen05-coverage"
- **THEN** the system creates `openspec/changes/fix-tcgen05-coverage/` directory
- **AND** writes `.openspec.yaml` (via `openspec new change`)
- **AND** writes `roadmap-meta.yaml` with phase and category
- **AND** writes minimal `proposal.md` containing only Why and What Changes sections
- **AND** sets `iteration.json` status to `planned`
- **AND** does NOT create `design.md` or `tasks.md`

#### Scenario: Skeleton change not classified as executable
- **WHEN** ship-candidate discovery scans active changes
- **THEN** changes without `design.md` SHALL NOT be flagged `executable`
- **AND** only artifact-complete changes (`proposal.md` + `design.md`, `_lib/discover_ship_changes.py`) are eligible for worktree creation

#### Scenario: Skeleton change visible in status
- **WHEN** user invokes `status <change-name>`
- **THEN** skeleton changes SHALL be displayed with status icon `📋` (planned)
- **AND** their `Builder phase:` line SHALL be shown (blocker/parallel_group/conflicts live in iteration.json — use `rddf iteration` for those)

### Requirement: skeleton-minimal-artifacts
The system SHALL define the minimum artifacts for a `planned` skeleton change as: `.openspec.yaml` + `roadmap-meta.yaml` + minimal `proposal.md`.

The minimal `proposal.md` SHALL contain:
- `## Why` section: 1-2 sentences explaining the change motivation
- `## What Changes` section: bullet list of changes with file paths
- SHALL NOT require `## Capabilities`, `## Impact`, or any other sections

#### Scenario: Skeleton proposal passes validation
- **WHEN** a skeleton change has `.openspec.yaml`, `roadmap-meta.yaml`, and `proposal.md` with Why + What Changes
- **THEN** the change is considered valid for `planned` status
- **AND** guide-plan fill phase can locate it
<!-- v4-residue:allow=history -->
```text
> **已退役（2026-11-21）**：本 Requirement 描述的 v3 plan 阶段 fill 行为在 v4 已不存在 —— `list_ready_for_fill`（`_lib/iteration/store.py:446`）只有定义 + 导出 + 单测，**无生产调用方**；`skills/rdd-builder/scripts/phase1_plan.sh` 对 `planned` / `skeleton` **零命中**。原文保留以备查。
```

#### Scenario: Skeleton proposal missing required sections
- **WHEN** a skeleton change has `proposal.md` without Why or What Changes sections
- **THEN** guide-plan fill phase SHALL warn the user
<!-- v4-residue:allow=history -->
- **AND** SHALL prompt for manual completion or skip

### Requirement: skeleton-deps-preanalysis
The system SHALL support dependency analysis on skeleton changes with degraded precision.

When a change is in `planned` status:
- deps SHALL extract scope file paths and ADR references from the minimal proposal.md
- deps SHALL perform file-conflict detection (Axis 1) and ADR dependency detection (Axis 2)
- deps SHALL skip interface dependency detection (Axis 3, requires design.md)
- deps output SHALL mark skeleton changes with `skeleton: true`
- deps SHALL set confidence to `low` for skeleton-based dependency edges

#### Scenario: deps runs on mixed planned+proposed changes
- **WHEN** deps is invoked with 3 changes: 2 `proposed`, 1 `planned`
- **THEN** all 3 changes appear in the dependency graph
- **AND** the `planned` change has `skeleton: true` annotation
- **AND** dependency edges involving the `planned` change are marked `confidence: low`

#### Scenario: deps skips interface axis for skeleton changes
- **WHEN** a `planned` change has no `design.md`
- **THEN** the interface dependency axis is skipped for that change
- **AND** deps output does NOT error or warn about missing design.md
- **AND** a note is appended: "Axis 3 (interface) skipped for skeleton change <name>"

### Requirement: proposal-suggestions-skeleton-status
The system SHALL support a `skeleton` status value in `improvement-suggestions.md` entries, distinct from `待创建`, `进行中`, and `已完成`.

A `skeleton` status SHALL indicate that the change directory has been created with minimal artifacts but has not been filled.

#### Scenario: Entry transitions from 待创建 to skeleton
- **WHEN** user creates a skeleton change from an existing proposal-suggestions entry
- **THEN** the entry's status SHALL change from `待创建` to `skeleton`
- **AND** the entry SHALL remain in improvement-suggestions.md (not removed)

#### Scenario: Entry transitions from skeleton to 已完成
- **WHEN** guide-plan fill completes and creates all artifacts for a skeleton change
<!-- v4-residue:allow=history -->
```text
> **已退役（2026-11-21）**：本 Requirement 描述的 v3 plan 阶段 fill 收尾行为在 v4 已不存在 —— `planned` → `proposed` 的状态迁移在 v4 由 **P0 approval** 完成（`skills/rdd-builder/scripts/phase0_approval.sh:252` 调 `store.set_status(data, name, "proposed")`），而 P1 脚本 `skills/rdd-builder/scripts/phase1_plan.sh` 对 `planned` / `skeleton` **零命中**。（legacy propose 流仍有「待创建 → skeleton」转换（`skills/propose/SKILL.md:515`），但没有 fill 完成的触发器。）原文保留以备查。
```
- **THEN** the entry's status SHALL change from `skeleton` to `已完成`
- **AND** on next propose scan, the entry SHALL be removed from improvement-suggestions.md

