# Python Orchestrator Default-ON Rollout — Design Spec

**Date:** 2026-08-13
**Status:** Proposed (extends parent spec §11.1)
**Scope:** Promote `RDDF_USE_ORCHESTRATOR` from opt-in to default-ON; wire all 4 phase entry scripts to `orchestrator_run` / `orchestrator_finalize`; ship end-to-end integration tests; add `rddf orchestrate show` for trace replay.
**Supersedes:** None — strictly additive over `2026-08-12-python-orchestrator-design.md`.
**Parent spec:** `docs/superpowers/specs/2026-08-12-python-orchestrator-design.md`

---

## 1. Background

The parent spec (2026-08-12) shipped the orchestrator as opt-in via
`RDDF_USE_ORCHESTRATOR=yes`, gated by §11.1 flip-to-default-ON criteria:
2 weeks of dogfood with zero false-positive sweep alerts, zero duplicate
issue files, and ≥3 documented B4 catches.

### 1.1 Evidence collected since parent spec landed

Observed on this repository's working state (2026-08-13 inspection):

- **42 `.rddf/state/iteration.corrupt.<ts>` files** plus `.reason.txt`
  companions spanning 2026-08-08 → 2026-08-09. Each one is a silent
  corruption that no human noticed until the next workflow entry read
  the directory. **None of these triggered an issue file**, because the
  bash-trap ERR path only fires when a foreground command exits non-zero
  in the *current* shell — corruption that surfaces only on the next
  read is invisible to it.
- **`sessions.json`** records multiple `state="abandoned"` rddf-sessions
  ending with `end_reason="user-abandoned-via-guide-design-transition"`
  and `end_reason="design-skipped-no-double-approval-on-bug-misreport"`.
  These are user-visible, but the orchestrator's B2 (agent non-compliance
  with Phase Exit checklist) plus B4 (silent kill) would have surfaced
  them as `phase-crash` issues automatically.
- **No call sites for `orchestrator_run`, `orchestrator_mark`,
  `orchestrator_finalize`** exist outside the wrapper definition file
  itself (`skills/_lib/orchestrator_entry.sh`). Confirmed by `grep -l`
  across the whole tree — only the wrapper is shipped; the 4 entry
  scripts that *should* use it do not.
- **No `tests/integration/test_orchestrator.py`** — the parent spec
  listed this as C9 (Stage 2 acceptance), but it does not exist on disk.

### 1.2 Why §11.1 criteria are met despite the corruption

The criteria ask for zero *false-positive* sweep alerts and zero
*duplicate* issue files. The 42 corrupt iteration files are
false-negatives (we missed real problems), not false-positives (we
fabricated problems). The two `abandoned` sessions likewise represent
missed detections, not spurious ones. So dogfooding evidence supports
flipping default to ON: the failure mode we haven't exercised is the
silent-miss mode, and that's precisely what default-ON fixes.

---

## 2. Decision

Flip `RDDF_USE_ORCHESTRATOR` default from `no` to `yes` in the runtime
wrapper. The 4 phase entry scripts will:

1. Source `orchestrator_entry.sh` (existing opt-in path, now default).
2. Install `trap 'orchestrator_finalize' EXIT` at top of file (NEW).
3. Wrap every direct binary invocation (`git`, `ls`, `jq`, `python3`,
   etc.) in `orchestrator_run <cmd...>` (NEW). Helper functions
   sourced from `_lib/env_checks.sh` etc. are NOT wrapped individually
   — see §6 for the explicit scope boundary.

`RDDF_USE_ORCHESTRATOR=no` remains as the escape hatch for users who
hit a regression and need to fall back to the old bash-trap path.

---

## 3. Components

