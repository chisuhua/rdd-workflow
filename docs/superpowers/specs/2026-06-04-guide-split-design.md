# Spec-Workflow Guide Split — Design Spec

**Date:** 2026-06-04
**Status:** Pending Review
**Scope:** Refactor `skills/guide.md` (1465 lines) into three focused skills
**Target Branch:** `master`

---

## 1. Background

`skills/guide.md` is the current interactive wizard for the spec-workflow package. It owns a single state machine spanning setup → roadmap → propose → deps → plan → execute → status/archive → cleanup, with persistence in `workflow-state.md` and `workflow-progress.md`. The file has accumulated to 1465 lines and conflates two very different mental models:

- **Spec-side** (what to build): driven by openspec CLI, ADR scanning, roadmap filtering, change artifacts
- **Ship-side** (how to build & ship it): driven by git worktree, Prometheus `start_work`, merge, archive

This conflation creates three concrete problems:

1. **State file ownership is ambiguous** — `workflow-state.md` mixes "which phase are we in" (spec) with "which worktree is active" (ship), so neither side can be understood or reset in isolation.
2. **The `plan` skill straddles the boundary** — it does candidate discovery (spec-side) AND worktree creation + Prometheus plan generation (ship-side), which is the actual source of coupling.
3. **The `guide` entry point pulls in too many concerns** — every call must re-load the full state machine even when the user only wants, say, "check if I have any unfinished worktrees."

## 2. Goals

1. Split `guide` into three skills with clear, non-overlapping responsibility:
   - `guide-spec`: owns the spec-side state machine (setup → roadmap → propose → deps → spec-done)
   - `guide-ship`: owns the ship-side state machine (discover → worktree → plan → execute → archive → ship-done)
   - `guide`: a stateless recommender that scans project state and suggests which sub-skill to run
2. Delete `plan.md` and distribute its responsibilities to both sides (no cross-boundary skill).
3. Eliminate `workflow-state.md` and `workflow-progress.md`; each side persists its own state in already-existing files (`proposal-suggestions.md` for spec, `tasks.md` for ship). `guide` recommender does on-the-fly scanning.
4. Make the handoff between spec and ship a **git commit boundary**: spec-side ends when `openspec/changes/<name>/{proposal,design,tasks}.md` are all reachable via `git show HEAD:...`. Ship-side starts by scanning committed changes only.
5. Keep the public command surface minimal: only the three skill names.

## 3. Non-Goals

- No changes to underlying openspec CLI behavior, change artifact schemas, or commit conventions.
- No new external dependencies.
- No re-design of `execute` or `propose` internals — they keep their current behavior; only their **caller** changes (now `guide-ship` calls `execute`; `guide-spec` calls `propose`).
- No renaming of `propose` / `execute` / `status` / `INSTALL` skills.
- No support for "do everything end-to-end in one call" — the user is now explicit about which phase they're invoking.
- No migration script for old `workflow-state.md` files; if a user upgrades mid-flight, they must re-run from a clean state (warning emitted by `guide` recommender if a stale state file is detected).

## 4. Files In Scope

| File | Action |
|---|---|
| `skills/guide.md` | **Rewrite** as ~50-line stateless recommender |
| `skills/guide-spec.md` | **Create** (new file) — spec-side state machine |
| `skills/guide-ship.md` | **Create** (new file) — ship-side state machine |
| `skills/plan.md` | **Delete** — responsibilities distributed to spec/ship sides |
| `skills/execute.md` | **Edit** — update header to clarify it's called by `guide-ship`, not standalone (no behavior change) |
| `skills/propose.md` | **Edit** — update header to clarify it's called by `guide-spec` (no behavior change) |
| `skills/roadmap.md` | **Edit** — update header to clarify it's called by `guide-spec` (no behavior change) |
| `skills/deps.md` | **Edit** — update header to clarify it's called by `guide-spec` (no behavior change) |
| `skills/status.md` | **Edit** — clarify its standalone-vs-called-by-`guide-ship` status (no behavior change) |
| `README.md` | **Edit** — document the three new entry points |
| `USAGE.md` | **Edit** — update workflow examples |
| `INSTALL.md` | **Edit** — list the three new skills to install |

