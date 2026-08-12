# Python Orchestrator + Bash Leaf — Design Spec

**Date:** 2026-08-12
**Status:** Approved (Oracle review SHIP-WITH-FIXES, 5 corrections integrated)
**Scope:** Replace `bash trap ERR` post-flow detection with a Python orchestrator that supervises subprocess execution; introduce crash-survivable stale-trace detection; close the SIGKILL / agent-noncompliance blind spot.
**Target Branch:** `master`
**Supersedes:** None (additive — keeps `post_flow_wrap.sh` as fallback)
**Related:** ADR-0027 (§1.0 two-plane architecture, §1.2 three-stage classification), ADR-0016 (env-var override convention), ADR-0024 (handoff schema patterns)

---

## 1. Background

`rdd-workflow` v2.1 ships **ADR-0027** (Continuous Evolution Feedback Loop), which
classifies phase failures via `_lib/post_flow_analysis.classify_phase_outcome` and
writes flow-bug issues via `report_flow_bug`. The **detection trigger** for script-plane
failures is a bash `trap ERR` handler in `skills/_lib/post_flow_wrap.sh`, wired into
4 phase entry scripts (`arch_env_check.sh`, `plan_intake.sh`, `ship_env_check.sh`,
`select_worktree.sh`).

### 1.1 Known blind spots (current design)

| # | Blind spot | Root cause | Severity |
|---|------------|-----------|----------|
| **B1** | Sub-scripts that don't `source post_flow_wrap.sh` never fire the trap | bash `trap ERR` only affects commands in the SAME shell session after registration | High |
| **B2** | Agents don't always comply with `Phase Exit` instruction to call `rddf report-issue` | SKILL.md prose is not enforced; agent autonomy | Medium |
| **B3** | Intermediate "silent corruption" (exit 0 but state already broken) is missed | trap only checks `$?` per command | Medium |
| **B4** | **SIGKILL / OOM / laptop-close** — zero signal, no trap, no finalize | Process died before any hook could fire | **Critical** (newly identified by Oracle) |

The current design was Oracle-reviewed (8/8/7 in ADR-0027) but did not consider B4.
Oracle review on this proposal (2026-08-12): **SHIP-WITH-FIXES**, 5 corrections.

### 1.2 Why Path B (and not A/C)

Three candidate paths were evaluated:

| Path | Description | Verdict |
|------|-------------|---------|
| A | Full Python rewrite of all `skills/*/scripts/*.sh` (~10K lines + 117 bats tests) | ❌ 2-4 person-months, v3.0 breaking change |
| **B** | **Python orchestrator supervises bash leaf scripts via `subprocess.run`; bash scripts unchanged** | ✅ ~2 person-weeks, additive, no breakage |
| C | Extend existing `event_log.py` only | ❌ Doesn't fix B1 (sub-scripts that don't emit events still invisible) |

Path B is the only one that closes **B1** while preserving the bash scripts that
work. **B4** (SIGKILL) requires additional crash-survivable detection (see §5).

---

## 2. Decision

Introduce a **Python orchestrator** that:

1. Lives as a new `rddf orchestrate` subcommand (reuses existing `_lib/cli/` dispatch).
2. Wraps each phase subprocess invocation with `subprocess.run`, capturing exit code,
   timing, and tail-of-stdout / tail-of-stderr to a JSONL trace file.
3. Runs a **stale-trace sweep** on first invocation per phase entry, classifying
   unfinalized traces from killed phases as `phase-interrupted` (covers B4 + B2).
4. Sanitizes trace content via existing `loop/sanitizer.sanitize()` before write.
5. Keeps `post_flow_wrap.sh` as fallback — single-writer rule disables it when
   `RDDF_USE_ORCHESTRATOR=yes`.

The orchestrator's **headline feature is crash-survivability**, not "more capture".
The reframing is critical for product narrative and for prioritising implementation work.

---

## 3. Architecture

