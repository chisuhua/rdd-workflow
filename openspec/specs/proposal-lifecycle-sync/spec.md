# proposal-lifecycle-sync Specification

## Purpose

Ensure that `improvement-approved.md` stays in sync with the actual approval and archive lifecycle of OpenSpec changes. After a change is approved, every stage (design → plan → ship → archive) MUST consistently reflect the change's status in `improvement-approved.md`. The current implementation has 3 synchronization gaps that cause archived changes to remain visible as "pending" in the dashboard.

This delta closes the gaps by:
1. Adding `git add improvement-approved.md` to `approve_proposal.sh` so design-phase writes are never lost.
2. Adding a `compgen -G "openspec/changes/archive/[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]-<name>"` fallback to `mark_approved_completed <name>` so archive-phase can recover from missing entries in the main table.
3. Hardening the dashboard's pending filter so archived changes are never reported as pending, even if `improvement-approved.md` is missing their entry.

## Requirements

### Requirement: `approve_proposal.sh` MUST stage `improvement-approved.md` before returning

> **RETIRED (2026-11-20, retire-spec-musts-pointing-at-retired-objects)** —— `skills/guide-design/scripts/approve_proposal.sh` 已随 ADR-0043 / ADR-0044 不存在；实测 `skills/rdd-builder/scripts/phase0_approval.sh` 对 `git add` / `improvement-approved` **0 命中** ⇒ staging 纪律无承接。注：写文件函数 `append_approved` 仍存于 `_lib/state.sh:156`。保留原文与 Scenario 作为历史记录。
<!-- v4-residue:allow=history -->

The `skills/guide-design/scripts/approve_proposal.sh` script MUST execute `git add improvement-approved.md` after the file is written (whether by `append_approved` or as a fallback) and BEFORE the script exits successfully. The git add call MUST run failure-fast: if the staging fails, the script MUST exit non-zero with a clear error message.
<!-- v4-residue:allow=history -->

modifies: proposal-lifecycle-sync

The script SHALL output a confirmation line `git add improvement-approved.md done` so the AI orchestrator can verify the staging succeeded.

modifies: proposal-lifecycle-sync

#### Scenario: Normal approval — improvement-approved.md is staged

- **GIVEN** working tree is clean
- **AND** `approve_proposal.sh <name> <priority> <project_root>` runs
- **WHEN** the script writes a new row to `improvement-approved.md` main table
- **THEN** the script executes `git add improvement-approved.md` before exit
- **AND** `git status --porcelain improvement-approved.md` shows `M  improvement-approved.md` (no question mark)
- **AND** the script outputs `git add improvement-approved.md done`
- **AND** exit code is 0

#### Scenario: git add fails — script exits non-zero

- **GIVEN** working tree has a pre-existing `improvement-approved.md` lock or readonly error
- **WHEN** `approve_proposal.sh` runs and `git add` fails
- **THEN** the script exits with code 1
- **AND** outputs `❌ git add improvement-approved.md failed: <git error message>`
- **AND** the row IS written to `improvement-approved.md` (the underlying state is correct, only the staging fails)

### Requirement: `mark_approved_completed <name>` MUST fallback to archive-prefix detection

The `_lib/state.sh::mark_approved_completed <project_root> <name>` function MUST, when the entry is not found in the main table of `improvement-approved.md`, check if `openspec/changes/archive/<date>-<name>/` exists using the pattern `compgen -G "openspec/changes/archive/[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]-<name>"`. If the pattern matches, the function MUST append a row to the `## 已实施` section even though the main table entry is missing.

modifies: proposal-lifecycle-sync

The fallback MUST NOT emit a warning when the archive presence is verified — this is a normal recovery path, not an error.

modifies: proposal-lifecycle-sync

#### Scenario: Main table entry missing — archive fallback recovers

- **GIVEN** `improvement-approved.md` main table does NOT contain `[fix-proposal-approved-missing-after-archive]` row
- **AND** `openspec/changes/archive/2026-08-08-fix-proposal-approved-missing-after-archive/` exists
- **WHEN** `mark_approved_completed <project_root> "fix-proposal-approved-missing-after-archive"` runs
- **THEN** the function appends a row to `## 已实施` section: `| [fix-proposal-approved-missing-after-archive](improvements/fix-proposal-approved-missing-after-archive.md) | P1 | 2026-08-08 |`
- **AND** the function returns 0 (success)
- **AND** no error or warning is emitted

#### Scenario: Main table entry missing + no archive — no-op

- **GIVEN** `improvement-approved.md` main table does NOT contain `[draft-change]` row
- **AND** `openspec/changes/archive/*-draft-change/` does NOT exist
- **AND** `openspec/changes/draft-change/` does NOT exist either
- **WHEN** `mark_approved_completed <project_root> "draft-change"` runs
- **THEN** the function emits a warning `⚠️ mark_approved_completed: draft-change not found in improvement-approved.md and no archive/ detected`
- **AND** the function returns 1 (failure)
- **AND** no row is added

### Requirement: Dashboard pending filter MUST skip archived changes