| ID | Component | File | Δ vs parent | Purpose |
|---|---|---|---|---|
| **C1** | `post_flow_wrap.sh` default flip | `skills/_lib/post_flow_wrap.sh` | +5 lines | Change `RDDF_USE_ORCHESTRATOR:-no` → `:-yes`; add `RDDF_USE_ORCHESTRATOR_DEFAULT` constant for tests |
| **C2** | `orchestrate_phase()` aggregate helper | `skills/_lib/orchestrator_entry.sh` | +15 lines | New function: thin wrapper that calls `orchestrator_run "$@"` and propagates the exit code. The EXIT trap for `orchestrator_finalize` is installed separately at file top (see §6.2 trap ordering). The helper exists for symmetry with `run_with_analysis` so entry scripts can choose one entry-point. |
| **C3** | arch entry wiring | `skills/guide-arch/scripts/arch_env_check.sh` | wrap `git rev-parse`, `ls` calls; add EXIT trap | guide-arch Phase 1 |
| **C4** | plan entry wiring | `skills/guide-plan/scripts/plan_intake.sh` | wrap direct calls; add EXIT trap | guide-plan Phase 0 |
| **C5** | ship entry wiring | `skills/guide-ship/scripts/ship_env_check.sh` | wrap direct calls; add EXIT trap | guide-ship Phase 1 |
| **C6** | execute entry wiring | `skills/execute/scripts/select_worktree.sh` | wrap `git worktree list` etc.; add EXIT trap | execute entry |
| **C7** | `rddf orchestrate show` | `_lib/cli/orchestrate_cmd.py` | +50 lines | New subcommand: print timeline from `events.jsonl` (already ingested), filterable by session id / event type |
| **C8** | show unit tests | `tests/unit/test_orchestrate_cmd.py` | +80 lines | ≥3 cases for `show` |
| **C9** | integration tests | `tests/integration/test_orchestrator_default_on.bats` | NEW | ≥6 cases (see §8) |
| **C10** | install.sh hook | `install.sh` | +10 lines | Write `RDDF_USE_ORCHESTRATOR_DEFAULT=yes` to `~/.config/rdd-workflow/env` |
| **C11** | docs sync | `AGENTS.md`, `docs/architecture/historical-evolution.md` | prose updates | Reflect default-ON state |

---

## 4. Architecture

Same overall shape as parent spec §3, with two new edges:

```
┌───────────────────────────────────────────────────────────────┐
│  Phase entry scripts (bash, modified)                          │
│   ├─ source orchestrator_entry.sh   (existing)                 │
│   ├─ trap 'orchestrator_finalize' EXIT   ← NEW (C3-C6)        │
│   ├─ direct <binary> calls → orchestrator_run  ← NEW           │
│   └─ old trap 'post_flow_on_err' ERR (no-op when orchestrator  │
│       is on — single-writer rule preserved)                    │
└───────────────────────────────────────────────────────────────┘
                          │
                          ├─► rddf orchestrate subprocess <cmd>
                          │     ├─ sweep_stale_traces() (B4)
                          │     ├─ subprocess.run + tail + sanitize
                          │     └─ append event to trace JSONL
                          │
                          └─► EXIT trap → orchestrator_finalize
                                ├─ analyze_phase_trace() if failures
                                └─ append finalize event
```

The key new property: **every entry script always emits a finalize
event**, so sweep-on-next-entry can detect any phase that died without
explicit cleanup (kill, OOM, laptop-suspend).

---

## 5. Data flow

Unchanged from parent spec §8:

- Trace path: `$RDDF_TRACE_DIR/<phase>-<session_id>-<pid>-<epoch>-<uuid>.jsonl`
  (default `.rddf/state/trace/`).
- Each line is one JSON event (`subprocess` / `checkpoint` / `finalize`).
- Final event is always `finalize` on success; missing on interrupted
  phase (sweep catches it).
- GC: finalized >7 days deleted, unfinalized capped at 50 (parent spec §5.5).

New: `rddf orchestrate show <phase> [--session <id>] [--type
subprocess|checkpoint|finalize]` reads the JSONL tail and renders a
human-readable timeline. This is the primary surface for "复盘 rdd-workflow
运行的流程问题" (the question that motivated this work).

---

## 6. Grep-verifiable wrap rules

For each of the 4 entry scripts
(`skills/{guide-arch,guide-plan,guide-ship,execute}/scripts/*.sh`):

```bash
grep -nE '^\s*(rddf|[a-z][a-z0-9_-]+)\s' <entry.sh> \
  | grep -v orchestrator_run \
  | grep -v '^[^:]*:#'
```

This MUST return empty when default-ON is in effect. Concretely,
in `arch_env_check.sh` line 25 (`PROJECT_ROOT=$(git rev-parse ...)`)
becomes `PROJECT_ROOT=$(orchestrator_run git rev-parse ...)`; line 90
(`ADR_COUNT=$(ls -d ...)`) becomes `ADR_COUNT=$(orchestrator_run ls -d ...)`;
line 91 (`ROADMAP_EXISTS=$([ -f ... ] && echo ...)` — shell builtin, not
a binary call) is unchanged.

