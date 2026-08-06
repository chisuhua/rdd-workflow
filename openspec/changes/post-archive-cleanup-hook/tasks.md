# post-archive-cleanup-hook — Tasks

> Schema: spec-driven
> Created: 2026-08-06
> See: `proposal.md` (motivation/scope) + `design.md` (technical decisions).

## 1. Setup & Baseline

- [ ] 1.1 Confirm working tree clean (`git status --porcelain` returns empty) before starting
- [ ] 1.2 Capture current `.rddf/plans/fix-rddf-init-broken-layout.md` "D" state as baseline
- [ ] 1.3 Add stub `_lib/post_archive_cleanup.sh` with header + public function signature

## 2. Core Hook Implementation

- [ ] 2.1 Implement `_WHITELIST_DELETED_PATHS` array (3 entries: `.rddf/plans/`, `.rddf/state/<change>*.json`, `openspec/changes/<change>/`)
- [ ] 2.2 Implement `_WHITELIST_MODIFIED_STAGED` array (3 entries: `proposal-approved.md`, `proposal-suggestions.md`, `roadmap.md`)
- [ ] 2.3 Implement `git status --porcelain` scan + classify into 3 buckets
- [ ] 2.4 Implement `git rm -f` for deleted-bucket (only whitelist paths)
- [ ] 2.5 Implement `git add` for modified-bucket (only whitelist paths)
- [ ] 2.6 Implement auto-commit (`chore(post-archive): clean residue from <change-name>`) when rm-bucket non-empty
- [ ] 2.7 Idempotent guard: when both buckets empty, exit 0 with no commit
- [ ] 2.8 `SKIP_POST_ARCHIVE_CLEANUP=yes` early-return
- [ ] 2.9 `DRY_RUN_POST_ARCHIVE_CLEANUP=yes` echo-only mode

## 3. Wire into Archive Pipeline

- [ ] 3.1 In `_lib/archive.sh::archive_change`: insert `post_archive_cleanup "$PWD" "$name"` after `cleanup_plan_file` call (around line 340)
- [ ] 3.2 In `skills/guide-ship/scripts/ship_archive.sh::archive_change_for_mode`: insert same hook after `cleanup_plan_file` call (line 248)
- [ ] 3.3 Source `_lib/post_archive_cleanup.sh` from both call sites (or have them call via explicit path)

## 4. Test Coverage (≥8 bats scenarios)

- [ ] 4.1 Setup: create throwaway change with `.rddf/plans/<n>.md` deleted state, run hook, assert `git status` clean
- [ ] 4.2 Idempotent: run hook twice, second run produces no commit
- [ ] 4.3 Dry-run: with `DRY_RUN_POST_ARCHIVE_CLEANUP=yes`, no git mutation, but echo output present
- [ ] 4.4 Skip: with `SKIP_POST_ARCHIVE_CLEANUP=yes`, hook early-returns exit 0
- [ ] 4.5 Whitelist boundary: dirty `tasks.md` + `docs/adr/*.md`, run hook, assert neither modified
- [ ] 4.6 Dual mode: instantiate both worktree + lightweight archive flows, verify hook fires in both
- [ ] 4.7 Commit message: assert commit subject matches `^chore\(post-archive\): clean residue from <name>$`
- [ ] 4.8 Real-world regression: apply hook to current `.rddf/plans/fix-rddf-init-broken-layout.md`, assert cleanup commit created

## 5. Documentation

- [ ] 5.1 Update `AGENTS.md` "Worktree Commit Flow" section: insert hook call diagram after archive主体
- [ ] 5.2 Update `proposal-approved.md` (after archive completed): add real-world wisdom about hook escape paths
- [ ] 5.3 Add inline comments in `_lib/post_archive_cleanup.sh` referencing 3 个根因 line numbers from this proposal

## 6. Rollout & Cleanup (post-merge)

- [ ] 6.1 After merge: run hook manually on existing残留 (`.rddf/plans/fix-rddf-init-broken-layout.md`, `proposal-approved.md`) → 产生 cleanup commit
- [ ] 6.2 Verify `bats tests/integration/test_ship_*.bats` 全绿(no regression)
- [ ] 6.3 Verify `pytest tests/` 全绿
- [ ] 6.4 (Optional follow-up PR) Remove now-redundant `cleanup_plan_file` function from `ship_archive.sh`