Total: 1 deleted, 2 created, 1 rewritten, 8 edited.

## 5. Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         User invokes one of:                        │
│                                                                     │
│  skill_use("guide")   →  Stateless recommender (50 lines)          │
│                            │                                        │
│                            │ reads: roadmap.md, openspec/changes/, │
│                            │        git worktree list              │
│                            │ writes: nothing                       │
│                            │                                        │
│                            ▼                                        │
│                   prints recommended command:                       │
│                   skill_use("guide-spec")  OR                      │
│                   skill_use("guide-ship")                          │
│                                                                     │
│  skill_use("guide-spec")  →  Spec-side state machine              │
│                                  setup → roadmap → propose →       │
│                                  deps → spec-done                  │
│                            │                                        │
│                            │ calls: roadmap, propose, deps         │
│                            │ reads: docs/adr/, roadmap.md          │
│                            │ writes: openspec/changes/<name>/,     │
│                            │         proposal-suggestions.md       │
│                            │                                        │
│                            ▼                                        │
│                   spec-done = git commit of three artifacts       │
│                                                                     │
│  skill_use("guide-ship")  →  Ship-side state machine              │
│                                  discover → worktree → plan →      │
│                                  execute → archive → ship-done     │
│                            │                                        │
│                            │ calls: execute (skill),               │
│                            │        Prometheus start_work          │
│                            │ reads: openspec/changes/<name>/,      │
│                            │        .sisyphus/plans/<name>.md      │
│                            │ writes: tasks.md ([x]), git main,     │
│                            │         openspec/changes/archive/     │
└─────────────────────────────────────────────────────────────────────┘
```

## 6. The Three Skills

### 6.1 `guide-spec` — Spec-Side State Machine

**Owns:** the chain from "no idea what to build" to "OpenSpec change artifacts committed to main".

| Phase | Entry condition | Action | Exit condition |
|---|---|---|---|
| `setup` | No `roadmap.md` or first invocation | Check openspec CLI, git, ADR directories | Tools available |
| `roadmap` | `setup` done | Init/read/edit `roadmap.md`, set current phase | `roadmap.md` exists with current phase |
| `propose` | `roadmap` phase set | Scan ADR + code TODOs → `proposal-suggestions.md`; user picks → `openspec new` + `openspec instructions` → git commit artifacts | ≥1 change has all three artifacts (proposal, design, tasks) committed |
| `deps` | `propose` done | Read all committed changes → generate `.zcf/.deps-output.md` (Mermaid dep graph + recommended execution order) | User confirms (or skips) |
| `spec-done` | `deps` confirmed | Print "run `guide-ship` to proceed"; do NOT auto-invoke | Recommendation printed |

**Files managed (writes):** `openspec/changes/<name>/{proposal,design,tasks}.md`, `proposal-suggestions.md`, `.zcf/.deps-output.md`, git commits on main.

**Files read:** `roadmap.md`, `docs/adr/*`, `docs/architecture/*`, `docs/developer_guide/*`.

**Recovery points** (persisted as inline markdown status markers in `proposal-suggestions.md` — e.g. `status: scan_done`, `status: change_committed` — matching the pattern already used in the current `propose` skill at line ~1201 of `guide.md`): `setup.env_check`, `roadmap.phase_set`, `propose.scan_done`, `propose.change_committed`, `deps.analysis_done`, `spec-done`.

**Refactored from current `guide.md`:** the `setup` (lines 244-339), `roadmap` (lines 343-445), `propose` (lines 448-555), `deps` (lines 559-653) sections. Total ~520 lines lifted with these light edits applied uniformly:

1. Strip all `workflow-state.md` and `workflow-progress.md` read/write logic (these files are deleted)
2. Strip all "current global phase" / "recovery point" cross-references to phases owned by `guide-ship`
3. Replace standalone `skill_use("spec-workflow-propose")` calls with the now-clearly-bounded `propose` sub-skill
4. Strip worktree-creation code (moved to `guide-ship`)

### 6.2 `guide-ship` — Ship-Side State Machine

**Owns:** the chain from "an OpenSpec change is committed" to "code merged to main and archived".

| Phase | Entry condition | Action | Exit condition |
|---|---|---|---|
| `discover` | Invocation or returning from `ship-done` with more changes | Scan `openspec/changes/` (excluding `archive/`) for committed changes; if focus provided, validate; else show list to user. "Batch mode" = user picks option "all" → iterate over every committed change with no worktree, creating one worktree per change in turn | User-selected focus change (single or batch "all") |
| `worktree` | Focus change chosen | COMMIT GATE (`git show HEAD:.../proposal.md` must succeed); create branch `openspec/<name>`; create worktree at `.zcf/<name>-wt/`; verify branch is attached (no detached HEAD) | Worktree verified, branch attached |
| `plan` | Worktree ready | `cd` into worktree; invoke Prometheus `start_work` skill to generate `.sisyphus/plans/<name>.md` | Plan file exists, task count > 0 |
| `execute` | Plan file exists | Call `execute` skill (existing, unchanged behavior) — delegates per-Work-Unit to deep/unspecified-high agents, runs `cmake --build` + ctest, sed-updates `tasks.md` to `[x]` | `tasks.md` has all tasks `[x]` |
| `archive` | All tasks `[x]` | MERGE VERIFICATION GATE → `git checkout main` → `git merge --no-ff openspec/<name>` (or `--ff-only` if no divergence) → POST-MERGE VERIFICATION GATE → `openspec archive <name> --yes` → `git worktree remove` → `git branch -d openspec/<name>` | Archive successful, worktree + branch removed |
| `ship-done` | `archive` done | If more unprocessed committed changes exist → recommend re-invoking `guide-ship`; else "this batch complete" | Recommendation printed |

**Files managed (writes):** `tasks.md` (`[x]` updates), `.sisyphus/plans/<name>.md` (via Prometheus), git commits on `main`, `openspec/changes/archive/<name>/`.

**Files read:** `openspec/changes/<name>/{proposal,design,tasks}.md`, `git worktree list`, `git log openspec/<name>..main`.

**Refactored from current `guide.md`:** the `plan` (lines 657-941), `execute` (lines 944-1059), `status_archive` (lines 1062-1227), `cleanup` (lines 1231-1282) sections. Total ~770 lines lifted with these light edits applied uniformly:

1. Strip all `workflow-state.md` and `workflow-progress.md` read/write logic
2. Strip all candidate-discovery code (already done in `guide-spec.propose`)
3. Strip all "current global phase" references to spec-side phases
4. The plan-phase invocation of Prometheus `start_work` is added here (currently lives in `plan.md`; moves to `guide-ship.plan`)

### 6.3 `guide` — Stateless Recommender

**Owns:** nothing. Recommends which sub-skill to invoke based on on-the-fly project scan.

**Scanning logic (in priority order):**

1. If any `openspec/*` worktree exists AND its `tasks.md` is not fully `[x]` → recommend `guide-ship` (resume execution)
2. Else if any `openspec/*` worktree exists AND its `tasks.md` is fully `[x]` → recommend `guide-ship` (run archive phase)
3. Else if any committed change in `openspec/changes/` (excluding `archive/`) has no worktree → recommend `guide-ship` (start a new change)
4. Else if `roadmap.md` does not exist → recommend `guide-spec` (initialize roadmap)
5. Else if `openspec/changes/` is empty or has no committed changes → recommend `guide-spec` (run propose phase)
6. Else (no changes, roadmap exists) → recommend `guide-spec` (continue roadmap-driven propose)

**Output format:**

```
🔍 Project state scan:
   - roadmap.md: ✅ exists (current phase: phase-2)
   - committed changes: 2 (fix-ns-pollution, add-stream-pipes)
   - worktrees: 1 (fix-ns-pollution, 2/3 tasks done)

💡 Recommended: skill_use("guide-ship")
   Reason: worktree exists with unfinished tasks → resume execution
```

**Constraints:**

- Total file length ≤ 80 lines
- Zero state persistence (no `workflow-state.md` writes)
- Zero `openspec` CLI calls
- Zero git mutations
- Pure read-only scanning of: `roadmap.md` existence, `openspec/changes/` listing, `git worktree list`, `tasks.md` `[x]` count

**Stale state detection (one-time, on first invocation after upgrade):**

If `$PROJECT_ROOT/workflow-state.md` exists from a pre-refactor run, `guide` prints:

```
⚠️  Stale workflow-state.md detected (pre-refactor format).
   This file is no longer used and will be ignored.
   Remove it manually if you want: rm workflow-state.md
```

Does NOT auto-delete (respects user data).

### 6.4 Deletion of `plan.md`

`plan.md` (699 lines) currently does:
- Candidate discovery (scan `openspec/changes/`) → moves to `guide-spec.discover` (or rather, `guide-spec.propose` already does this)
- Phase gating → stays in `guide-spec`
- Change name validation → moves to `guide-ship.discover` (5 lines, trivial)
- Branch + worktree creation → moves to `guide-ship.worktree` (~80 lines lifted)
- Prometheus `start_work` invocation → moves to `guide-ship.plan` (~20 lines, mostly the cd + skill call)

The split is clean: nothing in `plan.md` is shared. After distribution, `plan.md` becomes empty and is deleted.

## 7. Data Flow

### 7.1 Spec-side flow

```
User → guide-spec
  │
  ├─[setup]──→  openspec --version, git status, ls docs/adr/
  │
  ├─[roadmap]──→  read/write roadmap.md
  │
  ├─[propose]──→  reads:  docs/adr/, docs/architecture/, code TODOs,
  │                       proposal-suggestions.md
  │              writes: proposal-suggestions.md
  │              user picks change name
  │              → calls `propose` skill
  │              → openspec new + openspec instructions
  │              → writes openspec/changes/<name>/{proposal,design,tasks}.md
  │              → git add + git commit
  │
  └─[deps]──→  reads:  openspec/changes/*/{proposal,design}.md
              writes: .zcf/.deps-output.md (Mermaid)
              user confirms
              → print "run guide-ship"
