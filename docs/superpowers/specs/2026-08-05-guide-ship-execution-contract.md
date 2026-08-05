# guide-ship Execution Contract (v1.1)

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

## Change discovery

- `guide-ship` Phase 1 uses `rddf discover-ship-changes` as the **single source of truth**
  for active candidates (filesystem ∪ plan-handoff ∪ iteration ∪ branch/worktree).
- Archived entries (`archived_changes` in `.plan-handoff.json`,
  `iteration.status == archived`) are filtered out.
- Single executable candidate → auto-select via `ship_top_candidate`.
- Multiple → display the candidate table from the discovery output and let the user pick.

## Quick Finish

Quick Finish is a degenerate exit from this contract, not a separate contract.
Conditions (all required):
- ≤2 remaining tasks in `tasks.md`
- no TRACKED uncommitted source changes
- no non-trivial keywords (implement, add, create, build, refactor, test, function, class, module, api, feature, logic, handler, controller, schema, migration, script, breaking)
- no unresolved `manual_blocks` in `roadmap-meta.yaml` (per ADR-0022)
- user explicitly confirms with `--quick-finish` (or the orchestrator sets `QUICK_FINISH_SELECTED=A`)

If any condition fails, the full plan → execute path is mandatory.

## Workspace

- `guide-ship` chooses `lightweight` (branch on main repo) or `worktree` (isolated worktree) **once** in Phase 1.
- The chosen workspace is exported as `RDDF_EXECUTION_ROOT` for `execute`.
- `execute` honors `RDDF_EXECUTION_ROOT` only when its `--git-common-dir` matches
  the detected main repo root (containment check); otherwise it falls through
  to legacy worktree detection.
- `run_ship_phase1` re-exports `RDDF_EXECUTION_ROOT` in the parent shell after
  capturing `WT_PATH` via command substitution (subshells lose exports).

## Commit policy

- `execute` does not commit per task.
- `guide-ship` Phase 2.7 creates one aggregate commit per change before archive.
- `archive.sh::check_worktree_commits` runs in the worktree archive path.
- `archive_change_for_mode` checks `archive_gate_check` in BOTH modes and propagates
  errors; lightweight mode without new commits is a hard block.
- `archive_gate_check` accepts an explicit `tasks_root` arg so it reads the
  up-to-date `tasks.md` from the worktree copy, not the stale default-branch copy.