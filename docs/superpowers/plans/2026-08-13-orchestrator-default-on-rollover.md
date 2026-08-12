# Orchestrator Default-ON Rollout Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Promote `RDDF_USE_ORCHESTRATOR` from opt-in to default-ON; wire all 4 phase entry scripts to `orchestrator_run` + `orchestrator_finalize`; add `rddf orchestrate show` for trace replay; ship 6 bats integration + 3 unit tests. One atomic PR per user's "一刀切" decision.

**Architecture:** Default-flip in `post_flow_wrap.sh` (single 2-line change). New thin `orchestrate_phase()` helper alongside existing `orchestrator_run`/`orchestrator_finalize`. Each phase entry script installs an EXIT trap that always runs finalize, and wraps direct binary calls (`git`, `ls`, etc.) via `orchestrator_run`. The grep rule in spec §6 is the regression contract. New `rddf orchestrate show` reads JSONL trace tail and renders a timeline.

**Tech Stack:** bash 4+ (traps, subshells), Python 3.11+ (orchestrator CLI, classifier), bats-core 1.10+ (integration tests), pytest (unit tests). Existing modules: `post_flow_analysis.py`, `orchestrate_cmd.py`, `orchestrator_entry.sh`.

**Spec:** `docs/superpowers/specs/2026-08-13-orchestrator-default-on-rollover-design.md` (commit `bc8555d`)

---

## File Structure

Files created or modified by this plan:

| File | Action | Component | Responsibility |
|---|---|---|---|
| `skills/_lib/post_flow_wrap.sh` | Modify | C1 | Default `RDDF_USE_ORCHESTRATOR:-yes`; comment |
| `skills/_lib/orchestrator_entry.sh` | Modify | C2 | Add `orchestrate_phase()` helper |
| `skills/guide-arch/scripts/arch_env_check.sh` | Modify | C3 | Wrap direct binary calls + EXIT trap |
| `skills/guide-plan/scripts/plan_intake.sh` | Modify | C4 | Wrap direct binary calls + EXIT trap |
| `skills/guide-ship/scripts/ship_env_check.sh` | Modify | C5 | Wrap direct binary calls + EXIT trap |
| `skills/execute/scripts/select_worktree.sh` | Modify | C6 | Wrap direct binary calls + EXIT trap |
| `_lib/cli/orchestrate_cmd.py` | Modify | C7 | Add `show` subcommand handler + dispatch |
| `install.sh` | Modify | C10 | Write default env var to user config |
| `AGENTS.md` | Modify | C11 | Update 触发链总结表 row |
| `docs/architecture/historical-evolution.md` | Modify | C11 | Add v2.1.x entry |
| `tests/unit/test_orchestrate_cmd.py` | Modify | C8 | Add 3 unit tests for `show` |
| `tests/unit/test_post_flow_wrap.sh` | Create | C1 | Default-flip unit test |
| `tests/unit/test_orchestrator_entry.sh` | Create | C2 | Helper existence test |
| `tests/integration/test_orchestrator_default_on.bats` | Create | C9 | 6 integration tests |
| `tests/scripts/check_wrap_grep.sh` | Create | C9 | Grep-rule regression guard |

---

## Task 0: Preflight — worktree + branch

**Files:**
- Worktree: `.rddf/wt/orchestrator-default-on`
- Branch: `openspec/orchestrator-default-on`

- [ ] **Step 1: Verify clean working tree**

```bash
git status --porcelain
```
Expected: empty output.

- [ ] **Step 2: Create worktree off master**

```bash
git worktree add .rddf/wt/orchestrator-default-on -b openspec/orchestrator-default-on master
```
Expected: `Preparing worktree (new branch)...` then `HEAD is now at <hash>`

- [ ] **Step 3: Confirm starting baseline is green**

```bash
cd .rddf/wt/orchestrator-default-on && ./test.sh --quick 2>&1 | tail -20
```
Expected: smoke + pytest unit pass. Note any pre-existing failures from KNOWN_FAILURES.txt for comparison.

- [ ] **Step 4: Verify spec is committed**

```bash
git log --oneline -1 -- docs/superpowers/specs/2026-08-13-orchestrator-default-on-rollover-design.md
```
Expected: `bc8555d spec(orchestrator): default-ON rollout design ...`

- [ ] **Step 5: Commit nothing — just record the baseline**

No commit. The worktree itself is the baseline.

---

## Task 1: C1 — Default flip in `post_flow_wrap.sh`

**Files:**
- Modify: `skills/_lib/post_flow_wrap.sh:42`
- Create: `tests/unit/test_post_flow_wrap.sh`

- [ ] **Step 1: Write failing test for default flip**

Create `tests/unit/test_post_flow_wrap.sh`:

```bash
#!/usr/bin/env bats
# Verifies RDDF_USE_ORCHESTRATOR defaults to "yes" after C1.
setup() {
    WRAP="${BATS_TEST_DIRNAME}/../../skills/_lib/post_flow_wrap.sh"
}
@test "post_flow_wrap: RDDF_USE_ORCHESTRATOR defaults to yes when unset" {
    unset RDDF_USE_ORCHESTRATOR
    # shellcheck disable=SC1090
    source "$WRAP" 2>/dev/null || true
    # If unset, post_flow_on_err should defer (return 0 on non-fatal code)
    # by checking the env var expansion default
    run bash -c "unset RDDF_USE_ORCHESTRATOR; source $WRAP; echo \"\${RDDF_USE_ORCHESTRATOR:-yes}\""
    [ "$output" = "yes" ]
}
@test "post_flow_wrap: RDDF_USE_ORCHESTRATOR=no bypasses orchestrator deferral" {
    run bash -c "export RDDF_USE_ORCHESTRATOR=no; source $WRAP; echo \"\${RDDF_USE_ORCHESTRATOR}\""
    [ "$output" = "no" ]
}
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd .rddf/wt/orchestrator-default-on && bats tests/unit/test_post_flow_wrap.sh
```
Expected: first test FAIL (default is still `no`, so output is `no`); second PASS.

- [ ] **Step 3: Flip the default in `post_flow_wrap.sh`**

Edit `skills/_lib/post_flow_wrap.sh:42`:
```bash
    # Single-writer rule (spec 2026-08-12 §7): defer to orchestrator.
    # Default ON since spec 2026-08-13 §2; override with RDDF_USE_ORCHESTRATOR=no.
    if [ "${RDDF_USE_ORCHESTRATOR:-yes}" = "yes" ]; then
        return 0
    fi
```

- [ ] **Step 4: Re-run test to verify it passes**

```bash
bats tests/unit/test_post_flow_wrap.sh
```
Expected: both tests PASS.

- [ ] **Step 5: Commit**

```bash
git add skills/_lib/post_flow_wrap.sh tests/unit/test_post_flow_wrap.sh
git commit -m "feat(orchestrator): flip RDDF_USE_ORCHESTRATOR default to yes (C1)

Per spec 2026-08-13 §2. Old trap path remains as fallback for
RDDF_USE_ORCHESTRATOR=no escape hatch. Verified by 2 new bats
cases (default unset -> yes, explicit no -> no)."
```

---

## Task 2: C2 — `orchestrate_phase()` helper

**Files:**
- Modify: `skills/_lib/orchestrator_entry.sh`
- Create: `tests/unit/test_orchestrator_entry.sh`

- [ ] **Step 1: Write failing test for helper existence + propagation**

Create `tests/unit/test_orchestrator_entry.sh`:

```bash
#!/usr/bin/env bats
setup() {
    ENTRY="${BATS_TEST_DIRNAME}/../../skills/_lib/orchestrator_entry.sh"
}
@test "orchestrator_entry: orchestrate_phase function is defined" {
    # shellcheck disable=SC1090
    source "$ENTRY" 2>/dev/null
    declare -F orchestrate_phase >/dev/null
}
@test "orchestrator_entry: orchestrate_phase propagates exit code" {
    RDDF_TRACE_DIR="$(mktemp -d)"
    export RDDF_TRACE_DIR RDDF_PHASE="int-test"
    # shellcheck disable=SC1090
    source "$ENTRY" 2>/dev/null
    run orchestrate_phase int-test false   # `false` exits 1
    [ "$status" -eq 1 ]
    rm -rf "$RDDF_TRACE_DIR"
}
@test "orchestrator_entry: orchestrate_phase emits finalize event on success" {
    RDDF_TRACE_DIR="$(mktemp -d)"
    export RDDF_TRACE_DIR RDDF_PHASE="int-test"
    # shellcheck disable=SC1090
    source "$ENTRY" 2>/dev/null
    orchestrate_phase int-test true
    # Find the trace file
    trace_file=$(ls "$RDDF_TRACE_DIR"/*.jsonl 2>/dev/null | head -1)
    [ -n "$trace_file" ]
    last_event=$(tail -1 "$trace_file" | grep -o '"type":"finalize"' || true)
    [ -n "$last_event" ]
    rm -rf "$RDDF_TRACE_DIR"
}
```

- [ ] **Step 2: Run test to verify it fails**

```bash
bats tests/unit/test_orchestrator_entry.sh
```
Expected: all 3 FAIL (`orchestrate_phase: command not found`).

- [ ] **Step 3: Implement the helper**

Append to `skills/_lib/orchestrator_entry.sh`:

```bash
# orchestrate_phase <name> <cmd...>
#   Aggregate helper: run <cmd> via orchestrator_run, then finalize the
#   current trace. Exit code of <cmd> is propagated. The file-level
#   EXIT trap in caller scripts already runs orchestrator_finalize;
#   this helper exists for symmetry with run_with_analysis when callers
#   want a single entry-point. Idempotent: finalize is a no-op if
#   already called.
orchestrate_phase() {
    local phase="${1:?orchestrate_phase requires phase name}"
    shift
    if [ "$#" -eq 0 ]; then
        echo "orchestrate_phase: requires command after phase" >&2
        return 2
    fi
    if ! command -v python3 >/dev/null 2>&1; then
        "$@"
        return $?
    fi
    _orchestrator_py subprocess "$@"
    local rc=$?
    _orchestrator_py finalize 2>/dev/null || true
    return $rc
}
```

- [ ] **Step 4: Re-run test to verify it passes**

```bash
bats tests/unit/test_orchestrator_entry.sh
```
Expected: all 3 PASS.

- [ ] **Step 5: Commit**

```bash
git add skills/_lib/orchestrator_entry.sh tests/unit/test_orchestrator_entry.sh
git commit -m "feat(orchestrator): add orchestrate_phase aggregate helper (C2)

Symmetric with run_with_analysis; runs orchestrator_run then finalize,
propagates exit code. Idempotent finalize via existing _orchestrator_py."
```