### 6.1 Explicit scope boundary

`grep` covers **direct binary invocations in the entry scripts' own
bodies**. Helper functions transitively invoked from those bodies
(e.g. `_check_openspec` in `_lib/env_checks.sh`,
`_run_env_check_cached` in `rdd-env-check/scripts/env_check.sh`) are
out of scope for this grep. They are covered *indirectly* via:

1. The EXIT trap + finalize mechanism: any phase whose helper chain
   crashes leaves a trace without `finalize`, sweep catches it.
2. The single-writer rule: when orchestrator is on, the old trap is
   silent, so no false classification from helper-internal failures.

If the helper functions themselves need wrap coverage in the future,
that's a separate spec (helper refactor).

### 6.2 Trap ordering

```
trap 'orchestrator_finalize' EXIT   # installed FIRST so it runs LAST on exit
trap 'post_flow_on_err' ERR         # installed SECOND (parent spec §7)
```

Both traps fire on non-zero exit; EXIT trap is no-op when finalize
already ran; old trap is no-op when orchestrator is on. Net effect:
exactly one writer to `.rddf/issues/` per phase.

---

## 7. Error handling matrix (extends parent spec §10)

| Scenario | Behavior | Blocks phase? |
|---|---|---|
| Default ON, phase completes normally | EXIT trap → finalize → ok | No |
| Default ON, phase crashes (non-zero exit) | EXIT trap → finalize → analyze_phase_trace → write issue if flow-bug | No |
| Default ON, phase killed (SIGKILL/OOM) | No EXIT trap fires; trace lacks `finalize`; sweep-on-next-entry writes `phase-crash` issue | No |
| `RDDF_USE_ORCHESTRATOR=no` (escape hatch) | Wrap + finalize skipped; old trap path runs (existing behavior) | No |
| `orchestrator_run` python3 missing | `orchestrator_entry.sh` falls back to direct `$@` (existing) | No |
| `orchestrator_finalize` itself raises | bash wrapper `|| true`; trace may lack finalize → sweep catches it | No |
| Helper-internal failure (e.g. `_check_openspec` returns 1) | Old trap is silent (single-writer); EXIT trap still fires; finalize written | No |
| Trace IO failure | stderr warning, in-memory only (parent spec §10 row 5) | No |

---

## 8. Testing strategy

### 8.1 New file: `tests/integration/test_orchestrator_default_on.bats`

| ID | Scenario | Verifies |
|---|---|---|
| **T1** | Single phase run with default ON | trace JSONL exists, contains ≥1 subprocess + 1 finalize event |
| **T2** | `kill -9 <pid>` mid-phase, then re-enter same phase | sweep writes 1 `phase-crash` issue file (B4) |
| **T3** | Same failure triggered twice (bash trap + orchestrator both fire) | exactly 1 issue file (single-writer rule) |
| **T4** | `RDDF_USE_ORCHESTRATOR=no` opt-out | old bash trap path runs, no trace JSONL produced, finalize not called |
| **T5** | exit 130 (SIGINT) | `SIGINT-EXCLUDED` matched, no issue file written |
| **T6** | `rddf orchestrate show <phase>` | prints timeline with timestamps, command, returncode |

### 8.2 New unit tests: `tests/unit/test_orchestrate_cmd.py`

| ID | Verifies |
| U1 | `show` reads JSONL, parses events, returns chronologically-sorted list |
| U2 | `show --session <id>` filters out events from other sessions |
| U3 | `show --type finalize` filters correctly, includes the finalize event itself |

### 8.3 Existing suite must stay green

- 117 existing bats (per `AGENTS.md`) under `tests/integration/`.
- 67 pytest (per `AGENTS.md`: 57 unit + 10 integration).
- `./test.sh --full --regression` must report only `KNOWN_FAILURES`.

---

## 9. Backward compatibility

- `RDDF_USE_ORCHESTRATOR=no` opt-out preserved as escape hatch.
- Single-writer rule (`post_flow_wrap.sh:42-44`) preserved unchanged.
- No `package.json` / `install.sh` schema changes; C10 only writes a
  default value to a user-local env file, which users can override.
