# plan-execute-commit-policy-consistency Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use skill_use("execute") to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Eliminate the structural contradiction between the rdd-workflow-writing-plans TDD 5-step template and the repository's archive-phase commit convention by defaulting Step 5 to "Defer commit to archive phase", aligning the execute skill instructions and AGENTS.md policy note, and locking the behavior with a bats test.

**Architecture:** Change the embedded Task template in `skills/rdd-workflow-writing-plans/SKILL.md` so Step 5 no longer instructs a per-task commit; instead it documents the default "defer to archive" policy and a `COMMIT_IN_EXECUTE=yes` opt-in switch. Mirror the same wording in `skills/execute/SKILL.md` where the executor is instructed how to behave. Update the relevant paragraph in `AGENTS.md` so the policy, plan template, and executor instructions are consistent. Add one bats integration test that greps the skill files to verify the default Step 5 does not contain commit instructions and does contain the defer wording.

**Tech Stack:** Markdown skill files, bash (bats-core 1.10+), grep.

**OpenSpec change artifacts** (canonical): `openspec/changes/plan-execute-commit-policy-consistency/{proposal,tasks}.md`.

---

## File Structure

### Production Code

| File | Responsibility |
|---|---|
| `skills/rdd-workflow-writing-plans/SKILL.md` | MODIFY: replace the Step 5 template block with defer-commit wording + `COMMIT_IN_EXECUTE=yes` opt-in note |
| `skills/execute/SKILL.md` | MODIFY: align the Step 5 instruction text for executor with the archive-phase commit policy |
| `AGENTS.md` | MODIFY: unify the commit policy wording so the plan template and execute skill are cross-referenced |

### Tests

| File | Responsibility |
|---|---|
| `tests/integration/test_plan_commit_policy.bats` | NEW: verify the default writing-plans Step 5 defers commit and the execute skill no longer instructs a per-task commit |

---

### Task 1: Lock the policy with a failing bats test

**Files:**
- Create: `tests/integration/test_plan_commit_policy.bats`
- Read: `skills/rdd-workflow-writing-plans/SKILL.md`
- Read: `skills/execute/SKILL.md`

- [x] **Step 1: Write the failing test**

Create `tests/integration/test_plan_commit_policy.bats` with three cases. The test file uses the standard `test_helper` and asserts structural policy on the two skill files.

```bash
#!/usr/bin/env bats
# tests/integration/test_plan_commit_policy.bats
#
# Verify that rdd-workflow-writing-plans and execute skill files default
# to deferring commit to the archive phase, not per-task commit.

load ../test_helper

setup() {
  wp="$REPO_ROOT/skills/rdd-workflow-writing-plans/SKILL.md"
  ex="$REPO_ROOT/skills/execute/SKILL.md"
}

@test "plan_commit_policy: writing-plans template step 5 defers commit" {
  # The example Step 5 heading must be "Defer commit" or equivalent.
  grep -qE 'Step 5.*Defer commit' "$wp"
  # The example Step 5 body must mention the archive-phase defer wording.
  grep -qE '留待 archive 阶段统一提交|暂不 commit|archive 阶段统一提交' "$wp"
}

@test "plan_commit_policy: writing-plans template does not instruct commit by default" {
  # Extract the embedded Task template block (from "### Task N:" to the closing `````).
  block=$(sed -n '/^### Task N:/,/^````/p' "$wp")
  # Default template must not contain a commit command.
  [[ "$block" != *"git commit"* ]]
  [[ "$block" != *"git add"* ]]
}