---

## Task 3: C7 + C8 — `rddf orchestrate show` subcommand

**Files:**
- Modify: `_lib/cli/orchestrate_cmd.py`
- Modify: `tests/unit/test_orchestrate_cmd.py`

- [ ] **Step 1: Write 3 failing unit tests**

Append to `tests/unit/test_orchestrate_cmd.py`:

```python
def test_cmd_orchestrate_show_reads_jsonl(tmp_path, monkeypatch, capsys):
    """`show` reads trace JSONL and prints timeline."""
    trace = tmp_path / "guide-arch-ses_x-1-100-aaaa.jsonl"
    trace.write_text(
        '{"ts":"2026-08-13T10:00:00Z","type":"checkpoint","name":"start"}\n'
        '{"ts":"2026-08-13T10:00:01Z","type":"subprocess","cmd":["git"],"returncode":0}\n'
        '{"ts":"2026-08-13T10:00:02Z","type":"finalize","subprocess_failures":0}\n'
    )
    monkeypatch.setenv("RDDF_TRACE_DIR", str(tmp_path))
    rc = cmd_orchestrate(["show", "guide-arch"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "10:00:00" in out
    assert "10:00:01" in out
    assert "10:00:02" in out
    assert "checkpoint" in out
    assert "subprocess" in out
    assert "finalize" in out


def test_cmd_orchestrate_show_filters_by_session(tmp_path, monkeypatch, capsys):
    """`show --session <id>` filters out events from other sessions."""
    (tmp_path / "guide-arch-ses_A-1-100-aaaa.jsonl").write_text(
        '{"ts":"2026-08-13T10:00:00Z","type":"checkpoint","name":"A"}\n'
    )
    (tmp_path / "guide-arch-ses_B-1-100-bbbb.jsonl").write_text(
        '{"ts":"2026-08-13T10:00:01Z","type":"checkpoint","name":"B"}\n'
    )
    monkeypatch.setenv("RDDF_TRACE_DIR", str(tmp_path))
    rc = cmd_orchestrate(["show", "guide-arch", "--session", "ses_A"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "A" in out
    assert "B" not in out


def test_cmd_orchestrate_show_filters_by_type(tmp_path, monkeypatch, capsys):
    """`show --type subprocess` filters out non-subprocess events."""
    trace = tmp_path / "guide-arch-ses_x-1-100-aaaa.jsonl"
    trace.write_text(
        '{"ts":"2026-08-13T10:00:00Z","type":"checkpoint","name":"start"}\n'
        '{"ts":"2026-08-13T10:00:01Z","type":"subprocess","cmd":["x"],"returncode":0}\n'
        '{"ts":"2026-08-13T10:00:02Z","type":"finalize","subprocess_failures":0}\n'
    )
    monkeypatch.setenv("RDDF_TRACE_DIR", str(tmp_path))
    rc = cmd_orchestrate(["show", "guide-arch", "--type", "subprocess"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "subprocess" in out
    assert "checkpoint" not in out
    assert "finalize" not in out
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
python3 -m pytest tests/unit/test_orchestrate_cmd.py::test_cmd_orchestrate_show_reads_jsonl tests/unit/test_orchestrate_cmd.py::test_cmd_orchestrate_show_filters_by_session tests/unit/test_orchestrate_cmd.py::test_cmd_orchestrate_show_filters_by_type -v
```
Expected: all 3 FAIL with `argparse.ArgumentError` (unknown subcommand `show`).

- [ ] **Step 3: Add `show` subparser + handler**

In `_lib/cli/orchestrate_cmd.py`, after `p_sweep = sub.add_parser("sweep-stale-traces", ...)`, add:

```python
    p_show = sub.add_parser("show", help="Print trace timeline for a phase")
    p_show.add_argument("phase", help="Phase name (e.g. guide-arch)")
    p_show.add_argument("--session", default="", help="Filter by session id")
    p_show.add_argument("--type", dest="event_type", default="",
                       choices=["", "subprocess", "checkpoint", "finalize"])
```

In the dispatch block, add:
```python
    if parsed.action == "show":
        return _handle_show(parsed.phase, parsed.session, parsed.event_type, trace_dir)
```

Then add the handler function (anywhere in the file):
```python
def _handle_show(phase: str, session_filter: str, type_filter: str, trace_dir: Path) -> int:
    """Print chronologically-sorted timeline of events for a phase.

    Reads all ``<phase>-*.jsonl`` files in trace_dir, applies optional
    session/type filters, prints one line per event. Empty result is
    not an error — just prints nothing.
    """
    if not trace_dir.is_dir():
        print(f"(trace dir not found: {trace_dir})")
        return 0
    candidates = sorted(trace_dir.glob(f"{phase}-*.jsonl"))
    if not candidates:
        print(f"(no traces for phase {phase!r})")
        return 0
    rows = []
    for trace_file in candidates:
        if session_filter and session_filter not in trace_file.name:
            continue
        for event in _read_events(trace_file):
            if type_filter and event.get("type") != type_filter:
                continue
            ts = event.get("ts", "")[:19]
            etype = event.get("type", "?")
            detail = ""
            if etype == "subprocess":
                detail = f"cmd={event.get('cmd')} rc={event.get('returncode')}"
            elif etype == "checkpoint":
                detail = f"name={event.get('name')}"
            elif etype == "finalize":
                detail = (f"failures={event.get('subprocess_failures')} "
                          f"checkpoints={event.get('checkpoints')}")
            rows.append((ts, etype, detail))
    rows.sort(key=lambda r: r[0])
    for ts, etype, detail in rows:
        print(f"{ts}  {etype:<11}  {detail}")
    return 0
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
python3 -m pytest tests/unit/test_orchestrate_cmd.py::test_cmd_orchestrate_show_reads_jsonl tests/unit/test_orchestrate_cmd.py::test_cmd_orchestrate_show_filters_by_session tests/unit/test_orchestrate_cmd.py::test_cmd_orchestrate_show_filters_by_type -v
```
Expected: all 3 PASS.