```
┌──────────────────────────────────────────────────────────────┐
│  Phase entry scripts (bash, 现有)                            │
│    source skills/_lib/post_flow_wrap.sh  (existing, fallback)│
│    source skills/_lib/orchestrator_entry.sh (NEW)            │
│    RDDF_USE_ORCHESTRATOR=yes → orchestrator path             │
│    default                       → trap path (unchanged)     │
└──────────────────────────────────────────────────────────────┘
                          │
                          ├──── 老路径 (默认)
                          │     bash trap ERR
                          │         ↓
                          │     post_flow_on_err (existing)
                          │
                          └──── 新路径 (env var 启用)
                                orchestrator_entry.sh sourced
                                    ↓
                          ┌─────────────────────────┐
                          │ rddf orchestrate        │
                          │  --subprocess <cmd>     │
                          │   ↓                     │
                          │ sweep_stale_traces() ← ─┤  (B4 修复)
                          │   ↓                     │
                          │ subprocess.run          │
                          │   stdout/stderr → tmp   │
                          │   read tail 4KB         │
                          │   sanitize() ←──────    │  (security)
                          │   append to trace       │
                          │  --finalize             │
                          │   ↓                     │
                          │ analyze_phase_trace()   │  (B3 部分)
                          │   ↓                     │
                          │ classify + report_flow_bug │
                          └─────────────────────────┘
```

**Why both paths coexist**:

- Existing bash scripts in 117 bats tests continue working unchanged.
- New path is opt-in via `RDDF_USE_ORCHESTRATOR=yes`; default remains trap.
- Single-writer rule: when new path is enabled, `post_flow_on_err` no-ops (no
  duplicate issue file risk; see §7).

---

## 4. Components

| ID | Component | Location | Lines (est) | Behavior |
|----|-----------|----------|-------------|----------|
| **C1** | `rddf orchestrate` CLI | `_lib/cli/orchestrate_cmd.py` + registered in `_lib/cli/__main__.py` | ~250 | Subcommands: `--subprocess` / `--mark-checkpoint` / `--finalize` / `--sweep-stale-traces` |
| **C2** | Bash wrapper | `skills/_lib/orchestrator_entry.sh` | ~50 | Functions `orchestrator_run` / `orchestrator_mark` / `orchestrator_finalize`; forwards to C1 via env vars |
| **C3** | Trace analyzer | `_lib/post_flow_analysis.py::analyze_phase_trace` (NEW function) | ~120 | Reads JSONL, detects cumulative failure, returns Classification + calls `report_flow_bug` |
| **C4** | Existing bash scripts | `skills/*/scripts/*.sh` | 0 changes | Fully backward-compatible |
| **C5** | Single-writer guard | `skills/_lib/post_flow_wrap.sh` (modify `post_flow_on_err`) | +5 lines | Check `RDDF_USE_ORCHESTRATOR=yes` → return 0 (no-op) |
| **C6** | SKILL.md checklist update | 4 files: `skills/guide-{arch,plan,ship}/SKILL.md` + `skills/execute/SKILL.md` | ~30 per file | Replace prose Phase Exit with 3-rule checklist (see §6) |
| **C7** | Unit tests | `tests/unit/test_orchestrate_cmd.py` (NEW) | ~180 | ≥12 cases: subprocess capture / sanitize / sweep / finalize / single-writer |
| **C8** | Unit tests extension | `tests/unit/test_post_flow_analysis.py` (extend) | ~80 | ≥3 multi-step cumulative-failure fixtures |
| **C9** | Python integration | `tests/integration/test_orchestrator.py` (NEW) | ~120 | ≥5 cases: real phase commands → trace → analyze |
| **C10** | bats regression | existing 117 tests | 0 changes | Validate trap path still works when env var unset |

**Total new code**: ~830 lines Python + ~80 lines bash + 4 SKILL.md edits.

---

## 5. Stale-trace sweep — the centerpiece (B4 fix)

### 5.1 The problem

A phase script killed by SIGKILL / OOM / `kill -9` / laptop-suspend leaves:
- No trap fired (process is dead)
- No `report-issue` called (agent is dead)
- No `finalize` event in trace (we never got there)

Today: zero signal. Lost failure mode.

### 5.2 The solution

On **first `--subprocess` call per phase entry**, sweep `.rddf/state/trace/` for
JSONL files matching:
- Same `<phase>` name
- No `finalize` event at end
- Last event timestamp > 5 minutes old

For each match: classify as `phase-interrupted` (new `phase-crash` subcategory per
ADR-0027 §1.1), call `report_flow_bug`, then **unlink the stale trace** (idempotency).

### 5.3 Why this also fixes B2

Agent plane non-compliance (B2) means the agent never called `orchestrator_finalize`.
Result: trace file lacks `finalize` event → sweep catches it on the **next** entry.
The detection is automatic; agent compliance becomes a nice-to-have rather than a
load-bearing assumption.

### 5.4 Sweep implementation

