# sync-changelog-unreleased Implementation Plan

**Source change**: `openspec/changes/sync-changelog-unreleased/`
**Mode**: lightweight (no worktree, ADR-0024 rationale: doc-only, tasks≤5)
**Generated**: 2026-08-13 by guide-ship equivalent (rdd-workflow-writing-plans AI)

## Context

`CHANGELOG.md [Unreleased]` last updated at `afc369a`. 20+ commits accumulated unreleased.
This plan resolves the drift via a doc-only change and verifies the
post-flow-analysis reporter (ADR-0027) both detects the pre-state drift AND
stops detecting once the gap is closed.

## TDD 5-Step Structure

### Step 1: Verify drift baseline (red test)

- **Goal**: Confirm ground truth — CHANGELOG is stale before our fix
- **Action**: Run drift detection commands
- **Test command**:
  ```bash
  last_changelog_commit=$(git log --oneline -1 -- CHANGELOG.md | cut -d' ' -f1)
  drift_count=$(git log --oneline ${last_changelog_commit}..HEAD -- ':!CHANGELOG.md' | wc -l)
  changelog_updates=$(git log --oneline ${last_changelog_commit}..HEAD -- CHANGELOG.md | wc -l)
  # RED condition: drift_count > 0 AND changelog_updates == 0
  [ "$drift_count" -gt 5 ] && [ "$changelog_updates" -eq 0 ] && echo "RED: drift detected ($drift_count commits)"
  ```
- **Expected**: drifts > 5, CHANGELOG updates = 0

### Step 2: Generate CHANGELOG [Unreleased] updates (implement)

- **Goal**: Add 3 feature groups covering all 20+ commits
- **File**: `CHANGELOG.md`
- **Action**: Insert under `## [Unreleased]` header with 3 `### Feature Name` subsections
- **Acceptance**:
  - ≥ 30 lines added
  - 3 feature groups (orchestrator / env-check / archive)
  - All 20+ commits referenced by hash

### Step 3: Verify fix (pass test)

- **Goal**: Confirm CHANGELOG now covers the drift
- **Test command**:
  ```bash
  last_changelog_commit=$(git log --oneline -1 -- CHANGELOG.md | cut -d' ' -f1)
  drift_count=$(git log --oneline ${last_changelog_commit}..HEAD -- ':!CHANGELOG.md' | wc -l)
  changelog_updates=$(git log --oneline ${last_changelog_commit}..HEAD -- CHANGELOG.md | wc -l)
  # PASS condition: changelog_updates >= 1
  [ "$changelog_updates" -ge 1 ] && echo "GREEN: CHANGELOG now updated"
  ```
- **Expected**: CHANGELOG updates ≥ 1

### Step 4: Run reporter (verify AD-0027 contract)

- **Goal**: Verify ADR-0027 reporter detects drift BEFORE fix and stops after
- **Action**:
  ```bash
  # BEFORE (would happen if we hadn't fixed): detect_issue returns arch_drift
  # AFTER (current state): detect_issue returns no changelog drift
  python3 -c "from _lib.issue_reporter import detect_issue; r = detect_issue(); print(r)"
  ```
- **Expected**: No `arch_drift: CHANGELOG` reported (we just fixed it)

### Step 5: Commit + archive

- **Goal**: Persist the change and close the loop
- **Action**:
  ```bash
  git add CHANGELOG.md docs/adr/ADR-0027-continuous-evolution-feedback-loop.md
  git commit -m "feat(changelog): sync [Unreleased] with 20+ drift commits
  
  Implements sync-changelog-unreleased change. Covers 3 feature groups:
  rddf orchestrate (11 commits), env-check gh_available (1),
  archive close hook lightweight mode (1), plus 8 docs/fix/test commits."
  openspec archive sync-changelog-unreleased --yes
  ```
- **Acceptance**: archive completes, iteration.json status → archived

## Verification

- ✅ `git diff --stat CHANGELOG.md` shows ≥ 30 added lines
- ✅ `git log --oneline afc369a..HEAD -- CHANGELOG.md` returns ≥ 1 commit
- ✅ `python3 -m pytest tests/unit/` 0 regression
- ✅ `python3 -c "from _lib.issue_reporter import detect_issue; print(detect_issue())"` shows no CHANGELOG drift
- ✅ `openspec status` shows `sync-changelog-unreleased` as archived