@test "plan_commit_policy: execute skill step 5 defers commit" {
  # The execute skill instructions must contain the defer wording.
  grep -qE 'Step 5.*Defer commit|execute 阶段不.*commit|archive 阶段.*提交' "$ex"
  # The five lines following "Step 5" must not contain a commit command.
  run grep -A 5 "Step 5" "$ex"
  [[ "$output" != *"git commit"* ]]
}
```

- [x] **Step 2: Run the test to verify it fails**

```bash
cd /workspace/project/rdd-workflow
bats tests/integration/test_plan_commit_policy.bats
```
Expected: all 3 tests fail because the skill files currently instruct a per-task commit.

- [x] **Step 3: Do not implement yet**

This task only creates the test; the implementation is in Task 2 and Task 3. Mark this step done when the failing test is recorded.

- [x] **Step 4: Re-run the test to confirm it still fails**

```bash
bats tests/integration/test_plan_commit_policy.bats
```
Expected: RED (3 failures). This confirms the test is sensitive to the bug.

- [x] **Step 5: Defer commit**

Do not run any commit command. After the test is written and confirmed failing, mark this task complete by updating `openspec/changes/plan-execute-commit-policy-consistency/tasks.md`. All changes will be committed together in the archive phase.

---

### Task 2: Update the writing-plans skill template

**Files:**
- Modify: `skills/rdd-workflow-writing-plans/SKILL.md` (lines 115-121, the Step 5 template block)
- Test: `tests/integration/test_plan_commit_policy.bats`

- [x] **Step 1: Identify the Step 5 template block**

Locate the embedded Task template block in `skills/rdd-workflow-writing-plans/SKILL.md`. It starts at:

```markdown
- [x] **Step 5: Commit**
```

and ends with the closing code fence for the bash example.

- [x] **Step 2: Verify the test is still failing before the edit**

```bash
bats tests/integration/test_plan_commit_policy.bats
```
Expected: RED.

- [x] **Step 3: Replace Step 5 with the defer-commit wording**

Replace the Step 5 block with the following:

```markdown
- [x] **Step 5: Defer commit**

按仓库约定，execute 阶段不逐任务 commit；所有变更将在 archive 阶段统一提交。
如需在 execute 阶段逐任务 commit（不推荐），可设置 `COMMIT_IN_EXECUTE=yes`。
```

Do not leave any bash example containing commit commands under the default template. Keep the `COMMIT_IN_EXECUTE=yes` opt-in mention explicit so the policy is discoverable.

- [x] **Step 4: Run the bats test to verify the writing-plans part passes**

```bash
bats tests/integration/test_plan_commit_policy.bats
```
Expected: the first two tests pass; the third may still fail because `skills/execute/SKILL.md` is not yet updated.

- [x] **Step 5: Defer commit**

Do not run any commit command. Mark the task complete by updating `tasks.md`. Changes will be committed in the archive phase.

---

### Task 3: Align the execute skill instructions

**Files:**
- Modify: `skills/execute/SKILL.md` (lines 176-179, the Step 5 instruction text)
- Test: `tests/integration/test_plan_commit_policy.bats`

- [x] **Step 1: Inspect the current Step 5 instructions**

Locate the Step 5 instructions in `skills/execute/SKILL.md` around line 176. The current text instructs the executor to add files and create a commit for each work unit.

- [x] **Step 2: Verify the test still fails for the execute skill part**

```bash
bats tests/integration/test_plan_commit_policy.bats
```
Expected: the third test fails.

- [x] **Step 3: Replace the Step 5 instruction with the defer wording**

Replace the Step 5 instruction text with:

```markdown
Step 5 — Defer commit：
  按仓库约定，execute 阶段不执行 commit；继续下一个 Task。所有变更将在 archive 阶段统一提交。
  如需在 execute 阶段逐任务 commit（不推荐），设置 `COMMIT_IN_EXECUTE=yes`。