```

### 7.2 Ship-side flow

```
User → guide-ship
  │
  ├─[discover]──→  git show HEAD:openspec/changes/<name>/.openspec.yaml
  │                (gate: artifacts must be in HEAD)
  │                user picks focus change
  │
  ├─[worktree]──→  git branch openspec/<name> HEAD
  │                git worktree add .zcf/<name>-wt/ openspec/<name>
  │                worktree verification (no detached HEAD)
  │
  ├─[plan]──→  cd .zcf/<name>-wt/
  │            → calls Prometheus start_work skill
  │            ← .sisyphus/plans/<name>.md
  │
  ├─[execute]──→  cd .zcf/<name>-wt/
  │              → calls `execute` skill
  │              execute loops Work Units:
  │                delegate to deep/unspecified-high
  │                cmake --build + ctest
  │                sed tasks.md ([ ] → [x])
  │
  └─[archive]──→  cd .zcf/<name>-wt/
                  git checkout main
                  git merge --no-ff openspec/<name>
                  merge verification
                  openspec archive <name> --yes
                  git worktree remove .zcf/<name>-wt/
                  git branch -d openspec/<name>
                  → if more changes: print "run guide-ship again"
```

### 7.3 Handoff (spec-done → ship-discover)

The handoff is the **commit of all three change artifacts to main**:

```
spec-done exit guard:
  for each artifact in (proposal, design, tasks):
    if ! git show HEAD:openspec/changes/<name>/<artifact>.md:
      fail "not all artifacts committed — refuse to exit spec-side"