The dashboard pending pool SHALL classify each improvement's lifecycle status from its leading marker using a single definition point, and that vocabulary MUST treat the registry's completion tokens — including `已落地`, `已拆分` and `已取代` — as terminal. Archived and approved names SHALL be removed from the pending pool only AFTER classification, and an archived-or-approved entry whose recorded status is not terminal MUST be reported as a stale-status diagnostic rather than disappearing from every view.

#### Scenario: Archived change is NOT in pending
- **GIVEN** `improvements/archive-cleanup-plan-files-extension.md` exists
- **AND** `openspec/changes/archive/2026-08-08-archive-cleanup-plan-files-extension/` exists
- **AND** `improvement-approved.md` does NOT contain the entry (lost during plan-phase commit)
- **WHEN** `data = collect(project_root)` runs
- **AND** `data.pending_suggestions` is computed
- **THEN** `archive-cleanup-plan-files-extension` is NOT counted in `pending_suggestions`
- **AND** `archive-cleanup-plan-files-extension` is NOT in `data.suggestions`
- **AND** the Section 7 "Pending" render lists it as "(no pending suggestions)" — no false-positive row
#### Scenario: Active improvement IS in pending
- **GIVEN** `improvements/fix-proposal-approved-missing-after-archive.md` exists
- **AND** `openspec/changes/archive/*-fix-proposal-approved-missing-after-archive/` does NOT exist
- **AND** `improvement-approved.md` already contains this name (in the main table)
- **WHEN** `data = collect(project_root)` runs
- **THEN** `fix-proposal-approved-missing-after-archive` is filtered out by the main-table check
- **AND** `pending_suggestions` does NOT include it (already approved)
#### Scenario: Pending improvement (not yet approved) IS in pending
- **GIVEN** `improvements/some-new-improvement.md` exists
- **AND** `improvement-approved.md` does NOT contain the entry
- **AND** `openspec/changes/archive/*-some-new-improvement/` does NOT exist
- **WHEN** `data = collect(project_root)` runs
- **THEN** `some-new-improvement` IS in `pending_suggestions`
- **AND** `some-new-improvement` IS in `data.suggestions`

#### Scenario: Archived improvement with a stale status is reported, not hidden

- **WHEN** an improvement has an archived copy, its `状态` is not terminal, and the dashboard snapshot is collected
- **THEN** the name is absent from the pending pool and appears in the snapshot's stale-status diagnostics

### Requirement: `plan-done` gate MUST warn on dirty `improvement-approved.md`

> **RETIRED (2026-11-20, align-spec-residue-prior-18)** —— 两个落点都不存在：① `.plan-handoff.json` 已于 ADR-0044 Wave 3 RETIRE（`docs/schemas/README.md:51` 「legacy plan-done, per ADR-0044 RETIRE」）；② `skills/rdd-builder/` 对 `plan-done` **0 命中**（v4 的 plan-done 是 `_lib/gate.py:378` 的 `plan_done` checks，其中没有 dirty-improvement-approved 判据）。语义祖先 `_lib/state.sh:505 check_dirty_key_files` 尚存但**孤儿**（唯一生产调用方 `guide/scan-state.sh` 已归档 `docs/legacy/`）⇒ 无等价承接。保留原文与 Scenario 作为历史记录。

The `guide-plan.md` plan-done exit handler MUST, before writing `.plan-handoff.json`, check `git status --porcelain improvement-approved.md`. If the output is non-empty (tracked file modified, or untracked file present), the gate MUST emit a warning `⚠️ improvement-approved.md has uncommitted changes — commit before plan-done` to stderr. The gate MUST NOT block plan-done (warning level only).
<!-- v4-residue:allow=history -->

modifies: proposal-lifecycle-sync

The warning is best-effort: if `git status` fails or `improvement-approved.md` does not exist, the gate MUST skip the warning silently.

modifies: proposal-lifecycle-sync

#### Scenario: plan-done with dirty improvement-approved.md

- **GIVEN** `improvement-approved.md` has uncommitted changes (`M improvement-approved.md` in `git status`)
- **WHEN** `plan-done` gate runs
- **THEN** the warning `⚠️ improvement-approved.md has uncommitted changes — commit before plan-done` is emitted to stderr
- **AND** plan-done continues (does not block)
- **AND** `.plan-handoff.json` is written

#### Scenario: plan-done with clean improvement-approved.md

- **GIVEN** `improvement-approved.md` is committed (no `M` or `??` in `git status`)
- **WHEN** `plan-done` gate runs
- **THEN** no warning is emitted
- **AND** plan-done proceeds normally

### Requirement: Out of scope MUST NOT include backward-compat shims

This fix MUST NOT introduce backward-compat shims for the missing `improvement-approved.md` row in `archive-cleanup-plan-files-extension` (the bug that motivated this improvement). The historical state is preserved in git; future recovery MUST be via the fix itself, not via retroactive patch.

modifies: proposal-lifecycle-sync

#### Scenario: No retroactive patch applied

- **GIVEN** `archive-cleanup-plan-files-extension` row was manually added to `## 已实施` (commit 3dc1b03)
- **WHEN** this improvement is shipped
- **THEN** the manual row is preserved (no rewriting)
- **AND** no script auto-detects and re-adds historical entries

## Opening Note

Worktree commit policy: this change follows the v2.0.5+ aggregate-commit pattern. After all tasks complete, ONE commit at the worktree level with conventional message, then archive.