```

The example bash block previously shown under this step should also be removed, because the default path does not stage or commit anything.

- [x] **Step 4: Run the full bats test to verify all three tests pass**

```bash
bats tests/integration/test_plan_commit_policy.bats
```
Expected: 3/3 PASS.

- [x] **Step 5: Defer commit**

Do not run any commit command. Mark the task complete by updating `tasks.md`. Changes will be committed in the archive phase.

---

### Task 4: Unify the AGENTS.md policy note

**Files:**
- Modify: `AGENTS.md` (the "常见陷阱 #6" and the "分支与 Worktree" sections)
- Test: `tests/integration/test_plan_commit_policy.bats` (already green)

- [x] **Step 1: Find the existing commit policy notes**

```bash
cd /workspace/project/rdd-workflow
grep -n "execute 阶段不 commit\|COMMIT_IN_EXECUTE\|archive 阶段" AGENTS.md
```
Expected: at least one hit in the "常见陷阱" section and one in the "归档流程" section.

- [x] **Step 2: Add a cross-reference to the plan template and opt-in switch**

After the existing "execute 阶段不 commit/push — commit 留到 archive 阶段" note in the "常见陷阱" section, add one sentence:

```markdown
- `rdd-workflow-writing-plans` 生成的 plan 默认在 Step 5 不执行 commit；如需逐任务 commit，设置 `COMMIT_IN_EXECUTE=yes`（不推荐）。
```

Also verify the "分支与 Worktree" section mentions the commit gate for worktree creation; do not change that behavior. The goal is to make the policy note, the plan template, and the executor instructions point to the same convention.

- [x] **Step 3: Verify the AGENTS.md wording is present**

```bash
grep -n "COMMIT_IN_EXECUTE\|暂不 commit\|留到 archive 阶段" AGENTS.md
```
Expected: the new cross-reference line and the original policy line are both present.

- [x] **Step 4: Re-run the full policy test suite**

```bash
bats tests/integration/test_plan_commit_policy.bats
```
Expected: 3/3 PASS.

- [x] **Step 5: Defer commit**

Do not run any commit command. Mark the task complete by updating `tasks.md`. Changes will be committed in the archive phase.

---

### Task 5: Final verification and regression gate

**Files:**
- Read: `skills/rdd-workflow-writing-plans/SKILL.md`
- Read: `skills/execute/SKILL.md`
- Read: `AGENTS.md`
- Test: `tests/integration/test_plan_commit_policy.bats`

- [x] **Step 1: Verify no commit instruction appears in the default plan template**

```bash
cd /workspace/project/rdd-workflow
sed -n '/^### Task N:/,/^````/p' skills/rdd-workflow-writing-plans/SKILL.md | grep -c 'git commit' || true
```
Expected: 0.

- [x] **Step 2: Run the new integration test**

```bash
bats tests/integration/test_plan_commit_policy.bats
```
Expected: 3/3 PASS.

- [x] **Step 3: Run smoke tests to confirm no structural breakage**

```bash
bats tests/smoke.bats
```
Expected: all existing smoke tests pass (exit 0).

- [x] **Step 4: Verify the updated skill file still has a valid frontmatter header**

```bash
head -5 skills/rdd-workflow-writing-plans/SKILL.md | grep -c '^---'
head -5 skills/execute/SKILL.md | grep -c '^---'
```
Expected: 2 for each file (opening and closing `---` of the frontmatter YAML block).

- [x] **Step 5: Defer commit**

Do not run any commit command. After all verification passes, mark the final task complete by updating `tasks.md`. The archive phase will commit all modified files together.

---

## Acceptance Criteria

- [ ] `skills/rdd-workflow-writing-plans/SKILL.md` default Step 5 template says "Defer commit" and explains the archive-phase policy.
- [ ] `skills/rdd-workflow-writing-plans/SKILL.md` default Step 5 template no longer contains a `git commit` example.
- [ ] `skills/execute/SKILL.md` Step 5 instructions tell the executor to defer commit to the archive phase.
- [ ] `AGENTS.md` contains a cross-reference linking the commit policy to the plan template and the `COMMIT_IN_EXECUTE=yes` opt-in.
- [ ] `tests/integration/test_plan_commit_policy.bats` passes and locks the behavior.
- [ ] Smoke tests remain green.
- [ ] Frontmatter of both skill files remains intact.
- [ ] No changes are made to `archive.sh` or archive-phase commit logic.
- [ ] The TDD 5-step structure itself is preserved; only Step 5 content is changed.

## Commit History Expected

```
<existing base>
test(integration): add bats test for plan/execute commit policy consistency
docs(skills): default writing-plans Step 5 to defer commit with opt-in
docs(skills): align execute skill Step 5 with archive-phase commit policy
docs(AGENTS.md): cross-reference plan template commit policy
```