ship-discover entry guard:
  for change in openspec/changes/ (excluding archive/):
    if ! git show HEAD:openspec/changes/<change>/.openspec.yaml:
      skip (treat as in-flight, only show fully-committed changes)
```

This makes git the immutable boundary. No shared state file, no race condition, no "spec is half-written and ship tried to execute" failure mode.

## 8. Error Handling

| Scenario | `guide-spec` response | `guide-ship` response |
|---|---|---|
| User invokes wrong skill for current state | (N/A — assumes user chose deliberately) | Same |
| `workflow-state.md` exists (pre-refactor) | Print warning, continue | Same |
| worktree directory conflict (`.zcf/<name>-wt` exists but not in worktree list) | N/A | Refuse; print `rm -rf .zcf/<name>-wt` command |
| Change artifacts incomplete (e.g. proposal exists but tasks.md missing) | Refuse to enter `spec-done`; print "complete propose first" | Refuse to enter `discover`; print "finish via guide-spec" |
| `git show HEAD:` fails (no commits yet) | Refuse; print "make an initial commit first" | Same |
| Multiple independent changes for parallel execution | N/A (spec-side doesn't care) | User picks "batch" in `discover`; each gets its own worktree |
| Merge conflict in `archive` | N/A | Print conflict details; recommend `git status`; user resolves manually and re-invokes `guide-ship` |
| Prometheus `start_work` fails | N/A | Refuse to enter `execute`; print "fix plan generation and re-invoke" |

## 9. Testing

This is a refactor — the underlying skill behaviors (`propose`, `execute`, `archive`) are unchanged. Testing strategy:

1. **Smoke test the recommender:** invoke `guide` in a project with various states (no roadmap, has changes, has worktrees, all archived) and verify correct recommendation.
2. **Smoke test `guide-spec`:** invoke in a fresh project, walk through setup → roadmap → propose, verify a change gets committed. Compare artifact contents with current `guide` output.
3. **Smoke test `guide-ship`:** invoke on a project with a committed change, verify worktree creation, plan generation, execution (on a trivial change), and archive. Compare with current `guide` output.
4. **Stale state handling:** drop a fake `workflow-state.md` into a test project, invoke `guide`, verify warning is printed and behavior is unaffected.
5. **Boundary enforcement:** manually create a half-written change (only `proposal.md`, no `tasks.md`), invoke `guide-ship`, verify it refuses to discover it and points back to `guide-spec`.

No automated test framework exists for these skills (they are documentation-driven). Testing is manual run-through.

## 10. Migration Path

For users upgrading from pre-refactor version:

1. Pull the new code.
2. If `workflow-state.md` exists: it will be ignored; the `guide` recommender prints a one-time warning. User may `rm` it manually.
3. If user was mid-flight (e.g. created artifacts but no worktree yet): invoke `guide-spec` to finish propose, then `guide-ship` to start execution. The recommender will point them correctly.
4. No data migration needed: `openspec/changes/` contents are git-versioned and remain authoritative.

## 11. Open Questions

None — all four design questions were resolved during brainstorming:

1. **Plan skill fate:** delete and distribute
2. **State file structure:** none (YAGNI; each side uses its own files)
3. **Naming:** `guide-spec`, `guide-ship`, `guide` (recommender)
4. **Backward compatibility:** complete rewrite, no alias, no warning beyond the one-time stale-state notice

## 12. Definition of Done

- [ ] `skills/guide-spec.md` exists, ≤ 800 lines
- [ ] `skills/guide-ship.md` exists, ≤ 900 lines
- [ ] `skills/guide.md` exists, ≤ 80 lines, contains no `openspec` CLI calls
- [ ] `skills/plan.md` deleted
- [ ] `skills/{propose,execute,status,roadmap,deps}.md` headers updated to clarify caller
- [ ] `README.md` and `USAGE.md` updated with three new entry points
- [ ] `INSTALL.md` lists three new skills
- [ ] Manual smoke tests pass for all three skills
- [ ] Stale state warning verified
- [ ] No regressions: existing `propose`/`execute`/`status` skill behaviors unchanged