```python
# _lib/cli/orchestrate_cmd.py — invoked by --subprocess first call
def sweep_stale_traces(trace_dir: Path, current_phase: str, max_age_min: int = 5):
    for trace in trace_dir.glob(f"{current_phase}-*.jsonl"):
        events = read_jsonl_tail(trace)
        if not events:
            continue
        if has_finalize_event(events):
            continue
        last_ts = parse_iso(events[-1]["ts"])
        if (utc_now() - last_ts).total_seconds() < max_age_min * 60:
            continue
        # Stale → report + cleanup
        cls = classify_interrupted_phase(trace, events)
        report_flow_bug(cls, project_root=...)
        trace.unlink()
        log_info(f"swept stale trace: {trace.name}")
```

### 5.5 Trace GC

To prevent trace directory unbounded growth:

- **Finalized traces** older than 7 days → delete on sweep
- **Unfinalized traces** older than 24 hours and not in current phase → delete on sweep
- Cap: max 50 unfinalized traces; oldest deleted first if exceeded

---

## 6. SKILL.md Phase Exit checklist (B2 reinforcement)

Replace prose in 4 SKILL.md files with a **3-rule checklist**. Agents follow
checklists measurably better than prose (Oracle observation).

```markdown
## Phase Exit — Post-Flow Analysis (Agent 平面, ADR-0027 §1.0)

### Checklist (must satisfy exactly one)

- [ ] **Normal exit** → orchestrator_finalize (always)
- [ ] **Abnormal exit** → orchestrator_finalize + `rddf report-issue --phase <p> --exit <code> "<one-line>"`

### Triggers for "abnormal exit" (non-exhaustive)

- gate reports CRITICAL and it's not a usage-error / environment-error
- state machine branch enters an unexpected case
- agent cannot continue after 3 retries on the same step
- user explicitly says "this is wrong" while phase reports success

### NOT abnormal (do NOT report-issue)

- User-initiated SIGINT / SIGTERM (exit 130/143)
- Missing tools, network errors, permission errors (environment-error)
- Bad CLI flags, missing required arguments (usage-error)
```

---

## 7. Single-writer rule (avoid duplicate issue files)

**Problem**: if both trap path and orchestrator path fire on same failure, they
construct different `description` strings (different stderr tails, different
classifiers) → different `dedup_hash` → **two issue files written**.

**Fix**: when `RDDF_USE_ORCHESTRATOR=yes`, the trap path no-ops:

```bash
# skills/_lib/post_flow_wrap.sh (modified post_flow_on_err)
post_flow_on_err() {
    local code=$?
    [ "$code" -eq 0 ] && return 0
    [ "$code" -eq 130 ] && return 0
    [ "$code" -eq 143 ] && return 0

    # NEW: single-writer rule
    if [ "${RDDF_USE_ORCHESTRATOR:-no}" = "yes" ]; then
        return 0  # orchestrator owns this phase's reporting
    fi

    # ... existing trap logic unchanged ...
}
```

**Verification**: integration test in `tests/integration/test_orchestrator.py` runs
a failing command under both modes and asserts exactly one issue file is written.

---

## 8. Data contract

### 8.1 Trace file format

Path: `.rddf/state/trace/<phase>-<session_id>-<pid>-<epoch>.jsonl` (gitignored).

`<session_id>` is `owner_opencode_session_id` from `.rddf/state/sessions.json`,
or a fresh UUID v4 if no rddf-session is bound (per ADR-0017 fallback).

Env override: `RDDF_TRACE_DIR` (default `.rddf/state/trace/`).

Each line is one JSON event:

```jsonl
{"ts":"2026-08-12T10:00:00Z","type":"subprocess","cmd":["arch_gap_analysis.sh"],"returncode":0,"stdout_tail":"...","stderr_tail":"","duration_ms":120}
{"ts":"2026-08-12T10:00:01Z","type":"checkpoint","name":"after-setup","state_marker":"phase_started"}
{"ts":"2026-08-12T10:00:02Z","type":"subprocess","cmd":["arch_done_gate.sh"],"returncode":1,"stdout_tail":"...","stderr_tail":"ERROR: ...","duration_ms":340}
{"ts":"2026-08-12T10:00:03Z","type":"finalize","subprocess_failures":1,"checkpoints":1,"report_written":"true","issue_file":".rddf/issues/flow-bug-a1b2c3d4.md"}
```

### 8.2 Field constraints

- Each event < 4 KB (POSIX atomic-append guarantee; see §9.3)
- `stdout_tail` / `stderr_tail`: **sanitized** before write (see §9.1)
- Final trace file always ends with a `finalize` event (success or failure path)

