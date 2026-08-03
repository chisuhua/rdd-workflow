## 1. Setup

- [ ] 1.1 Read `proposal.md`, `design.md`, `improvements/fix-execute-change-name-persistence.md` and confirm In Scope / Out of Scope boundaries
- [ ] 1.2 Verify `skills/execute/scripts/select_worktree.sh::auto_detect_worktree_context` exports CHANGE_NAME on both paths (worktree L45 / lightweight L127); confirm current behavior with `grep -n "export CHANGE_NAME"`
- [ ] 1.3 Check current branch + worktree strategy; identify all execute-side entry points that read `$CHANGE_NAME` without a guard (SKILL.md Step 1, tasks_writeback.sh, execute_step7.sh, update_roadmap_progress.sh)

## 2. Implementation (TDD 5 步)

- [ ] 2.1 Write failing tests: add 2 bats cases (worktree branch `openspec/<name>` auto-derive / lightweight branch auto-derive) + extend for explicit-CHANGE_NAME-wins and non-openspec-branch error semantics in `tests/integration/test_select_worktree_extraction.bats` (or a new `test_execute_change_name_derive.bats`); assert derived CHANGE_NAME passes `test -f .rddf/plans/$CHANGE_NAME.md`
- [ ] 2.2 Verify tests fail (red): confirm execute SKILL.md Step 1 and tasks_writeback.sh entry currently have no derivation guard and fail with empty CHANGE_NAME
- [ ] 2.3 Implement change: add CHANGE_NAME auto-derivation fallback (`git branch --show-current | sed 's|^openspec/||'`, explicit value wins, failure exits non-zero with repair guidance) to execute SKILL.md Step 1 entry and `execute/scripts/tasks_writeback.sh`; reuse the shared `auto_detect_worktree_context` / extracted `derive_change_name` helper (single source, no copy-paste)
- [ ] 2.4 Verify tests pass (green): both new bats cases pass; explicit CHANGE_NAME is respected (not overwritten); non-openspec branch exits non-zero with "无法推导 change 名称，请设置 CHANGE_NAME" guidance
- [ ] 2.5 Refactor + commit: confirm no duplicated derivation logic across execute scripts, verify diff is proposal-only scope, then commit

## 3. Verification

- [ ] 3.1 Run `openspec validate fix-execute-change-name-persistence --json` — 接受 specs/ 缺失 ERROR (本次 fill 不写 specs/, plan 阶段决策)
- [ ] 3.2 Run `bats tests/integration/test_select_worktree_extraction.bats tests/integration/test_execute_skill.bats tests/integration/test_tasks_writeback_extraction.bats` (all pass)
- [ ] 3.3 Run `bats tests/smoke.bats` + full `npm test` bats regression — zero regression on existing execute-related tests
- [ ] 3.4 Manual smoke: in a temp git repo on branch `openspec/fake-change` with `.rddf/plans/fake-change.md` present, run the Step 1 derivation snippet without CHANGE_NAME set → derives correctly; with CHANGE_NAME=manual → manual wins
- [ ] 3.5 Run `git show HEAD:openspec/changes/fix-execute-change-name-persistence/design.md` (artifact committed)

## 4. Documentation

- [ ] 4.1 Update `skills/execute/SKILL.md` Step 1 / entry section documenting the CHANGE_NAME auto-derivation fallback and explicit-value-wins semantics
- [ ] 4.2 Add entry to `CHANGELOG.md` (if present)
- [ ] 4.3 Confirm no ADR change needed (proposal explicitly out of scope for ADR-0003 modifications)