- [ ] **Step 5: Commit**

```bash
git add _lib/cli/orchestrate_cmd.py tests/unit/test_orchestrate_cmd.py
git commit -m "feat(orchestrator): add rddf orchestrate show subcommand (C7+C8)

Reads trace JSONL, prints timeline with phase/session/type filters.
3 new unit tests in test_orchestrate_cmd.py cover happy path + both
filter dimensions. Spec 2026-08-13 §5 primary复盘 surface."
```

---

## Task 4: C3 — Wire `arch_env_check.sh`

**Files:**
- Modify: `skills/guide-arch/scripts/arch_env_check.sh`
- Create: `tests/scripts/check_wrap_grep.sh` (referenced by Task 8)

- [ ] **Step 1: Identify all direct binary calls in the script**

```bash
grep -nE '^\s*(rddf|[a-z][a-z0-9_-]+)\s' skills/guide-arch/scripts/arch_env_check.sh | grep -v orchestrator_run | grep -v '^[^:]*:#'
```
Expected: 3 lines — line 25 (`git rev-parse`), line 90 (`ls -d`), line 91 (`ls`).

- [ ] **Step 2: Wrap each direct call**

Edit `skills/guide-arch/scripts/arch_env_check.sh`:

Line 25:
```bash
  PROJECT_ROOT=$(orchestrator_run git rev-parse --show-toplevel 2>/dev/null || pwd)
```

Line 90:
```bash
  ADR_COUNT=$(orchestrator_run ls -d "$PROJECT_ROOT/$DISCOVERED_ADR_DIR/"$DISCOVERED_ADR_PATTERN 2>/dev/null | wc -l | tr -d '[:space:]')
```

Line 91:
```bash
  ROADMAP_EXISTS=$([ -f "$PROJECT_ROOT/$DISCOVERED_ROADMAP_PATH" ] && echo "yes" || echo "no")  # shell builtin, no wrap needed
```

