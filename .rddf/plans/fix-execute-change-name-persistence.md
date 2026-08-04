# fix-execute-change-name-persistence Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use skill_use("execute") to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ensure execute can derive its OpenSpec change name from an `openspec/<name>` branch whenever the environment variable is absent, while preserving explicit values and producing a clear error on unrelated branches.

**Architecture:** Introduce one sourced `ensure_change_name` helper that implements explicit-value-first, branch-derived-second, error-on-failure semantics. `select_worktree.sh` reuses it for both existing-worktree and selected-worktree paths; execute’s entry documentation and dependent shell helpers source the same file instead of copying branch parsing logic.

**Tech Stack:** POSIX-compatible Bash, git branch/worktree commands, Bats, temporary git repositories, existing execute helper scripts.

---

## File Structure

### Production Code

| File | Responsibility |
|---|---|
| `skills/execute/scripts/change_name.sh` | Shared `ensure_change_name` function that exports `CHANGE_NAME` or returns a repairable error. |
| `skills/execute/scripts/select_worktree.sh` | Source and invoke the shared helper while retaining existing worktree selection behavior. |
| `skills/execute/scripts/tasks_writeback.sh` | Ensure `CHANGE_NAME` before resolving the selected change’s tasks.md. |
| `skills/execute/scripts/execute_step7.sh` | Ensure the final report receives the derived runtime context. |
| `skills/execute/scripts/update_roadmap_progress.sh` | Ensure the optional change argument/context is derived consistently. |
| `skills/execute/SKILL.md` | Document and invoke automatic derivation at the Step 1 entry. |
| `CHANGELOG.md` | Record the runtime-context fix. |

### Tests

| File | Responsibility |
|---|---|
| `tests/integration/test_execute_change_name_derive.bats` | Verify worktree and lightweight branch derivation, explicit-value precedence, invalid-branch failure, and plan-path usability. |
| `tests/integration/test_select_worktree_extraction.bats` | Preserve existing helper extraction/export contracts while covering shared-helper sourcing. |
| `tests/integration/test_tasks_writeback_extraction.bats` | Verify tasks writeback works when branch context supplies the change name. |
| `tests/integration/test_execute_skill.bats` | Verify the documented Step 1 sources the helper and keeps the plan lookup guarded. |

---

### Task 1: Lock change-name derivation behavior with temporary repositories

**Files:**
- Create: `tests/integration/test_execute_change_name_derive.bats`
- Test: `skills/execute/scripts/change_name.sh`
- Test: `skills/execute/scripts/select_worktree.sh`

- [ ] **Step 1: Write the failing tests**

Create Bats cases that initialize temporary git repositories, create a commit, create `.rddf/plans/worktree-case.md` or `.rddf/plans/lightweight-case.md`, and check out `openspec/worktree-case` or `openspec/lightweight-case`. Source the future shared helper with `CHANGE_NAME` unset and assert `CHANGE_NAME=worktree-case` or `CHANGE_NAME=lightweight-case`, respectively. Add cases for `CHANGE_NAME=manual-case` remaining unchanged and a `master` branch returning non-zero with `无法推导 change 名称，请设置 CHANGE_NAME`.

- [ ] **Step 2: Run tests to verify they fail**

Run: `bats tests/integration/test_execute_change_name_derive.bats`

Expected: FAIL because `skills/execute/scripts/change_name.sh` does not exist and the current entry points do not provide the shared guard.

- [ ] **Step 3: Write the minimal implementation**

Create `change_name.sh` with `ensure_change_name`: return immediately when `CHANGE_NAME` is non-empty; otherwise read `git branch --show-current`, require the `openspec/` prefix, strip only that prefix, export the result, and return non-zero with the exact repair guidance when git context or prefix validation fails. Keep the helper side-effect limited to `CHANGE_NAME`.

- [ ] **Step 4: Run focused tests to verify they pass**

Run: `bats tests/integration/test_execute_change_name_derive.bats`

Expected: PASS for both branch forms, explicit precedence, and the non-openspec error path. The plan file check must use the derived value and pass in both temporary repositories.

- [ ] **Step 5: Commit the shared derivation contract**

```bash
git add skills/execute/scripts/change_name.sh tests/integration/test_execute_change_name_derive.bats
git commit -m "test: lock execute change name derivation"
```

### Task 2: Reuse the helper in worktree selection and dependent scripts

**Files:**
- Modify: `skills/execute/scripts/select_worktree.sh`
- Modify: `skills/execute/scripts/tasks_writeback.sh`
- Modify: `skills/execute/scripts/execute_step7.sh`
- Modify: `skills/execute/scripts/update_roadmap_progress.sh`
- Modify: `tests/integration/test_select_worktree_extraction.bats`
- Modify: `tests/integration/test_tasks_writeback_extraction.bats`

- [ ] **Step 1: Write the failing tests**

Extend the existing extraction tests to assert `select_worktree.sh` sources `change_name.sh`, an `openspec/*` current branch exports its name through `auto_detect_worktree_context`, and `tasks_writeback.sh` can mark a task with `CHANGE_NAME` initially unset when run from an OpenSpec branch. Add structural assertions that Step 7 and roadmap progress source or invoke the same guard before using the name.

- [ ] **Step 2: Run tests to verify they fail**

Run: `bats tests/integration/test_select_worktree_extraction.bats tests/integration/test_tasks_writeback_extraction.bats`

Expected: FAIL on the new shared-source and unset-context assertions because the existing scripts either parse the branch themselves or reject an empty `CHANGE_NAME`.