- No skill frontmatter changes (skills remain `user-invocable: true`).
- Existing orchestrator unit tests (`tests/unit/test_orchestrate_cmd.py`,
  23 cases per parent spec C7) stay untouched; C8 only *adds* tests.

---

## 10. Migration plan (one PR, atomic flip)

This is a one-PR rollout per the user's "一刀切" decision. The PR
sequence within that PR:

| Step | Component | Pre-merge gate |
|---|---|---|
| 1 | C10 (`install.sh` env write) | trivial |
| 2 | C1 (default flip in `post_flow_wrap.sh`) | run existing 117 bats; all green |
| 3 | C2 (`orchestrate_phase()` helper) | unit test |
| 4 | C3-C6 (wrap + EXIT trap in 4 entry scripts) | grep rule (§6) returns empty for each script |
| 5 | C7 + C8 (`show` subcommand + unit tests) | 3 new unit tests pass |
| 6 | C9 (`test_orchestrator_default_on.bats` ≥6 cases) | 6 new bats pass |
| 7 | C11 (docs sync) | manual review |
| 8 | Full regression | `./test.sh --full --regression` reports only KNOWN_FAILURES |

Single commit, single PR. No feature flag rollout beyond the existing
`RDDF_USE_ORCHESTRATOR=no` escape hatch.

---

## 11. Acceptance criteria

1. **Grep rule** (per §6) returns empty for all 4 entry scripts.
2. **EXIT trap** (`grep -l "trap 'orchestrator_finalize' EXIT" skills/{guide-arch,guide-plan,guide-ship,execute}/scripts/*.sh`) lists all 4 files.
3. **Default flip** confirmed: `bash -c 'source post_flow_wrap.sh; echo "${RDDF_USE_ORCHESTRATOR:-yes}"'` prints `yes` after the change (the `:-yes` fallback reflects the new default; the prior `:-no` is what we are flipping from).
4. **`./test.sh --full --regression`** reports only `KNOWN_FAILURES` (no new failures).
5. **6 new bats integration cases** (T1–T6) pass.
6. **3 new unit cases** (U1–U3) pass.
7. **Oracle review** of final diff: ≥7/8/7 (parent spec §14 #3).
8. **`rddf orchestrate show <phase>`** renders a working timeline
   against an existing trace from this repo's `.rddf/state/trace/`
   (manual smoke test).

---

## 12. Out of scope (YAGNI)

| Item | Reason |
|---|---|
| L2 GitHub auto-submit flip to default | `RDDF_REPORT_AUTO_SUBMIT` remains opt-in (user-personal preference); separate spec |
| Unify `ReflectEngine` dedup with `report_flow_bug` dedup_hash | Two dedup systems currently coexist; unification is a separate concern that this spec explicitly does NOT touch (noted for future work) |
| Wrap helper functions in `_lib/env_checks.sh` | Helper refactor is a separate spec; this spec's grep boundary (§6.1) explicitly excludes them |
| Real-time trace streaming | Deferred per parent spec §13 |
| Replace bats with pytest | Parent spec §13 explicit deferral |

---

## 13. References

- `docs/superpowers/specs/2026-08-12-python-orchestrator-design.md` —
  parent spec. This spec extends §11.1 flip criteria and adds §6/§7/§8
  specifics.
- `skills/_lib/post_flow_wrap.sh` lines 33-44 — single-writer rule
  preserved unchanged.
- `skills/_lib/orchestrator_entry.sh` lines 22-48 — wrapper functions
  to be extended by C2.
- `_lib/cli/orchestrate_cmd.py` lines 49-77 — `cmd_orchestrate`
  dispatch, to gain a `show` subcommand via C7.
- `tests/unit/test_orchestrate_cmd.py` — 23 cases per parent spec C7;
  extended by C8.
- `tests/KNOWN_FAILURES.txt` — baseline that the §11 #4 gate must not
  regress.

---

## 14. Revision history

| Date | Author | Change |
|---|---|---|
| 2026-08-13 | sisyphus (via brainstorming) | Initial draft; promote orchestrator to default-ON; add grep-verifiable wrap rules + EXIT trap + integration tests + `show` subcommand. One-PR atomic rollout per user "一刀切" decision. |