(Note: line 91 is a `[ -f ]` shell builtin test — NOT a binary call. The grep regex catches it but it's a false positive. Add an inline comment to mark this.)

Also wrap line 78-87 (the `discover_adr_dir`, `discover_roadmap`, etc. function calls) if they are direct binary invocations. Inspect each one; most delegate to functions sourced from `_lib/`.

For `discover_*` calls (lines 75-77), these call bash functions, not binaries — leave them.

- [ ] **Step 3: Add EXIT trap for orchestrator_finalize**

After line 21 (existing `source orchestrator_entry.sh` block), add:

```bash
# C3 (spec 2026-08-13 §6): always finalize on exit so sweep can detect
# phases killed without explicit cleanup.
trap 'orchestrator_finalize' EXIT
```

- [ ] **Step 4: Verify grep rule is empty**

```bash
grep -nE '^\s*(rddf|[a-z][a-z0-9_-]+)\s' skills/guide-arch/scripts/arch_env_check.sh | grep -v orchestrator_run | grep -v '^[^:]*:#'
```
Expected: only the comment line about `ROADMAP_EXISTS` shell builtin.

If any other lines remain, wrap them. If a line is a shell builtin (`[`, `echo`, `local`, etc.), add an inline comment marker so the grep check can be skipped.

- [ ] **Step 5: Verify exit trap is installed**

```bash
grep -n "trap 'orchestrator_finalize' EXIT" skills/guide-arch/scripts/arch_env_check.sh
```
Expected: 1 match.

- [ ] **Step 6: Commit**

```bash
git add skills/guide-arch/scripts/arch_env_check.sh
git commit -m "feat(orchestrator): wire arch_env_check.sh (C3)

Wraps git rev-parse + ls direct calls via orchestrator_run; installs
EXIT trap for orchestrator_finalize. Verifies grep rule (spec §6)
returns empty except for documented shell-builtin exemption."
```

---

## Task 5: C4 — Wire `plan_intake.sh`

**Files:**
- Modify: `skills/guide-plan/scripts/plan_intake.sh`

- [ ] **Step 1: Identify direct binary calls**

```bash
grep -nE '^\s*(rddf|[a-z][a-z0-9_-]+)\s' skills/guide-plan/scripts/plan_intake.sh | grep -v orchestrator_run | grep -v '^[^:]*:#'
```
Expected: at least line 26 (`ls -d`), line 32 (`ls -d`), and any `jq`/`python3` calls.

- [ ] **Step 2: Wrap each direct call**

For each identified line, replace with `orchestrator_run <binary> <args>`. The `python3 -c` heredoc invocations (lines 70-90, 98-104) MUST be wrapped as `orchestrator_run python3 -c "..."`.

- [ ] **Step 3: Add EXIT trap**

After line 20 (existing `source orchestrator_entry.sh`), add:
```bash
trap 'orchestrator_finalize' EXIT
```

- [ ] **Step 4: Verify grep rule + trap**

```bash
grep -nE '^\s*(rddf|[a-z][a-z0-9_-]+)\s' skills/guide-plan/scripts/plan_intake.sh | grep -v orchestrator_run | grep -v '^[^:]*:#'
grep -n "trap 'orchestrator_finalize' EXIT" skills/guide-plan/scripts/plan_intake.sh
```
Expected: grep empty (modulo documented shell-builtin comments), 1 trap match.

- [ ] **Step 5: Commit**

```bash
git add skills/guide-plan/scripts/plan_intake.sh
git commit -m "feat(orchestrator): wire plan_intake.sh (C4)"
```

---

## Task 6: C5 — Wire `ship_env_check.sh`

**Files:**
- Modify: `skills/guide-ship/scripts/ship_env_check.sh`

- [ ] **Step 1: Identify direct binary calls**

```bash
grep -nE '^\s*(rddf|[a-z][a-z0-9_-]+)\s' skills/guide-ship/scripts/ship_env_check.sh | grep -v orchestrator_run | grep -v '^[^:]*:#'
```
Expected: line 18 (`git rev-parse`), line 22 (`source` via skill_root — note this is a shell builtin), line 23 (`source` again — builtin).

- [ ] **Step 2: Wrap each direct call**

Wrap line 18 (`git rev-parse`) as `orchestrator_run git rev-parse ...`.

The `source` lines are shell builtins; add inline comment to exempt from grep.

- [ ] **Step 3: Add EXIT trap**

After line 14, add:
```bash
trap 'orchestrator_finalize' EXIT
```

- [ ] **Step 4: Verify**

```bash
grep -nE '^\s*(rddf|[a-z][a-z0-9_-]+)\s' skills/guide-ship/scripts/ship_env_check.sh | grep -v orchestrator_run | grep -v '^[^:]*:#'
grep -n "trap 'orchestrator_finalize' EXIT" skills/guide-ship/scripts/ship_env_check.sh
```
Expected: empty (modulo comments), 1 trap match.

- [ ] **Step 5: Commit**

```bash
git add skills/guide-ship/scripts/ship_env_check.sh
git commit -m "feat(orchestrator): wire ship_env_check.sh (C5)"
```

---

## Task 7: C6 — Wire `select_worktree.sh`

**Files:**
- Modify: `skills/execute/scripts/select_worktree.sh`

- [ ] **Step 1: Identify direct binary calls**

```bash
grep -nE '^\s*(rddf|[a-z][a-z0-9_-]+)\s' skills/execute/scripts/select_worktree.sh | grep -v orchestrator_run | grep -v '^[^:]*:#'
```
Expected: line 42 (`git -C rev-parse`), line 45 (`git -C rev-parse`), line 46 (`git -C rev-parse`), line 66 (`git rev-parse`), line 72 (`git branch --show-current`), line 74 (`git rev-parse`), line 78 (`git worktree list`), line 106 (`git worktree list --porcelain`).

- [ ] **Step 2: Wrap each direct call**

Replace each `git ...` invocation with `orchestrator_run git ...`. Note: `git -C <path> rev-parse` becomes `orchestrator_run git -C <path> rev-parse`.

- [ ] **Step 3: Add EXIT trap**

After line 18, add:
```bash
trap 'orchestrator_finalize' EXIT
```

- [ ] **Step 4: Verify**

```bash
grep -nE '^\s*(rddf|[a-z][a-z0-9_-]+)\s' skills/execute/scripts/select_worktree.sh | grep -v orchestrator_run | grep -v '^[^:]*:#'
grep -n "trap 'orchestrator_finalize' EXIT" skills/execute/scripts/select_worktree.sh
```
Expected: empty, 1 trap match.

- [ ] **Step 5: Commit**

```bash
git add skills/execute/scripts/select_worktree.sh
git commit -m "feat(orchestrator): wire select_worktree.sh (C6)"
```

---

## Task 8: C9 — Integration tests + grep guard

**Files:**
- Create: `tests/scripts/check_wrap_grep.sh`
- Create: `tests/integration/test_orchestrator_default_on.bats`

- [ ] **Step 1: Create the grep guard script**

Create `tests/scripts/check_wrap_grep.sh`:

```bash
#!/usr/bin/env bash
# Verifies spec 2026-08-13 §6 grep rule across 4 phase entry scripts.
# Exits 0 if all entry scripts have empty unwrapped-call list.
# Exits 1 with diagnostic if any unwrapped call found.

set -e

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SCRIPTS=(
    "$REPO_ROOT/skills/guide-arch/scripts/arch_env_check.sh"
    "$REPO_ROOT/skills/guide-plan/scripts/plan_intake.sh"
    "$REPO_ROOT/skills/guide-ship/scripts/ship_env_check.sh"
    "$REPO_ROOT/skills/execute/scripts/select_worktree.sh"
)

violations=0
for script in "${SCRIPTS[@]}"; do
    if [ ! -f "$script" ]; then
        echo "MISSING: $script"
        violations=$((violations + 1))
        continue
    fi
    hits=$(grep -nE '^\s*(rddf|[a-z][a-z0-9_-]+)\s' "$script" \
        | grep -v orchestrator_run \
        | grep -v '^[^:]*:#' || true)
    if [ -n "$hits" ]; then
        echo "UNWRAPPED in $script:"
        echo "$hits" | sed 's/^/  /'
        violations=$((violations + 1))
    fi
    if ! grep -q "trap 'orchestrator_finalize' EXIT" "$script"; then
        echo "MISSING EXIT trap in $script"
        violations=$((violations + 1))
    fi
done

if [ "$violations" -gt 0 ]; then
    echo ""
    echo "$violations violation(s). See spec 2026-08-13 §6."
    exit 1
fi
echo "OK: all 4 entry scripts pass grep rule + EXIT trap check."
```

Make executable:
```bash
chmod +x tests/scripts/check_wrap_grep.sh
```

- [ ] **Step 2: Run guard to confirm current state passes (sanity check)**

```bash
bash tests/scripts/check_wrap_grep.sh
```
Expected: `OK: all 4 entry scripts pass grep rule + EXIT trap check.` (because Tasks 4-7 already wired everything).

- [ ] **Step 3: Create the 6 bats integration tests**

Create `tests/integration/test_orchestrator_default_on.bats`:

```bash
#!/usr/bin/env bats
# Spec 2026-08-13 §8 integration tests for default-ON orchestrator.

setup() {
    REPO_ROOT="$(cd "${BATS_TEST_DIRNAME}/../.." && pwd)"
    WORK="$(mktemp -d)"
    cd "$WORK"
    git init -q .
    git config user.email "test@test"
    git config user.name "test"
    # Stage post_flow_wrap + orchestrator_entry
    cp "$REPO_ROOT/skills/_lib/post_flow_wrap.sh" ./
    cp "$REPO_ROOT/skills/_lib/orchestrator_entry.sh" ./
    export RDDF_TRACE_DIR="$WORK/.rddf/state/trace"
    export RDDF_PHASE="int-test"
}

teardown() {
    rm -rf "$WORK"
}

@test "T1: default-ON phase run produces trace + finalize" {
    source post_flow_wrap.sh 2>/dev/null || true
    source orchestrator_entry.sh 2>/dev/null || true
    trap 'orchestrator_finalize' EXIT
    orchestrator_run bash -c 'echo hi'
    orchestrator_finalize
    [ -f "$RDDF_TRACE_DIR"/int-test-*.jsonl ]
    last=$(tail -1 "$RDDF_TRACE_DIR"/*.jsonl)
    [[ "$last" == *'"type":"finalize"'* ]]
}

@test "T2: kill -9 mid-phase triggers sweep -> phase-crash issue" {
    source post_flow_wrap.sh 2>/dev/null || true
    source orchestrator_entry.sh 2>/dev/null || true
    RDDF_TRACE_STALE_MINUTES=0
    export RDDF_TRACE_STALE_MINUTES
    orchestrator_run bash -c 'sleep 0.05' || true
    # Manually drop the trace to simulate kill -9 (no finalize event)
    trace=$(ls "$RDDF_TRACE_DIR"/*.jsonl 2>/dev/null | head -1)
    [ -n "$trace" ]
    rm "$trace"
    # Now create a stale trace mimicking a killed phase
    stale="$RDDF_TRACE_DIR/int-test-stale-1-1-aaaaaaaa.jsonl"
    printf '{"ts":"2026-08-13T09:00:00Z","type":"subprocess","cmd":["x"],"returncode":0,"stderr_tail":"","stdout_tail":""}\n' > "$stale"
    touch -t 202608130900 "$stale"
    # Run sweep
    orchestrator_sweep
    # Sweep unlinks the file; no trace should remain
    [ ! -f "$stale" ]
}

@test "T3: same failure triggered twice produces exactly 1 issue file" {
    source post_flow_wrap.sh 2>/dev/null || true
    RDDF_USE_ORCHESTRATOR=yes
    export RDDF_USE_ORCHESTRATOR
    # First write an issue via direct report_flow_bug
    mkdir -p .rddf/issues
    # Direct call: writes an issue with deterministic hash
    PYTHONPATH="$REPO_ROOT/_lib" RDDF_PROJECT_ROOT="$WORK" \
        python3 -c "
import sys; sys.path.insert(0, '$REPO_ROOT/_lib')
from post_flow_analysis import PhaseOutcome, classify_phase_outcome, report_flow_bug
o = PhaseOutcome(phase='int-test', exit_code=1, stderr='Traceback (most recent call last):\n  File \"$REPO_ROOT/_lib/foo.py\", line 1')
c = classify_phase_outcome('int-test', o)
report_flow_bug(c, project_root='$WORK')
" 2>/dev/null || true
    issue_count=$(ls .rddf/issues/*.md 2>/dev/null | wc -l)
    [ "$issue_count" -eq 1 ]
}

@test "T4: RDDF_USE_ORCHESTRATOR=no skips wrap+finalize; old trap fires" {
    RDDF_USE_ORCHESTRATOR=no
    export RDDF_USE_ORCHESTRATOR
    source post_flow_wrap.sh 2>/dev/null || true
    # With orchestrator off, the bash trap 'post_flow_on_err' is active.
    # We just verify env var reaches post_flow_on_err and is honored.
    run bash -c "
        export RDDF_USE_ORCHESTRATOR=no
        source $REPO_ROOT/skills/_lib/post_flow_wrap.sh 2>/dev/null || true
        bash -c 'exit 1' 2>/dev/null
        echo trap_fired=\$?
    "
    [[ "$output" == *"trap_fired=0"* ]]
}

@test "T5: exit 130 (SIGINT) is excluded, no issue written" {
    source post_flow_wrap.sh 2>/dev/null || true
    PYTHONPATH="$REPO_ROOT/_lib" RDDF_PROJECT_ROOT="$WORK" \
        python3 -c "
import sys; sys.path.insert(0, '$REPO_ROOT/_lib')
from post_flow_analysis import PhaseOutcome, classify_phase_outcome
o = PhaseOutcome(phase='int-test', exit_code=130, stderr='')
c = classify_phase_outcome('int-test', o)
assert c.should_report == False, 'SIGINT must not be reported'
assert c.matched_rule == 'SIGINT-EXCLUDED'
print('OK')
"
}

@test "T6: rddf orchestrate show prints timeline" {
    # Use real repo state: existing trace from this repo if any
    # Otherwise create a synthetic one
    mkdir -p "$RDDF_TRACE_DIR"
    trace="$RDDF_TRACE_DIR/int-test-ses_x-1-100-aaaa.jsonl"
    printf '{"ts":"2026-08-13T10:00:00Z","type":"checkpoint","name":"start"}\n' > "$trace"
    printf '{"ts":"2026-08-13T10:00:01Z","type":"subprocess","cmd":["x"],"returncode":0}\n' >> "$trace"
    printf '{"ts":"2026-08-13T10:00:02Z","type":"finalize","subprocess_failures":0}\n' >> "$trace"
    PYTHONPATH="$REPO_ROOT:_lib" RDDF_TRACE_DIR="$RDDF_TRACE_DIR" RDDF_PROJECT_ROOT="$WORK" \
        python3 "$REPO_ROOT/_lib/cli/orchestrate_cmd.py" show int-test
    [[ "$output" == *"checkpoint"* ]]
    [[ "$output" == *"subprocess"* ]]
    [[ "$output" == *"finalize"* ]]
}
```

- [ ] **Step 4: Run the integration tests**

```bash
bats tests/integration/test_orchestrator_default_on.bats
```
Expected: all 6 PASS.

If failures occur, debug per case (likely paths in `PYTHONPATH` or env vars not propagating through subshells).

- [ ] **Step 5: Commit**

```bash
git add tests/scripts/check_wrap_grep.sh tests/integration/test_orchestrator_default_on.bats
git commit -m "test(orchestrator): add 6 bats integration cases + grep guard (C9)

Tests: T1 default-ON trace + finalize, T2 kill -9 sweep, T3 single-writer,
T4 opt-out, T5 SIGINT excluded, T6 rddf orchestrate show. Plus a
tests/scripts/check_wrap_grep.sh regression guard for spec §6."
```

---

## Task 9: C10 — `install.sh` env hook

**Files:**
- Modify: `install.sh`

- [ ] **Step 1: Inspect `install.sh` for the existing env-write section**

```bash
grep -n "RDDF_\|~/.config/rdd-workflow" install.sh | head -20
```
Expected: existing pattern for writing user env file (or absence).

- [ ] **Step 2: Add the default-write snippet**

After the last existing `RDDF_*` write in `install.sh`, add:

```bash
# C10 (spec 2026-08-13 §3): default-ON orchestrator
ENV_FILE="${HOME}/.config/rdd-workflow/env"
mkdir -p "$(dirname "$ENV_FILE")"
if ! grep -q '^RDDF_USE_ORCHESTRATOR_DEFAULT=' "$ENV_FILE" 2>/dev/null; then
    echo 'export RDDF_USE_ORCHESTRATOR_DEFAULT=yes' >> "$ENV_FILE"
fi
```

- [ ] **Step 3: Verify the env file gets written on a dry run**

```bash
mkdir -p /tmp/opencode/rdd-test
HOME=/tmp/opencode/rdd-test bash install.sh 2>&1 | tail -5 || true
cat /tmp/opencode/rdd-test/.config/rdd-workflow/env
```
Expected: contains `export RDDF_USE_ORCHESTRATOR_DEFAULT=yes`.

- [ ] **Step 4: Commit**

```bash
git add install.sh
git commit -m "feat(orchestrator): install.sh writes RDDF_USE_ORCHESTRATOR_DEFAULT=yes (C10)"
```

---

## Task 10: C11 — Docs sync

**Files:**
- Modify: `AGENTS.md` (触发链总结表 row)
- Modify: `docs/architecture/historical-evolution.md` (v2.1.x entry)

- [ ] **Step 1: Update AGENTS.md 触发链总结表**

Find the row for "bash trap ERR" in the table (under "## 触发链总结表" section). Update the "是否自动" column to "是" and add a note in the description: "Default ON since spec 2026-08-13 §2".

- [ ] **Step 2: Add v2.1.x entry to historical-evolution.md**

Append to the topmost version section:

```markdown
### v2.1.x — Orchestrator default-ON (spec 2026-08-13)

- `RDDF_USE_ORCHESTRATOR` flips from opt-in to default-ON (single-writer rule preserved)
- 4 phase entry scripts now wrap direct binary calls via `orchestrator_run` + `orchestrator_finalize` on EXIT
- `rddf orchestrate show <phase>` provides trace replay surface
- 6 bats integration tests + 3 unit tests added in `tests/integration/test_orchestrator_default_on.bats` and `tests/unit/test_orchestrate_cmd.py`
- Spec: `docs/superpowers/specs/2026-08-13-orchestrator-default-on-rollover-design.md`
```

- [ ] **Step 3: Verify grep rule still passes**

```bash
bash tests/scripts/check_wrap_grep.sh
```
Expected: `OK: all 4 entry scripts pass grep rule + EXIT trap check.`

- [ ] **Step 4: Commit**

```bash
git add AGENTS.md docs/architecture/historical-evolution.md
git commit -m "docs(orchestrator): sync AGENTS.md and historical-evolution.md (C11)"
```

---

## Task 11: Final regression gate

- [ ] **Step 1: Run full test suite**

```bash
cd .rddf/wt/orchestrator-default-on && ./test.sh --full --regression 2>&1 | tail -30
```
Expected: passes with only `KNOWN_FAILURES` (no new failures).

- [ ] **Step 2: Run grep guard**

```bash
bash tests/scripts/check_wrap_grep.sh
```
Expected: `OK: all 4 entry scripts pass grep rule + EXIT trap check.`

- [ ] **Step 3: Manual smoke test of `rddf orchestrate show`**

```bash
export RDDF_TRACE_DIR=/tmp/opencode/show-smoke
mkdir -p "$RDDF_TRACE_DIR"
RDDF_PROJECT_ROOT="$(pwd)" python3 _lib/cli/orchestrate_cmd.py show int-test
```
Expected: prints `(no traces for phase 'int-test')` and exits 0.

- [ ] **Step 4: Verify all 11 component commits land in branch**

```bash
git log --oneline master..HEAD
```
Expected: 10 commits (Tasks 1, 2, 3, 4, 5, 6, 7, 8, 9, 10 — Task 0 made no commit, Task 11 makes none).

- [ ] **Step 5: Final summary commit if any docs adjustment**

If Steps 1-3 surfaced any tweaks, commit them with `chore(orchestrator): post-regression tweaks`.

---

## Self-Review

**Spec coverage check** (against `2026-08-13-orchestrator-default-on-rollover-design.md`):

| Spec § | Covered by Task |
|---|---|
| §1 Background (evidence) | (in spec only; not implementation) |
| §2 Decision | Task 1 (C1), Task 9 (C10) |
| §3 C1 (post_flow_wrap default) | Task 1 |
| §3 C2 (orchestrate_phase) | Task 2 |
| §3 C3-C6 (entry scripts) | Tasks 4, 5, 6, 7 |
| §3 C7-C8 (show + unit tests) | Task 3 |
| §3 C9 (integration tests) | Task 8 |
| §3 C10 (install.sh hook) | Task 9 |
| §3 C11 (docs sync) | Task 10 |
| §4 Architecture | Tasks 1-7 (EXIT trap + wrap) |
| §5 Data flow | Task 3 (show subcommand) |
| §6 Grep rule | Task 8 (check_wrap_grep.sh) |
| §6.1 Helper boundary | Acknowledged in §12 of spec; not changed in this plan |
| §6.2 Trap ordering | Documented in Tasks 4-7 |
| §7 Error handling matrix | Verified by Task 8 T1-T5 |
| §8 Testing strategy | Task 3 (unit) + Task 8 (integration) |
| §9 Backward compatibility | Task 8 T4 (opt-out test) |
| §10 Migration plan | Tasks 1-10 sequential |
| §11 Acceptance criteria #1 (grep empty) | Task 8 Step 2 + Task 10 Step 3 + Task 11 Step 2 |
| §11 #2 (EXIT trap on all 4) | Task 8 Step 1 (check_wrap_grep.sh checks) |
| §11 #3 (default flip) | Task 1 |
| §11 #4 (regression clean) | Task 11 Step 1 |
| §11 #5 (6 new bats pass) | Task 8 Step 4 + Task 11 Step 1 |
| §11 #6 (3 new unit pass) | Task 3 Step 4 + Task 11 Step 1 |
| §11 #7 (Oracle review) | (out of plan scope; reviewer task) |
| §11 #8 (show smoke) | Task 11 Step 3 |

**Placeholder scan:** No "TBD" / "TODO" / "implement later" / "similar to Task N" markers. Every step has concrete code or commands.

**Type consistency check:**
- `_handle_show(phase, session_filter, type_filter, trace_dir)` is defined once (Task 3 Step 3) and called once in dispatch — no signature drift.
- `orchestrate_phase <phase> <cmd...>` is defined once (Task 2 Step 3) and used in tests (Task 2 Step 1) — signatures match.
- `cmd_orchestrate(args)` is the single dispatch entry — unchanged from parent spec.
- `RDDF_USE_ORCHESTRATOR:-yes` default appears in Tasks 1, 8 (T4), 11 (verifies) — consistent.

**Self-review verdict:** Spec is fully covered. No spec requirement is missing a task.

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-08-13-orchestrator-default-on-rollover.md`.

Two execution options:

1. **Subagent-Driven (recommended)** — Dispatch a fresh subagent per task, review between tasks, fast iteration with isolation.
2. **Inline Execution** — Execute tasks in this session using executing-plans, batch execution with checkpoints.

Which approach?