### 8.3 Why JSONL

- Append-only, crash-safe (each write is atomic for small events)
- Same format as existing `_lib/core/event_log.py` (consistency)
- Readable by `jq` for debugging
- No migration cost from bash-side parsing

---

## 9. Security & performance

### 9.1 Trace content sanitization [MEDIUM severity, fix]

**Problem**: writing raw `stdout_tail` / `stderr_tail` to disk creates a new
unsanitized sink. Test outputs routinely contain API tokens in URLs, env dumps,
private paths.

**Fix**: pipe both tails through `loop/sanitizer.sanitize()` before JSONL write.
This is the same sanitizer used by `report_flow_bug` → `.rddf/issues/`.

```python
from skills._lib.loop.sanitizer import sanitize

stdout_tail = sanitize(stdout_tail)
stderr_tail = sanitize(stderr_tail)
```

### 9.2 Subprocess invocation [LOW severity, default OK]

`subprocess.run(cmd_list, shell=False, ...)` with argv-list is safe from shell
injection of the command itself. Threat model: local dev tool, agent already
trusted to run arbitrary bash. No command whitelist needed.

### 9.3 Concurrency

Trace filenames include `<pid>-<epoch>` for uniqueness. No flock needed because:
- POSIX `O_APPEND` writes < PIPE_BUF (4096 bytes) are atomic
- Trace events kept < 4 KB to guarantee atomicity
- Parallel worktrees have separate project roots anyway

### 9.4 Memory

Avoid `capture_output=True` for commands with potentially large output (e.g.,
`./test.sh --full` produces ~MBs). Use temp files + tail reading:

```python
stdout_tmp = tempfile.NamedTemporaryFile(mode='w', delete=False)
stderr_tmp = tempfile.NamedTemporaryFile(mode='w', delete=False)
try:
    proc = subprocess.run(
        cmd_list,
        shell=False,
        stdout=stdout_tmp,
        stderr=stderr_tmp,
        timeout=cmd_timeout,
    )
    stdout_tail = tail_file(stdout_tmp.name, n=4096)
    stderr_tail = tail_file(stderr_tmp.name, n=4096)
finally:
    stdout_tmp.close(); os.unlink(stdout_tmp.name)
    stderr_tmp.close(); os.unlink(stderr_tmp.name)
```

Add explicit `timeout=` to every `--subprocess` call (default: phase-default
from env var `RDDF_ORCHESTRATE_TIMEOUT`, fallback 600s).

---

## 10. Error handling matrix

