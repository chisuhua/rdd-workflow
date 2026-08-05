# guide-ship Execution Contract (v1)

## Authoritative files

| File | Owner | Read by | Written by |
|---|---|---|---|
| `openspec/changes/<name>/proposal.md` | guide-plan | guide-plan, guide-ship | guide-plan |
| `openspec/changes/<name>/design.md` | guide-plan | guide-plan, guide-ship | guide-plan |
| `openspec/changes/<name>/tasks.md` | guide-plan | all phases (progress only) | guide-plan, execute (writeback) |
| `.rddf/plans/<name>.md` | guide-ship | execute | guide-ship (via writing-plans) |
| `.rddf/state/iteration.json` | guide-plan + guide-ship | rddf CLI, dashboard | guide-plan, guide-ship |
| `.rddf/state/.plan-handoff.json` | guide-plan → guide-ship | guide-ship | guide-plan, guide-ship |
| `openspec/<name>` branch / `.rddf/wt/<name>` worktree | guide-ship | execute | guide-ship |

## Execution authority

- `tasks.md` is the OpenSpec scope and completion checklist.
- `.rddf/plans/<change>.md` is the **only** executable implementation contract.
- `execute` consumes the plan and writes completion state back to `tasks.md`.
- `guide-ship` does not execute `tasks.md` directly under any circumstance.

## Quick Finish

Quick Finish is a degenerate exit from this contract, not a separate contract.
Conditions (all required):
- ≤2 remaining tasks in `tasks.md`
- no uncommitted source changes
- no non-trivial keywords (refactor, migration, schema, breaking)
- no active blockers
- user explicitly confirms with `--quick-finish`

If any condition fails, the full plan → execute path is mandatory.

## Workspace

- `guide-ship` chooses `lightweight` (branch on main repo) or `worktree` (isolated worktree) **once** in Phase 1.
- The chosen workspace is exported as `RDDF_EXECUTION_ROOT` for `execute`.
- `execute` does not re-detect its workspace; it honors the env var.

## Commit policy

- `execute` does not commit per task.
- `guide-ship` Phase 2.7 creates one aggregate commit per change before archive.
- `archive.sh::check_worktree_commits` runs in both lightweight and worktree modes; the gate does not skip lightweight.