- [ ] **Step 3: Write the minimal implementation**

Source `change_name.sh` from `select_worktree.sh` and call `ensure_change_name` only where branch context is available; preserve its existing selection menu and `HAS_WORKTREE` behavior. In `tasks_writeback.sh`, source the helper and call it before checking task arguments, retaining the existing atomic `mktemp`/`mv` writes. In `execute_step7.sh` and `update_roadmap_progress.sh`, source the same helper and derive only when no explicit function argument or environment value exists; keep their existing graceful non-fatal behavior for missing roadmap metadata.

- [ ] **Step 4: Run focused tests to verify they pass**

Run: `bats tests/integration/test_select_worktree_extraction.bats tests/integration/test_tasks_writeback_extraction.bats tests/integration/test_execute_change_name_derive.bats`

Expected: All derivation, export, task writeback, and existing worktree-selection tests pass; explicit names remain authoritative and no duplicated branch-prefix parser is introduced.

- [ ] **Step 5: Commit the helper integrations**

```bash
git add skills/execute/scripts/select_worktree.sh skills/execute/scripts/tasks_writeback.sh skills/execute/scripts/execute_step7.sh skills/execute/scripts/update_roadmap_progress.sh tests/integration/test_select_worktree_extraction.bats tests/integration/test_tasks_writeback_extraction.bats
git commit -m "fix: reuse derived change name across execute helpers"
```

### Task 3: Wire the execute Step 1 entry and documentation

**Files:**
- Modify: `skills/execute/SKILL.md`
- Modify: `tests/integration/test_execute_skill.bats`
- Modify: `CHANGELOG.md`

- [ ] **Step 1: Write the failing tests**

Add structural Bats assertions that the Step 1 entry sources `scripts/change_name.sh`, calls `ensure_change_name` before checking `.rddf/plans/$CHANGE_NAME.md`, documents explicit-value precedence, and includes the exact error guidance for branches that cannot be mapped to a change.

- [ ] **Step 2: Run tests to verify they fail**

Run: `bats tests/integration/test_execute_skill.bats`

Expected: FAIL because the current Step 1 only prints `$CHANGE_NAME` and does not derive or validate it before plan lookup.

- [ ] **Step 3: Write the minimal implementation**

Update the Step 1 Bash block to source `scripts/change_name.sh`, call `ensure_change_name || exit 1`, then print the resolved name and perform the existing worktree/plan checks. Keep guide-ship’s selection logic unchanged, state that explicit `CHANGE_NAME` wins, and state that non-OpenSpec branches must set the variable manually. Add a concise changelog entry.

- [ ] **Step 4: Run tests to verify they pass**

Run: `bats tests/integration/test_execute_skill.bats tests/integration/test_select_worktree_extraction.bats tests/integration/test_tasks_writeback_extraction.bats`

Expected: PASS with the helper invocation present, the old empty-variable failure prevented, and all existing execute extraction contracts intact.

- [ ] **Step 5: Commit the entry-point fix**

```bash
git add skills/execute/SKILL.md CHANGELOG.md tests/integration/test_execute_skill.bats
git commit -m "fix: persist execute change name at entry"
```

### Task 4: Verify the complete change and repository regression

**Files:**
- Verify: `openspec/changes/fix-execute-change-name-persistence/proposal.md`
- Verify: `openspec/changes/fix-execute-change-name-persistence/design.md`
- Verify: `openspec/changes/fix-execute-change-name-persistence/tasks.md`
- Verify: `skills/execute/scripts/change_name.sh`
- Verify: `skills/execute/SKILL.md`

- [ ] **Step 1: Write the failing verification command**

Run the focused derivation, selection, tasks-writeback, and execute-skill tests together, then validate the OpenSpec change artifacts. This is the final gate that catches an untested consumer or a plan-path mismatch.

- [ ] **Step 2: Run tests to verify the baseline**

Run: `bats tests/integration/test_execute_change_name_derive.bats tests/integration/test_select_worktree_extraction.bats tests/integration/test_tasks_writeback_extraction.bats tests/integration/test_execute_skill.bats`

Expected: All focused tests pass; any failure must identify a concrete consumer that still reads an empty or duplicated change-name value.

- [ ] **Step 3: Complete the minimal verification**

Run: `openspec validate fix-execute-change-name-persistence --json`; then run `bats tests/smoke.bats` and `npm test`. Run a manual temporary-repository smoke for `openspec/fake-change` with no variable and with `CHANGE_NAME=manual`, and confirm the non-OpenSpec branch exits non-zero without guessing.

- [ ] **Step 4: Confirm the acceptance criteria**

Expected: worktree and lightweight branches derive correctly, explicit values are never overwritten, invalid branch context reports the repair command, all execute consumers share one helper, and the existing execute-related regression suite remains green. Record any unrelated pre-existing test failure separately.

- [ ] **Step 5: Commit final verification-only adjustments**

```bash
git add skills/execute/SKILL.md skills/execute/scripts/change_name.sh skills/execute/scripts/select_worktree.sh skills/execute/scripts/tasks_writeback.sh skills/execute/scripts/execute_step7.sh skills/execute/scripts/update_roadmap_progress.sh tests/integration/test_execute_change_name_derive.bats tests/integration/test_select_worktree_extraction.bats tests/integration/test_tasks_writeback_extraction.bats tests/integration/test_execute_skill.bats CHANGELOG.md
git commit -m "test: verify execute change name persistence"
```