| Scenario | Behavior | Blocks phase? |
|----------|----------|---------------|
| Python unavailable | bash wrapper detects `command -v python3`; stderr warning; falls back to trap path | No |
| Orchestrator CLI crashes | `\|\| true` wrap in bash wrapper; trace lost but phase continues | No |
| `subprocess.run` timeout | log `timeout: true` to trace event; phase returns 124 | Yes (preserves original code) |
| `analyze_phase_trace` exception | caught, warning appended to trace, finalize exit code unchanged | No |
| Trace file IO failure | stderr warning, silent degrade to in-memory only (lose data, don't crash) | No |
| `RDDF_USE_ORCHESTRATOR=yes` but Python missing | stderr warning + silent fallback to trap | No |
| Sanitizer raises | caught, fallback to truncated raw tail with warning | No |
| Stale trace sweep on a live trace (race) | mtime check + atomic rename before read | No |

---

## 11. Backward compatibility

- **Default**: `RDDF_USE_ORCHESTRATOR` unset → existing trap path runs unchanged.
- **Opt-in**: `export RDDF_USE_ORCHESTRATOR=yes` → orchestrator path active for
  that session. Trap path no-ops (single-writer rule, §7).
- **No `.rddf/` schema changes** required by users.
- **No SKILL.md breaking changes** — Phase Exit sections are clarifications, not
  behavioral changes.
- **No package.json / install.sh changes** — Python is already required (v2.0
  Loop engine on Python 3.11+).

### 11.1 Flip-to-default-ON criteria

The new path should remain opt-in for at least **2 weeks of dogfooding on this
repository** with:
- Zero false-positive issue files (`phase-interrupted` from sweep)
- Zero duplicate issue files (single-writer rule verified)
- At least 3 distinct catches of B4-class failures (SIGKILL/OOM) that the trap
  path would have missed

After criteria met, default flips to ON via a follow-up PR.

---

## 12. Migration plan (3 stages, ~2 person-weeks)

### Stage 1: Orchestrator core (4 days)

- C1 `_lib/cli/orchestrate_cmd.py` (--subprocess, --mark-checkpoint, --finalize)
- C2 `skills/_lib/orchestrator_entry.sh`
- C5 single-writer guard in `post_flow_wrap.sh`
- C7 `tests/unit/test_orchestrate_cmd.py` (≥12 cases)

**Acceptance**:
- `rddf orchestrate --subprocess echo hello` returns hello, trace written
- `rddf orchestrate --subprocess sh -c "exit 1"` records returncode=1
- 117 existing bats tests still pass (regression)

### Stage 2: Trace analyzer + stale sweep + SKILL.md (4 days)

- C3 `_lib/post_flow_analysis.py::analyze_phase_trace` (B3 detection)
- Stale-trace sweep logic + GC (B4)
- C6 4 SKILL.md Phase Exit checklists
- C8 extend `tests/unit/test_post_flow_analysis.py` (≥3 fixtures)
- C9 `tests/integration/test_orchestrator.py` (≥5 cases including single-writer)

**Acceptance**:
- Sweep catches SIGKILL-killed phase in test fixture
- Multi-step fixture (exit 0 then "invalid state") classified correctly
- Single-writer test: trap + orchestrator both fire → 1 issue file (not 2)
- All 4 SKILL.md pass `grep -c "checklist" SKILL.md >= 1` (smoke test)

### Stage 3: Entry-script integration + regression (2 days)

- 4 phase entry scripts source `orchestrator_entry.sh` alongside existing wrapper
- Full regression: `./test.sh --full --regression` must be all-green or only KNOWN_FAILURES
- Update `docs/architecture/historical-evolution.md` (v2.1.x entry)
- Update `ADR-0027 §1.0` with "future extension" note pointing to this spec

**Acceptance**:
- `./test.sh --full --regression` all green
- 1 new bats test verifying env-var toggling works end-to-end
- Docs updated

---

## 13. Out of scope (deliberately deferred)

| Item | Reason |
|------|--------|
| Agent-side enforcement of finalize | Sweep + checklist is sufficient; full enforcement would need agent runtime hooks |
| Auto-flip-to-default-ON | Deferred until 2-week dogfood criteria met (§11.1) |
| Multi-writer coordination (flock) | Not needed; unique filenames + atomic append suffice |
| Real-time trace streaming | Adds complexity for no gain; finalize-time analysis is enough |
| Generic phase-discovery | Each phase explicitly opts in via env var; no auto-detection yet |
| Backport to pre-v2.1 projects | This is v2.1+ additive change |
| Replace bats with pytest | bats tests are stable and well-isolated; not in this PR |

---

## 14. Acceptance criteria (final)

Before this design can be merged:

1. ✅ All 3 migration stages complete per §12 acceptance.
2. ✅ `./test.sh --full --regression` reports only KNOWN_FAILURES (no new failures).
3. ✅ Oracle review of final code: ≥ 7/8/7 (re-verify after implementation).
4. ✅ 2 weeks of dogfood on this repo with zero false-positive sweep alerts.
5. ✅ At least 3 documented catches of B4-class failures (SIGKILL/OOM).

---

## 15. References

- ADR-0027 §1.0 (two-plane architecture) — sets up the Script vs Agent split this spec extends
- ADR-0027 §1.1 (category list) — `phase-crash` category is reused for sweep detections
- ADR-0027 §3 (L1/L2/L3 reporting) — sweep reports flow at L1 only by default
- ADR-0016 §4 (env-var override convention) — `RDDF_USE_ORCHESTRATOR` follows the same pattern
- ADR-0024 (handoff schema patterns) — trace file naming parallels handoff conventions
- `_lib/post_flow_analysis.py` (existing) — `classify_phase_outcome` reused; new `analyze_phase_trace` extends
- `_lib/loop/sanitizer.py` (existing) — `sanitize()` reused for trace content (Oracle rec #2)
- `_lib/cli/` (existing) — `__main__.py` dispatch reused; new `orchestrate_cmd.py` follows same shape as `report_issue_cmd.py`
- `skills/_lib/post_flow_wrap.sh` (existing) — `post_flow_on_err` modified for single-writer rule (C5)
- Oracle review session 2026-08-12 — 5 corrections integrated

---

## 16. Revision history

| Date | Author | Change |
|------|--------|--------|
| 2026-08-12 | sisyphus (via brainstorming) | Initial draft; Path B selected; Oracle SHIP-WITH-FIXES integrated |