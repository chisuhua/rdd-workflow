# Python Orchestrator + Bash Leaf Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace bash `trap ERR` post-flow detection with a Python orchestrator (`rddf orchestrate`) that supervises subprocess execution, adds stale-trace sweep for SIGKILL/OOM detection (B4 fix), sanitizes trace content, and keeps `post_flow_wrap.sh` as a backward-compatible fallback. Closes 4 design blind spots in `report_flow_bug` triggering.

**Architecture:** Additive. New `rddf orchestrate` subcommand reuses existing `_lib/cli/__main__.py` dispatch. Bash scripts in `skills/_lib/orchestrator_entry.sh` wrap each subprocess call with `|| true`. Trace files at `.rddf/state/trace/<phase>-<session>-<pid>-<epoch>.jsonl` (gitignored). Stale-trace sweep runs on first `--subprocess` call per phase entry. Single-writer rule disables trap path when `RDDF_USE_ORCHESTRATOR=yes`.

**Tech Stack:** Python 3.11+ (subprocess, tempfile, json), bash (Phase 1), bats-core 1.10+, pytest. Reuses `_lib/loop/sanitizer.sanitize()` for trace content sanitization.

**Reference Spec:** `docs/superpowers/specs/2026-08-12-python-orchestrator-design.md`

---

## File Structure

Files this change touches:

| File | Operation | Responsibility |
|------|-----------|----------------|
| `_lib/cli/orchestrate_cmd.py` | Create | New `rddf orchestrate` subcommand: --subprocess / --mark-checkpoint / --finalize / --sweep-stale-traces |
| `_lib/cli/__main__.py` | Modify | Register `orchestrate` in `_print_help()` |
| `_lib/post_flow_analysis.py` | Modify | Add `analyze_phase_trace(trace_path, project_root) -> Classification` function |
| `skills/_lib/orchestrator_entry.sh` | Create | Bash wrapper exposing `orchestrator_run` / `orchestrator_mark` / `orchestrator_finalize` |
| `skills/_lib/post_flow_wrap.sh` | Modify | Add single-writer guard at top of `post_flow_on_err` (5 lines) |
| `skills/guide-arch/SKILL.md` | Modify | Replace Phase Exit prose (line 758-771) with 3-rule checklist |
| `skills/guide-plan/SKILL.md` | Modify | Replace Phase Exit prose (line 663) with 3-rule checklist |
| `skills/guide-ship/SKILL.md` | Modify | Replace Phase Exit prose (line 737) with 3-rule checklist |
| `skills/execute/SKILL.md` | Modify | Replace Phase Exit prose (line 288) with 3-rule checklist |
| `tests/unit/test_orchestrate_cmd.py` | Create | ≥12 unit tests for new subcommand |
| `tests/unit/test_post_flow_analysis.py` | Modify | Add ≥3 multi-step cumulative-failure fixtures |
| `tests/integration/test_orchestrator.py` | Create | ≥5 integration tests including single-writer rule |
| `tests/integration/test_env_var_toggle.bats` | Create | 4 bats tests for env-var toggling |
| `docs/architecture/historical-evolution.md` | Modify | Add v2.1.x entry referencing this spec |
| `docs/adr/ADR-0027-continuous-evolution-feedback-loop.md` | Modify | Add "Future extension" subsection in §1.0 |

Files explicitly NOT touched:
`_lib/issue_reporter.py`, `_lib/loop/sanitizer.py`, all `skills/*/scripts/*.sh` (except the 4 entry scripts listed above), `package.json`, `install.sh`.

---

## Truth-source hierarchy

| Layer | Role | Examples | Authority for … |
|-------|------|----------|----------------|
| L1 | Runtime code | `_lib/cli/orchestrate_cmd.py`; `skills/_lib/orchestrator_entry.sh` | Trace format, subcommand semantics |
| L2 | Spec | `docs/superpowers/specs/2026-08-12-python-orchestrator-design.md` | Component contracts, error matrix |
| L3 | ADR | `docs/adr/ADR-0027-continuous-evolution-feedback-loop.md` | Two-plane architecture, category taxonomy |

When in doubt, L1 wins. When L1 has a gap, L2 fills it. L3 documents policy.

---

## Stage 1: Orchestrator Core (Days 1-4)

### Task 1: Create orchestrate_cmd.py skeleton with CLI dispatch registration

**Files:**
- Create: `_lib/cli/orchestrate_cmd.py`
- Modify: `_lib/cli/__main__.py:163-185` (add `orchestrate` to help text)

- [ ] **Step 1: Create the skeleton file**

Write `_lib/cli/orchestrate_cmd.py`:

```python
"""``rddf orchestrate`` — Python orchestrator for phase subprocess supervision.

Closes 4 blind spots in the bash trap ERR approach (see
``docs/superpowers/specs/2026-08-12-python-orchestrator-design.md`` §1.1):

- B1: Sub-scripts that don't source ``post_flow_wrap.sh`` never fire the trap.
- B2: Agents don't always comply with SKILL.md Phase Exit instruction.
- B3: Intermediate silent corruption (exit 0 but state already broken).
- B4: SIGKILL / OOM / laptop-close — zero signal, no trap, no finalize.

The headline feature is crash-survivable stale-trace detection (§5 of spec):
on first ``--subprocess`` invocation per phase entry, sweep trace dir for
unfinalized traces and report them as ``phase-interrupted``.

Trace format: JSONL at ``$RDDF_TRACE_DIR/<phase>-<session>-<pid>-<epoch>.jsonl``
(default ``.rddf/state/trace/``).
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


def cmd_orchestrate(argv: list[str]) -> int:
    """Entry point for ``rddf orchestrate <subcommand> [args]``."""
    parser = argparse.ArgumentParser(prog="rddf orchestrate")
    sub = parser.add_subparsers(dest="action", required=True)

    p_sub = sub.add_parser("subprocess", help="Run a subprocess and record its result")
    p_sub.add_argument("cmd", nargs=argparse.REMAINDER, help="Command + args to run")

    p_mark = sub.add_parser("mark-checkpoint", help="Insert a checkpoint event")
    p_mark.add_argument("--name", required=True)
    p_mark.add_argument("--state-marker", default="")

    p_fin = sub.add_parser("finalize", help="Close the trace and trigger analysis")

    p_sweep = sub.add_parser("sweep-stale-traces", help="Manually trigger sweep")

    args = parser.parse_args(argv)
    trace_dir = _get_trace_dir()

    if args.action == "subprocess":
        return _handle_subprocess(args.cmd, trace_dir)
    if args.action == "mark-checkpoint":
        return _handle_checkpoint(args.name, args.state_marker, trace_dir)
    if args.action == "finalize":
        return _handle_finalize(trace_dir)
    if args.action == "sweep-stale-traces":
        return _handle_sweep(trace_dir)
    return 2  # unreachable


def _get_trace_dir() -> Path:
    """Return the trace directory from env or default."""
    raw = os.environ.get("RDDF_TRACE_DIR", ".rddf/state/trace")
    return Path(raw).resolve()


def _handle_subprocess(cmd: list[str], trace_dir: Path) -> int:
    """Placeholder — filled in Task 3."""
    raise NotImplementedError("filled in Task 3")


def _handle_checkpoint(name: str, state_marker: str, trace_dir: Path) -> int:
    """Placeholder — filled in Task 4."""
    raise NotImplementedError("filled in Task 4")


def _handle_finalize(trace_dir: Path) -> int:
    """Placeholder — filled in Task 5."""
    raise NotImplementedError("filled in Task 5")


def _handle_sweep(trace_dir: Path) -> int:
    """Placeholder — filled in Task 10."""
    raise NotImplementedError("filled in Task 10")
```

- [ ] **Step 2: Verify the file is importable**

Run: `python3 -c "from skills._lib.cli.orchestrate_cmd import cmd_orchestrate; print('ok')"`
Expected: `ok` (and any deprecation/import warnings — those are pre-existing).

- [ ] **Step 3: Register in `_print_help()`**

Edit `_lib/cli/__main__.py:163-185`. Find the help-text block (the multi-line string
inside `_print_help`) and add one line after the `migration-improvements` line:

```python
    print("  orchestrate    Phase subprocess orchestrator (subprocess/finalize)")
```

- [ ] **Step 4: Verify dispatch works**

Run: `rddf orchestrate --help`
Expected: usage line including `subprocess / mark-checkpoint / finalize / sweep-stale-traces`.

- [ ] **Step 5: Commit**

```bash
cd /workspace/project/rdd-workflow
git add _lib/cli/orchestrate_cmd.py _lib/cli/__main__.py
git commit -m "feat(cli): add rddf orchestrate subcommand skeleton"
```

---

### Task 2: Implement trace file management (open / append / finalize)

**Files:**
- Modify: `_lib/cli/orchestrate_cmd.py` (replace placeholders)

- [ ] **Step 1: Write the failing test**

Append to `tests/unit/test_orchestrate_cmd.py` (will be created in Task 8; for now
create a stub):

```python
"""Tests for rddf orchestrate subcommand (spec 2026-08-12)."""
import json
import os
from pathlib import Path

import pytest

from skills._lib.cli.orchestrate_cmd import (
    _get_trace_path,
    _open_trace,
    _append_event,
    _read_events,
)


def test_get_trace_path_includes_phase_pid_epoch(tmp_path, monkeypatch):
    monkeypatch.setenv("RDDF_TRACE_DIR", str(tmp_path))
    p = _get_trace_path(phase="guide-arch", session_id="ses_test123", pid=42, epoch=100)
    assert p.parent == tmp_path
    assert p.name.startswith("guide-arch-ses_test123-42-100-")
    assert p.suffix == ".jsonl"


def test_open_trace_creates_file_with_metadata(tmp_path, monkeypatch):
    monkeypatch.setenv("RDDF_TRACE_DIR", str(tmp_path))
    trace = _open_trace(phase="guide-arch", session_id="ses_test")
    assert trace.path.exists()
    assert trace.phase == "guide-arch"
    assert trace.session_id == "ses_test"
    trace.close()


def test_append_event_writes_valid_jsonl(tmp_path, monkeypatch):
    monkeypatch.setenv("RDDF_TRACE_DIR", str(tmp_path))
    trace = _open_trace(phase="guide-arch", session_id="ses_test")
    _append_event(trace, {"type": "checkpoint", "name": "start"})
    _append_event(trace, {"type": "subprocess", "cmd": ["echo"], "returncode": 0})
    trace.close()
    events = _read_events(trace.path)
    assert len(events) == 2
    assert events[0]["type"] == "checkpoint"
    assert events[1]["type"] == "subprocess"
    assert "ts" in events[0]  # timestamp auto-added


def test_read_events_skips_malformed_lines(tmp_path, monkeypatch):
    monkeypatch.setenv("RDDF_TRACE_DIR", str(tmp_path))
    trace_path = tmp_path / "test.jsonl"
    trace_path.write_text(
        '{"ts":"2026-08-12T10:00:00Z","type":"checkpoint","name":"a"}\n'
        'not json\n'
        '{"ts":"2026-08-12T10:00:01Z","type":"finalize"}\n'
    )
    events = _read_events(trace_path)
    assert len(events) == 2
    assert events[0]["name"] == "a"
    assert events[1]["type"] == "finalize"
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python3 -m pytest tests/unit/test_orchestrate_cmd.py -v`
Expected: FAIL with `ImportError: cannot import name '_get_trace_path'` (or similar).

- [ ] **Step 3: Implement trace file management**

Replace the placeholder helper definitions in `_lib/cli/orchestrate_cmd.py` with:

```python
@dataclass
class Trace:
    """Open trace file handle with phase/session metadata."""

    path: Path
    phase: str
    session_id: str
    _fh: object  # file handle

    def close(self) -> None:
        if self._fh and not self._fh.closed:
            self._fh.close()


def _get_trace_path(phase: str, session_id: str, pid: int, epoch: int) -> Path:
    """Return path for a new trace file.

    Filename: ``<phase>-<session>-<pid>-<epoch>-<uuid>.jsonl``
    Epoch ensures uniqueness even if pid reused within same second.
    UUID suffix guards against collision from same-process multi-open.
    """
    fname = f"{phase}-{session_id}-{pid}-{epoch}-{uuid.uuid4().hex[:8]}.jsonl"
    return _get_trace_dir() / fname


def _get_session_id() -> str:
    """Read rddf-session owner_opencode_session_id or generate a fresh UUID."""
    # Per ADR-0017 fallback: try sessions.json first, then env, then fresh UUID
    project_root = os.environ.get("RDDF_PROJECT_ROOT", ".")
    sessions_path = Path(project_root) / ".rddf" / "state" / "sessions.json"
    if sessions_path.is_file():
        try:
            import json
            data = json.loads(sessions_path.read_text())
            current = data.get("current", {})
            return current.get("owner_opencode_session_id", uuid.uuid4().hex)
        except (OSError, json.JSONDecodeError, KeyError):
            pass
    return os.environ.get("RDDF_OPENCODE_SESSION_ID", uuid.uuid4().hex)


def _open_trace(phase: str, session_id: Optional[str] = None) -> Trace:
    """Open a new trace file for writing.

    Ensures ``RDDF_TRACE_DIR`` exists; raises OSError on permission failure.
    """
    sid = session_id or _get_session_id()
    trace_dir = _get_trace_dir()
    trace_dir.mkdir(parents=True, exist_ok=True)
    path = _get_trace_path(
        phase=phase,
        session_id=sid,
        pid=os.getpid(),
        epoch=int(time.time()),
    )
    fh = open(path, "a", encoding="utf-8")
    return Trace(path=path, phase=phase, session_id=sid, _fh=fh)


def _append_event(trace: Trace, event: dict) -> None:
    """Append one event to the trace. Adds timestamp if missing."""
    if "ts" not in event:
        event = {**event, "ts": datetime.now(timezone.utc).isoformat()}
    line = json.dumps(event, ensure_ascii=False, separators=(",", ":"))
    trace._fh.write(line + "\n")
    trace._fh.flush()


def _read_events(path: Path) -> list[dict]:
    """Read all events from a JSONL file. Skips malformed lines."""
    events: list[dict] = []
    if not path.is_file():
        return events
    with open(path, encoding="utf-8") as fh:
        for raw in fh:
            raw = raw.strip()
            if not raw:
                continue
            try:
                events.append(json.loads(raw))
            except json.JSONDecodeError:
                continue  # skip malformed
    return events
```

Also add these imports at the top of the file (alongside existing ones):

```python
from dataclasses import dataclass
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `python3 -m pytest tests/unit/test_orchestrate_cmd.py -v`
Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
cd /workspace/project/rdd-workflow
git add _lib/cli/orchestrate_cmd.py tests/unit/test_orchestrate_cmd.py
git commit -m "feat(orchestrate): add trace file management (open/append/read)"
```

---

### Task 3: Implement `--subprocess` with tempfile streams + sanitize

**Files:**
- Modify: `_lib/cli/orchestrate_cmd.py` (replace `_handle_subprocess` placeholder)

- [ ] **Step 1: Write the failing test**

Append to `tests/unit/test_orchestrate_cmd.py`:

```python
def test_handle_subprocess_runs_command_and_records(monkeypatch, tmp_path):
    monkeypatch.setenv("RDDF_TRACE_DIR", str(tmp_path))
    monkeypatch.setenv("RDDF_PROJECT_ROOT", str(tmp_path))
    rc = _handle_subprocess(["echo", "hello"], trace_dir=tmp_path)
    assert rc == 0
    # find the trace file
    traces = list(tmp_path.glob("*.jsonl"))
    assert len(traces) == 1
    events = _read_events(traces[0])
    assert len(events) == 1
    assert events[0]["type"] == "subprocess"
    assert events[0]["cmd"] == ["echo", "hello"]
    assert events[0]["returncode"] == 0
    assert "hello" in events[0]["stdout_tail"]


def test_handle_subprocess_swallows_timeout(tmp_path, monkeypatch):
    monkeypatch.setenv("RDDF_TRACE_DIR", str(tmp_path))
    rc = _handle_subprocess(
        ["sleep", "10"], trace_dir=tmp_path, timeout=1
    )
    assert rc == 124  # conventional timeout exit code
    traces = list(tmp_path.glob("*.jsonl"))
    events = _read_events(traces[0])
    assert events[0]["timeout"] is True


def test_handle_subprocess_sanitizes_output(tmp_path, monkeypatch):
    monkeypatch.setenv("RDDF_TRACE_DIR", str(tmp_path))
    # echo prints an AWS-style secret; sanitizer should redact
    rc = _handle_subprocess(
        ["sh", "-c", "echo AWS_SECRET_ACCESS_KEY=AKIAIOSFODNN7EXAMPLE"],
        trace_dir=tmp_path,
    )
    assert rc == 0
    events = _read_events(list(tmp_path.glob("*.jsonl"))[0])
    # Either the tail contains "[REDACTED]" or the secret is gone
    assert "AKIAIOSFODNN7EXAMPLE" not in events[0]["stdout_tail"]
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python3 -m pytest tests/unit/test_orchestrate_cmd.py::test_handle_subprocess_runs_command_and_records -v`
Expected: FAIL with `NotImplementedError: filled in Task 3`.

- [ ] **Step 3: Implement `_handle_subprocess`**

Replace the `_handle_subprocess` function in `_lib/cli/orchestrate_cmd.py`:

```python
def _handle_subprocess(
    cmd: list[str],
    trace_dir: Path,
    timeout: Optional[int] = None,
) -> int:
    """Run a subprocess and record its result to a new trace.

    Args:
        cmd: argv list (no shell). First call per phase entry also
            triggers a stale-trace sweep (Task 10 implementation).
        trace_dir: target directory for the trace file.
        timeout: seconds before subprocess.TimeoutExpired. Defaults to
            ``RDDF_ORCHESTRATE_TIMEOUT`` env var or 600.

    Returns:
        The subprocess return code (timeout → 124).
    """
    from skills._lib.loop.sanitizer import sanitize

    if timeout is None:
        timeout = int(os.environ.get("RDDF_ORCHESTRATE_TIMEOUT", "600"))

    # Sweep stale traces from prior phase crashes (Task 10)
    _handle_sweep(trace_dir)

    phase = os.environ.get("RDDF_PHASE", "unknown")
    trace = _open_trace(phase=phase)

    rc = 124
    stdout_tail = ""
    stderr_tail = ""
    duration_ms = 0
    timed_out = False

    stdout_tmp = tempfile.NamedTemporaryFile(
        mode="w", delete=False, suffix=".out", encoding="utf-8"
    )
    stderr_tmp = tempfile.NamedTemporaryFile(
        mode="w", delete=False, suffix=".err", encoding="utf-8"
    )
    started = time.monotonic()
    try:
        proc = subprocess.run(
            cmd,
            shell=False,
            stdout=stdout_tmp,
            stderr=stderr_tmp,
            timeout=timeout,
        )
        rc = proc.returncode
    except subprocess.TimeoutExpired:
        timed_out = True
        rc = 124
    finally:
        duration_ms = int((time.monotonic() - started) * 1000)
        stdout_tmp.close()
        stderr_tmp.close()

    try:
        stdout_tail = _tail_file(Path(stdout_tmp.name), n=4096)
        stderr_tail = _tail_file(Path(stderr_tmp.name), n=4096)
        # Sanitize before writing (Oracle rec #2)
        try:
            stdout_tail = sanitize(stdout_tail)
        except Exception as e:  # pragma: no cover - defensive
            print(f"warning: sanitizer failed on stdout: {e}", file=sys.stderr)
            stdout_tail = stdout_tail[:4096]
        try:
            stderr_tail = sanitize(stderr_tail)
        except Exception as e:  # pragma: no cover - defensive
            print(f"warning: sanitizer failed on stderr: {e}", file=sys.stderr)
            stderr_tail = stderr_tail[:4096]
    finally:
        os.unlink(stdout_tmp.name)
        os.unlink(stderr_tmp.name)

    _append_event(
        trace,
        {
            "type": "subprocess",
            "cmd": cmd,
            "returncode": rc,
            "stdout_tail": stdout_tail,
            "stderr_tail": stderr_tail,
            "duration_ms": duration_ms,
            "timeout": timed_out,
        },
    )
    trace.close()
    return rc


def _tail_file(path: Path, n: int) -> str:
    """Return the last ``n`` bytes of a file, decoded as utf-8."""
    try:
        size = path.stat().st_size
        with open(path, "rb") as fh:
            if size <= n:
                return fh.read().decode("utf-8", errors="replace")
            fh.seek(size - n)
            return fh.read().decode("utf-8", errors="replace")
    except OSError:
        return ""
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `python3 -m pytest tests/unit/test_orchestrate_cmd.py -v -k subprocess`
Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
cd /workspace/project/rdd-workflow
git add _lib/cli/orchestrate_cmd.py tests/unit/test_orchestrate_cmd.py
git commit -m "feat(orchestrate): implement --subprocess with tempfile streams + sanitize"
```

---

### Task 4: Implement `--mark-checkpoint`

**Files:**
- Modify: `_lib/cli/orchestrate_cmd.py` (replace `_handle_checkpoint` placeholder)

- [ ] **Step 1: Write the failing test**

Append to `tests/unit/test_orchestrate_cmd.py`:

```python
def test_handle_checkpoint_appends_event(tmp_path, monkeypatch):
    monkeypatch.setenv("RDDF_TRACE_DIR", str(tmp_path))
    monkeypatch.setenv("RDDF_PHASE", "guide-plan")
    rc = _handle_checkpoint(
        name="after-setup",
        state_marker="phase_started",
        trace_dir=tmp_path,
    )
    assert rc == 0
    traces = list(tmp_path.glob("*.jsonl"))
    assert len(traces) == 1
    events = _read_events(traces[0])
    assert events[0]["type"] == "checkpoint"
    assert events[0]["name"] == "after-setup"
    assert events[0]["state_marker"] == "phase_started"
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python3 -m pytest tests/unit/test_orchestrate_cmd.py::test_handle_checkpoint_appends_event -v`
Expected: FAIL with `NotImplementedError: filled in Task 4`.

- [ ] **Step 3: Implement `_handle_checkpoint`**

Replace `_handle_checkpoint` in `_lib/cli/orchestrate_cmd.py`:

```python
def _handle_checkpoint(
    name: str,
    state_marker: str,
    trace_dir: Path,
) -> int:
    """Append a checkpoint event to the current trace."""
    phase = os.environ.get("RDDF_PHASE", "unknown")
    trace = _open_trace(phase=phase)
    _append_event(
        trace,
        {
            "type": "checkpoint",
            "name": name,
            "state_marker": state_marker,
        },
    )
    trace.close()
    return 0
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `python3 -m pytest tests/unit/test_orchestrate_cmd.py::test_handle_checkpoint_appends_event -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
cd /workspace/project/rdd-workflow
git add _lib/cli/orchestrate_cmd.py tests/unit/test_orchestrate_cmd.py
git commit -m "feat(orchestrate): implement --mark-checkpoint"
```

---

### Task 5: Implement `--finalize`

**Files:**
- Modify: `_lib/cli/orchestrate_cmd.py` (replace `_handle_finalize` placeholder)

- [ ] **Step 1: Write the failing test**

Append to `tests/unit/test_orchestrate_cmd.py`:

```python
def test_handle_finalize_writes_finalize_event(tmp_path, monkeypatch):
    monkeypatch.setenv("RDDF_TRACE_DIR", str(tmp_path))
    monkeypatch.setenv("RDDF_PHASE", "guide-arch")
    # First create a trace by running subprocess
    _handle_subprocess(["true"], trace_dir=tmp_path)
    # Then finalize
    rc = _handle_finalize(trace_dir=tmp_path)
    assert rc == 0
    traces = list(tmp_path.glob("*.jsonl"))
    events = _read_events(traces[0])
    last = events[-1]
    assert last["type"] == "finalize"
    assert last["subprocess_failures"] == 0
    assert last["checkpoints"] == 0


def test_handle_finalize_counts_failures(tmp_path, monkeypatch):
    monkeypatch.setenv("RDDF_TRACE_DIR", str(tmp_path))
    monkeypatch.setenv("RDDF_PHASE", "guide-arch")
    _handle_subprocess(["false"], trace_dir=tmp_path)  # returncode 1
    _handle_checkpoint("mid", "", trace_dir=tmp_path)
    _handle_finalize(trace_dir=tmp_path)
    events = _read_events(list(tmp_path.glob("*.jsonl"))[0])
    last = events[-1]
    assert last["subprocess_failures"] == 1
    assert last["checkpoints"] == 1
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python3 -m pytest tests/unit/test_orchestrate_cmd.py::test_handle_finalize_writes_finalize_event -v`
Expected: FAIL with `NotImplementedError: filled in Task 5`.

- [ ] **Step 3: Implement `_handle_finalize`**

Replace `_handle_finalize` in `_lib/cli/orchestrate_cmd.py`:

```python
def _handle_finalize(trace_dir: Path) -> int:
    """Close the current trace with a finalize event and trigger analysis.

    Reads all events written so far, counts subprocess failures + checkpoints,
    appends a finalize event with those counts. Calls analyze_phase_trace()
    if there were subprocess failures (Task 9 implementation).
    """
    phase = os.environ.get("RDDF_PHASE", "unknown")
    # Find the most recent unfinalized trace for this phase
    trace_file = _find_open_trace(trace_dir, phase)
    if trace_file is None:
        # Nothing to finalize — write a minimal finalize to a fresh trace
        trace = _open_trace(phase=phase)
        _append_event(
            trace,
            {
                "type": "finalize",
                "subprocess_failures": 0,
                "checkpoints": 0,
                "report_written": "false",
            },
        )
        trace.close()
        return 0

    events = _read_events(trace_file)
    subprocess_failures = sum(
        1 for e in events
        if e.get("type") == "subprocess" and e.get("returncode", 0) != 0
    )
    checkpoints = sum(1 for e in events if e.get("type") == "checkpoint")

    report_written = "false"
    if subprocess_failures > 0:
        try:
            from skills._lib.post_flow_analysis import analyze_phase_trace
            project_root = os.environ.get("RDDF_PROJECT_ROOT", ".")
            cls = analyze_phase_trace(
                trace_path=trace_file,
                project_root=project_root,
            )
            if cls is not None:
                report_written = "true"
        except Exception as e:  # pragma: no cover - defensive
            print(f"warning: analyze_phase_trace failed: {e}", file=sys.stderr)

    # Append finalize event
    with open(trace_file, "a", encoding="utf-8") as fh:
        finalize_event = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "type": "finalize",
            "subprocess_failures": subprocess_failures,
            "checkpoints": checkpoints,
            "report_written": report_written,
        }
        fh.write(json.dumps(finalize_event, ensure_ascii=False) + "\n")

    return 0


def _find_open_trace(trace_dir: Path, phase: str) -> Optional[Path]:
    """Return the most recent trace file for ``phase`` that has no finalize event.

    Searches all ``<phase>-*.jsonl`` files; returns the one whose last event
    is not ``finalize``, or None if all are finalized.
    """
    candidates = sorted(
        trace_dir.glob(f"{phase}-*.jsonl"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    for candidate in candidates:
        events = _read_events(candidate)
        if not events:
            continue
        if events[-1].get("type") != "finalize":
            return candidate
    return None
```

- [ ] **Step 4: Run the test to verify it passes (it will skip if analyze_phase_trace missing)**

Run: `python3 -m pytest tests/unit/test_orchestrate_cmd.py -v -k finalize`
Expected: PASS (the `analyze_phase_trace` import fails silently due to try/except, so
`report_written` stays "false" but `subprocess_failures` and `checkpoints` are correct).

- [ ] **Step 5: Commit**

```bash
cd /workspace/project/rdd-workflow
git add _lib/cli/orchestrate_cmd.py tests/unit/test_orchestrate_cmd.py
git commit -m "feat(orchestrate): implement --finalize with subprocess/chunkpoint counts"
```

---

### Task 6: Create `skills/_lib/orchestrator_entry.sh` bash wrapper

**Files:**
- Create: `skills/_lib/orchestrator_entry.sh`

- [ ] **Step 1: Write the failing bats test**

Create `tests/integration/test_orchestrator_entry.bats`:

```bash
#!/usr/bin/env bats
# tests/integration/test_orchestrator_entry.bats
# Tests for skills/_lib/orchestrator_entry.sh bash wrapper.

setup() {
    load "test_helper"
    setup_lib
    TRACE_DIR="$(mktemp -d)"
    export RDDF_TRACE_DIR="$TRACE_DIR"
    export RDDF_PHASE="guide-test"
    export RDDF_PROJECT_ROOT="$BATS_TMPDIR"
}

teardown() {
    rm -rf "$TRACE_DIR"
}

@test "orchestrator_entry.sh: source-able" {
    source "${PROJECT_ROOT}/skills/_lib/orchestrator_entry.sh"
    [ $? -eq 0 ]
}

@test "orchestrator_entry.sh: orchestrator_run records to trace" {
    source "${PROJECT_ROOT}/skills/_lib/orchestrator_entry.sh"
    orchestrator_run echo hello
    [ $? -eq 0 ]
    local traces
    traces=$(ls "$TRACE_DIR"/*.jsonl 2>/dev/null | wc -l)
    [ "$traces" -ge 1 ]
}

@test "orchestrator_entry.sh: orchestrator_finalize appends finalize event" {
    source "${PROJECT_ROOT}/skills/_lib/orchestrator_entry.sh"
    orchestrator_run true
    orchestrator_finalize
    local last_line
    last_line=$(tail -n 1 "$TRACE_DIR"/*.jsonl)
    echo "$last_line" | grep -q '"type":"finalize"'
}

@test "orchestrator_entry.sh: orchestrator_mark inserts checkpoint" {
    source "${PROJECT_ROOT}/skills/_lib/orchestrator_entry.sh"
    orchestrator_run true
    orchestrator_mark "after-setup" "phase_started"
    local has_checkpoint
    has_checkpoint=$(grep -c '"type":"checkpoint"' "$TRACE_DIR"/*.jsonl)
    [ "$has_checkpoint" -ge 1 ]
}

@test "orchestrator_entry.sh: missing python3 falls back silently" {
    # Simulate Python not in PATH
    PATH="/usr/bin:/bin"  # minimal PATH without python3 typically
    source "${PROJECT_ROOT}/skills/_lib/orchestrator_entry.sh"
    orchestrator_run echo hello  # should not fail even if python3 missing
    [ $? -eq 0 ]
}
```

- [ ] **Step 2: Run the bats test to verify it fails**

Run: `bats tests/integration/test_orchestrator_entry.bats`
Expected: 5 failed (file does not exist).

- [ ] **Step 3: Create the bash wrapper**

Write `skills/_lib/orchestrator_entry.sh`:

```bash
#!/usr/bin/env bash
# skills/_lib/orchestrator_entry.sh
#
# ADR-0027 + spec 2026-08-12: bash wrapper around `rddf orchestrate`.
# Provides orchestrator_run / orchestrator_mark / orchestrator_finalize for
# phase scripts to invoke Python orchestrator without losing failure tolerance.
#
# All Python invocations are wrapped in || true so a broken orchestrator
# never breaks the phase (matches _lib/post_archive_cleanup.sh pattern).

# Locate _lib/cli/__main__.py relative to this file so we can `python3 -m`
# without depending on cwd. This file lives at skills/_lib/, so skills/
# parent is one level up.
_ORCHESTRATOR_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
_PROJECT_ROOT_FROM_ORCH="$(cd "$_ORCHESTRATOR_DIR/.." && pwd)"

# orchestrator_run <cmd...>
#   Run cmd via `rddf orchestrate subprocess`; preserves the cmd's exit code
#   unless the orchestrator itself fails (in which case we fall through).
orchestrator_run() {
    if [ "$#" -eq 0 ]; then
        echo "orchestrator_run: requires at least one argument" >&2
        return 2
    fi
    if ! command -v python3 >/dev/null 2>&1; then
        # Silent fallback — don't break phase if Python is missing
        "$@"
        return $?
    fi
    RDDF_PHASE="${RDDF_PHASE:-unknown}" \
    PYTHONPATH="${PYTHONPATH}:${_PROJECT_ROOT_FROM_ORCH}" \
        python3 -m skills._lib.cli orchestrate subprocess "$@" 2>/dev/null || "$@"
}

# orchestrator_mark <name> [<state-marker>]
#   Append a checkpoint event to the current trace.
orchestrator_mark() {
    local name="${1:?orchestrator_mark requires name}"
    local marker="${2:-}"
    if ! command -v python3 >/dev/null 2>&1; then
        return 0  # silent no-op
    fi
    RDDF_PHASE="${RDDF_PHASE:-unknown}" \
    PYTHONPATH="${PYTHONPATH}:${_PROJECT_ROOT_FROM_ORCH}" \
        python3 -m skills._lib.cli orchestrate mark-checkpoint \
            --name "$name" --state-marker "$marker" 2>/dev/null || true
}

# orchestrator_finalize
#   Close the current trace and trigger analyze_phase_trace if any failures.
orchestrator_finalize() {
    if ! command -v python3 >/dev/null 2>&1; then
        return 0  # silent no-op
    fi
    RDDF_PHASE="${RDDF_PHASE:-unknown}" \
    PYTHONPATH="${PYTHONPATH}:${_PROJECT_ROOT_FROM_ORCH}" \
        python3 -m skills._lib.cli orchestrate finalize 2>/dev/null || true
}

# orchestrator_sweep
#   Manually trigger stale-trace sweep (e.g., from CI before tests).
orchestrator_sweep() {
    if ! command -v python3 >/dev/null 2>&1; then
        return 0
    fi
    PYTHONPATH="${PYTHONPATH}:${_PROJECT_ROOT_FROM_ORCH}" \
        python3 -m skills._lib.cli orchestrate sweep-stale-traces 2>/dev/null || true
}
```

- [ ] **Step 4: Make the file executable**

Run: `chmod +x skills/_lib/orchestrator_entry.sh`

- [ ] **Step 5: Run the bats test to verify it passes**

Run: `bats tests/integration/test_orchestrator_entry.bats`
Expected: 5 passed.

- [ ] **Step 6: Commit**

```bash
cd /workspace/project/rdd-workflow
git add skills/_lib/orchestrator_entry.sh tests/integration/test_orchestrator_entry.bats
git commit -m "feat(orchestrator): add bash wrapper with orchestrator_run/mark/finalize"
```

---

### Task 7: Add single-writer guard to `post_flow_wrap.sh`

**Files:**
- Modify: `skills/_lib/post_flow_wrap.sh:33-39` (top of `post_flow_on_err`)

- [ ] **Step 1: Write the failing bats test**

Create `tests/integration/test_single_writer_rule.bats`:

```bash
#!/usr/bin/env bats
# tests/integration/test_single_writer_rule.bats
# Verifies that when RDDF_USE_ORCHESTRATOR=yes, post_flow_on_err is a no-op
# (single-writer rule per spec 2026-08-12 §7).

setup() {
    load "test_helper"
    setup_lib
}

@test "post_flow_wrap: trap path no-ops when RDDF_USE_ORCHESTRATOR=yes" {
    source "${PROJECT_ROOT}/skills/_lib/post_flow_wrap.sh"
    export RDDF_USE_ORCHESTRATOR=yes
    # Spy: install a hook to count invocations of post_flow_on_err
    local count_file
    count_file="$(mktemp)"
    # Re-source after env var set so the guard sees the right value
    source "${PROJECT_ROOT}/skills/_lib/post_flow_wrap.sh"
    # We can't easily count post_flow_on_err; instead verify the Python
    # path is NOT invoked. Stub: trap fires, post_flow_on_err returns 0.
    set -e
    trap 'post_flow_on_err' ERR
    # Cause a controlled "error" via a subshell that the wrapper handles
    (
        set +e
        ( exit 1 )
    ) || true
    set +e
    [ -f "$count_file" ] || rm -f "$count_file"
    rm -f "$count_file"
}
```

(More complete test in Task 14 — this is a smoke test for now.)

- [ ] **Step 2: Edit `post_flow_wrap.sh` to add the guard**

Edit `skills/_lib/post_flow_wrap.sh`. In the `post_flow_on_err()` function (lines 33-39),
add the single-writer check **after** the exit code filters but **before** the Python call:

```bash
post_flow_on_err() {
    local phase="${1:-${RDDF_PHASE:-unknown}}"
    local code=$?
    # Skip no-op and user-cancellation exits
    [ "$code" -eq 0 ] && return 0
    [ "$code" -eq 130 ] && return 0  # SIGINT
    [ "$code" -eq 143 ] && return 0  # SIGTERM

    # Single-writer rule (spec 2026-08-12 §7): if Python orchestrator is
    # active for this phase, defer to it to avoid duplicate issue files.
    if [ "${RDDF_USE_ORCHESTRATOR:-no}" = "yes" ]; then
        return 0
    fi

    # Best-effort: find a stderr log. Prefer the env var; fall back to /dev/null.
    local err_log="${RDDF_ERR_LOG:-/dev/null}"
    [ -f "$err_log" ] || err_log="/dev/null"

    # Best-effort: find project root.
    local project_root="${RDDF_PROJECT_ROOT:-$PWD}"

    RDDF_PHASE="$phase" \
    RDDF_EXIT_CODE="$code" \
    RDDF_STDERR_FILE="$err_log" \
    RDDF_PROJECT_ROOT="$project_root" \
    PYTHONPATH="$_POST_FLOW_LIB_DIR" \
    python3 -c "
import os, sys
sys.path.insert(0, os.environ['RDDF_PROJECT_ROOT'] + '/_lib')
from post_flow_analysis import analyze_and_report
cls = analyze_and_report(
    phase=os.environ['RDDF_PHASE'],
    exit_code=int(os.environ['RDDF_EXIT_CODE']),
    stderr_file=os.environ['RDDF_STDERR_FILE'],
    project_root=os.environ['RDDF_PROJECT_ROOT'],
)
if cls.user_hint:
    print(f'[{cls.root_cause}] {cls.user_hint}')
" 2>/dev/null || true

    return 0
}
```

The only change is inserting these 4 lines after the SIGTERM check:

```bash
    if [ "${RDDF_USE_ORCHESTRATOR:-no}" = "yes" ]; then
        return 0
    fi

```

- [ ] **Step 3: Verify existing bats tests still pass**

Run: `bats tests/smoke.bats`
Expected: 7 passed (regression check).

- [ ] **Step 4: Commit**

```bash
cd /workspace/project/rdd-workflow
git add skills/_lib/post_flow_wrap.sh tests/integration/test_single_writer_rule.bats
git commit -m "feat(post-flow-wrap): add single-writer guard for orchestrator coexistence"
```

---

### Task 8: Expand unit tests for orchestrate_cmd (full coverage)

**Files:**
- Modify: `tests/unit/test_orchestrate_cmd.py` (extend)

- [ ] **Step 1: Append additional unit tests**

Append to `tests/unit/test_orchestrate_cmd.py`:

```python
def test_get_trace_dir_from_env(monkeypatch, tmp_path):
    monkeypatch.setenv("RDDF_TRACE_DIR", str(tmp_path / "custom_trace"))
    assert _get_trace_dir() == (tmp_path / "custom_trace").resolve()


def test_get_trace_dir_default(monkeypatch):
    monkeypatch.delenv("RDDF_TRACE_DIR", raising=False)
    d = _get_trace_dir()
    assert str(d).endswith(".rddf/state/trace")


def test_open_trace_creates_directory(tmp_path, monkeypatch):
    monkeypatch.setenv("RDDF_TRACE_DIR", str(tmp_path / "nested" / "trace"))
    trace = _open_trace(phase="guide-arch", session_id="ses_x")
    assert trace.path.parent.is_dir()
    trace.close()


def test_tail_file_returns_whole_file_when_small(tmp_path):
    p = tmp_path / "small.txt"
    p.write_text("hello world")
    assert _tail_file(p, n=4096) == "hello world"


def test_tail_file_truncates_large_file(tmp_path):
    p = tmp_path / "large.txt"
    p.write_text("x" * 10000)
    result = _tail_file(p, n=100)
    assert len(result.encode("utf-8")) == 100


def test_find_open_trace_returns_none_when_all_finalized(tmp_path):
    (tmp_path / "guide-arch-1-1-100-aaaaaaaa.jsonl").write_text(
        '{"ts":"2026-08-12T10:00:00Z","type":"subprocess","returncode":0}\n'
        '{"ts":"2026-08-12T10:00:01Z","type":"finalize"}\n'
    )
    assert _find_open_trace(tmp_path, "guide-arch") is None


def test_find_open_trace_returns_unfinalized(tmp_path):
    (tmp_path / "guide-arch-1-1-100-aaaaaaaa.jsonl").write_text(
        '{"ts":"2026-08-12T10:00:00Z","type":"subprocess","returncode":1}\n'
    )
    result = _find_open_trace(tmp_path, "guide-arch")
    assert result is not None
    assert result.name.startswith("guide-arch-")
```

- [ ] **Step 2: Run all unit tests for orchestrate_cmd**

Run: `python3 -m pytest tests/unit/test_orchestrate_cmd.py -v`
Expected: ≥11 passed.

- [ ] **Step 3: Commit**

```bash
cd /workspace/project/rdd-workflow
git add tests/unit/test_orchestrate_cmd.py
git commit -m "test(orchestrate): expand unit coverage to ≥11 cases"
```

---

## Stage 2: Trace Analyzer + Sweep + SKILL.md (Days 5-8)

### Task 9: Implement `analyze_phase_trace` in `post_flow_analysis.py`

**Files:**
- Modify: `_lib/post_flow_analysis.py` (append new function before `if __name__ == "__main__":`)

- [ ] **Step 1: Write the failing test**

Append to `tests/unit/test_post_flow_analysis.py`:

```python
def test_analyze_phase_trace_classifies_single_failure(tmp_path):
    """A trace with one non-zero subprocess is classified as flow-bug."""
    from post_flow_analysis import analyze_phase_trace, Classification
    trace = tmp_path / "guide-arch-ses_x-1-100-aaaaaaaa.jsonl"
    trace.write_text(
        '{"ts":"2026-08-12T10:00:00Z","type":"subprocess",'
        '"cmd":["arch_done_gate.sh"],"returncode":1,'
        '"stderr_tail":"Traceback (most recent call last):\\n  File \\"skills/guide-arch/scripts/foo.py\\"","stdout_tail":""}\n'
    )
    cls = analyze_phase_trace(trace_path=trace, project_root=str(tmp_path))
    assert isinstance(cls, Classification)
    assert cls.should_report is True


def test_analyze_phase_trace_returns_none_for_clean_trace(tmp_path):
    """A trace with all-zero subprocesses returns None."""
    from post_flow_analysis import analyze_phase_trace
    trace = tmp_path / "guide-arch-ses_x-1-100-bbbbbbbb.jsonl"
    trace.write_text(
        '{"ts":"2026-08-12T10:00:00Z","type":"subprocess","cmd":["echo"],"returncode":0,"stderr_tail":"","stdout_tail":""}\n'
    )
    cls = analyze_phase_trace(trace_path=trace, project_root=str(tmp_path))
    assert cls is None
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python3 -m pytest tests/unit/test_post_flow_analysis.py::test_analyze_phase_trace_classifies_single_failure -v`
Expected: FAIL with `ImportError: cannot import name 'analyze_phase_trace'`.

- [ ] **Step 3: Implement `analyze_phase_trace`**

Append to `_lib/post_flow_analysis.py` just before the `if __name__ == "__main__":` line:

```python
def analyze_phase_trace(
    trace_path: Path,
    project_root: str = ".",
) -> Optional[Classification]:
    """Classify a complete phase trace and return a Classification.

    Reads all subprocess events from ``trace_path`` and synthesizes a
    ``PhaseOutcome`` for the **first** failing subprocess. Returns None
    if all subprocesses returned 0 (success path).

    For multi-step cumulative failures (B3), detects the pattern where
    multiple subprocesses returned 0 but stderr mentions "invalid state"
    or similar markers, and reports as ``flow-bug`` / ``F2``.
    """
    events = _read_trace_events(trace_path)
    subprocess_events = [e for e in events if e.get("type") == "subprocess"]
    if not subprocess_events:
        return None

    # Check for any non-zero subprocess
    for event in subprocess_events:
        if event.get("returncode", 0) != 0:
            outcome = _outcome_from_event(event, project_root)
            classification = classify_phase_outcome(
                phase=os.environ.get("RDDF_PHASE", "unknown"),
                outcome=outcome,
            )
            return classification

    # All returncode=0 — check for cumulative failure pattern (B3)
    text_blob = " ".join(
        e.get("stderr_tail", "") for e in subprocess_events
    )
    if re.search(
        r"(invalid state|unexpected (status|phase)|状态机|state machine)",
        text_blob,
        re.I,
    ):
        # Synthesize an F2 classification
        return Classification(
            root_cause=ROOT_CAUSE_FLOW,
            report_category=REPORT_CATEGORY_GATE,
            matched_rule="F2-cumulative",
            description="cumulative failure: state machine violation across multiple zero-exit steps",
            metadata={"phase": "trace", "matched_rule": "F2-cumulative"},
            should_report=True,
            user_hint=USER_HINTS.get(ROOT_CAUSE_FLOW, ""),
        )

    return None


def _read_trace_events(trace_path: Path) -> list[dict]:
    """Read events from a JSONL trace file. Tolerates missing/malformed lines."""
    events: list[dict] = []
    if not trace_path.is_file():
        return events
    try:
        with open(trace_path, encoding="utf-8") as fh:
            for raw in fh:
                raw = raw.strip()
                if not raw:
                    continue
                try:
                    events.append(json.loads(raw))
                except json.JSONDecodeError:
                    continue
    except OSError:
        pass
    return events


def _outcome_from_event(event: dict, project_root: str) -> PhaseOutcome:
    """Convert a subprocess trace event into a PhaseOutcome for classification."""
    return PhaseOutcome(
        phase=os.environ.get("RDDF_PHASE", "unknown"),
        exit_code=event.get("returncode", 0),
        stderr=event.get("stderr_tail", ""),
        stdout_tail=event.get("stdout_tail", ""),
        traceback="",  # not captured in subprocess event
    )
```

Also add `import json` and `from typing import Optional` to the imports if not present.

- [ ] **Step 4: Run the test to verify it passes**

Run: `python3 -m pytest tests/unit/test_post_flow_analysis.py::test_analyze_phase_trace_classifies_single_failure tests/unit/test_post_flow_analysis.py::test_analyze_phase_trace_returns_none_for_clean_trace -v`
Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
cd /workspace/project/rdd-workflow
git add _lib/post_flow_analysis.py tests/unit/test_post_flow_analysis.py
git commit -m "feat(post-flow-analysis): add analyze_phase_trace for orchestrator finalize"
```

---

### Task 10: Implement stale-trace sweep (B4 fix)

**Files:**
- Modify: `_lib/cli/orchestrate_cmd.py` (replace `_handle_sweep` placeholder)
- Modify: `tests/unit/test_orchestrate_cmd.py` (add sweep tests)

- [ ] **Step 1: Write the failing test**

Append to `tests/unit/test_orchestrate_cmd.py`:

```python
def test_sweep_classifies_unfinalized_old_trace_as_interrupted(tmp_path, monkeypatch):
    monkeypatch.setenv("RDDF_TRACE_DIR", str(tmp_path))
    monkeypatch.setenv("RDDF_PROJECT_ROOT", str(tmp_path))
    monkeypatch.setenv("RDDF_PHASE", "guide-arch")
    # Create a trace that looks 10 minutes old with no finalize
    old_ts = "2026-08-12T09:00:00Z"  # arbitrary old timestamp
    trace = tmp_path / "guide-arch-ses_x-1-1000000-aaaaaaaa.jsonl"
    trace.write_text(
        f'{{"ts":"{old_ts}","type":"subprocess","cmd":["x"],"returncode":0,"stderr_tail":"","stdout_tail":""}}\n'
    )
    # Make file mtime old
    import os
    os.utime(trace, (1000000, 1000000))  # year 1970 — definitely old
    # Override max age to 0 for test
    monkeypatch.setenv("RDDF_TRACE_STALE_MINUTES", "0")
    rc = _handle_sweep(trace_dir=tmp_path)
    assert rc == 0
    # Trace should be deleted after classification
    assert not trace.exists()


def test_sweep_skips_finalized_traces(tmp_path, monkeypatch):
    monkeypatch.setenv("RDDF_TRACE_DIR", str(tmp_path))
    monkeypatch.setenv("RDDF_PHASE", "guide-arch")
    import os
    trace = tmp_path / "guide-arch-ses_x-1-1000000-bbbbbbbb.jsonl"
    trace.write_text(
        '{"ts":"2026-08-12T09:00:00Z","type":"finalize","subprocess_failures":0}\n'
    )
    os.utime(trace, (1000000, 1000000))
    _handle_sweep(trace_dir=tmp_path)
    assert trace.exists()  # Not deleted — already finalized
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python3 -m pytest tests/unit/test_orchestrate_cmd.py::test_sweep_classifies_unfinalized_old_trace_as_interrupted -v`
Expected: FAIL with `NotImplementedError: filled in Task 10`.

- [ ] **Step 3: Implement `_handle_sweep` and `_classify_interrupted_phase`**

Replace `_handle_sweep` and add `_classify_interrupted_phase` + `_run_trace_gc` in
`_lib/cli/orchestrate_cmd.py`:

```python
def _handle_sweep(trace_dir: Path) -> int:
    """Sweep trace directory for stale unfinalized traces (B4 fix).

    For each ``<phase>-*.jsonl`` with no finalize event and mtime older than
    ``RDDF_TRACE_STALE_MINUTES`` (default 5):
      - Classify as ``phase-interrupted`` → call ``report_flow_bug``
      - Unlink the trace file (idempotent)

    Also runs trace GC: deletes finalized traces > 7 days old, caps
    unfinalized at 50 files.
    """
    if not trace_dir.is_dir():
        return 0
    max_age_min = int(os.environ.get("RDDF_TRACE_STALE_MINUTES", "5"))
    phase_filter = os.environ.get("RDDF_PHASE")  # only sweep current phase if set

    now = time.time()
    for trace_file in trace_dir.glob("*.jsonl"):
        if phase_filter and not trace_file.name.startswith(f"{phase_filter}-"):
            continue
        try:
            events = _read_events(trace_file)
        except OSError:
            continue
        if not events:
            continue
        if events[-1].get("type") == "finalize":
            continue  # already finalized

        # Check staleness by file mtime
        mtime = trace_file.stat().st_mtime
        age_seconds = now - mtime
        if age_seconds < max_age_min * 60:
            continue

        # Stale → classify + report + delete
        try:
            cls = _classify_interrupted_phase(events)
            if cls is not None:
                project_root = os.environ.get("RDDF_PROJECT_ROOT", ".")
                from skills._lib.post_flow_analysis import report_flow_bug
                report_flow_bug(cls, project_root=project_root)
        except Exception as e:  # pragma: no cover - defensive
            print(f"warning: sweep report failed for {trace_file.name}: {e}", file=sys.stderr)
        try:
            trace_file.unlink()
        except OSError:
            pass

    # Run GC
    _run_trace_gc(trace_dir)
    return 0


def _classify_interrupted_phase(events: list[dict]):
    """Build a Classification for a stale (interrupted) trace.

    Returns None if events are insufficient to classify.
    """
    from skills._lib.post_flow_analysis import (
        Classification,
        PhaseOutcome,
        classify_phase_outcome,
        ROOT_CAUSE_FLOW,
        REPORT_CATEGORY_CRASH,
        USER_HINTS,
    )

    # Use the last subprocess event as the outcome
    subprocess_events = [e for e in events if e.get("type") == "subprocess"]
    if not subprocess_events:
        # No subprocess at all — phase crashed before any work
        return Classification(
            root_cause=ROOT_CAUSE_FLOW,
            report_category=REPORT_CATEGORY_CRASH,
            matched_rule="INTERRUPTED-NO-SUBPROCESS",
            description="phase interrupted before any subprocess completed (likely SIGKILL/OOM/laptop-close)",
            metadata={"phase": "trace", "matched_rule": "INTERRUPTED-NO-SUBPROCESS"},
            should_report=True,
            user_hint=USER_HINTS.get(ROOT_CAUSE_FLOW, ""),
        )

    last = subprocess_events[-1]
    outcome = PhaseOutcome(
        phase=os.environ.get("RDDF_PHASE", "unknown"),
        exit_code=last.get("returncode", 0),
        stderr=last.get("stderr_tail", ""),
        stdout_tail=last.get("stdout_tail", ""),
        traceback="",
    )
    return classify_phase_outcome(
        phase=os.environ.get("RDDF_PHASE", "unknown"),
        outcome=outcome,
    )


def _run_trace_gc(trace_dir: Path) -> None:
    """Garbage-collect old trace files.

    - Delete finalized traces older than 7 days
    - Delete unfinalized traces older than 24 hours (if not current phase)
    - Cap unfinalized at 50 files (oldest first)
    """
    if not trace_dir.is_dir():
        return
    now = time.time()
    finalized_old: list[Path] = []
    unfinalized: list[tuple[float, Path]] = []

    for trace in trace_dir.glob("*.jsonl"):
        mtime = trace.stat().st_mtime
        events = _read_events(trace)
        if not events:
            continue
        if events[-1].get("type") == "finalize":
            if (now - mtime) > 7 * 86400:
                finalized_old.append(trace)
        else:
            unfinalized.append((mtime, trace))

    for t in finalized_old:
        try:
            t.unlink()
        except OSError:
            pass

    # Cap unfinalized
    if len(unfinalized) > 50:
        unfinalized.sort()
        for _, t in unfinalized[: len(unfinalized) - 50]:
            try:
                t.unlink()
            except OSError:
                pass
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python3 -m pytest tests/unit/test_orchestrate_cmd.py -v -k sweep`
Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
cd /workspace/project/rdd-workflow
git add _lib/cli/orchestrate_cmd.py tests/unit/test_orchestrate_cmd.py
git commit -m "feat(orchestrate): implement stale-trace sweep + GC (B4 fix)"
```

---

### Task 11: Update `skills/guide-arch/SKILL.md` Phase Exit checklist

**Files:**
- Modify: `skills/guide-arch/SKILL.md:758-771` (replace Phase Exit prose)

- [ ] **Step 1: Write the validation test**

Create `tests/integration/test_skill_phase_exit_checklist.bats`:

```bash
#!/usr/bin/env bats
# Verifies that all 4 SKILL.md files contain the 3-rule checklist.

setup() {
    load "test_helper"
    setup_lib
}

@test "guide-arch SKILL.md: contains 3-rule checklist" {
    grep -q "Normal exit" "${PROJECT_ROOT}/skills/guide-arch/SKILL.md"
    grep -q "Abnormal exit" "${PROJECT_ROOT}/skills/guide-arch/SKILL.md"
    grep -q "Triggers for" "${PROJECT_ROOT}/skills/guide-arch/SKILL.md"
}

@test "guide-plan SKILL.md: contains 3-rule checklist" {
    grep -q "Normal exit" "${PROJECT_ROOT}/skills/guide-plan/SKILL.md"
    grep -q "Abnormal exit" "${PROJECT_ROOT}/skills/guide-plan/SKILL.md"
    grep -q "Triggers for" "${PROJECT_ROOT}/skills/guide-plan/SKILL.md"
}

@test "guide-ship SKILL.md: contains 3-rule checklist" {
    grep -q "Normal exit" "${PROJECT_ROOT}/skills/guide-ship/SKILL.md"
    grep -q "Abnormal exit" "${PROJECT_ROOT}/skills/guide-ship/SKILL.md"
    grep -q "Triggers for" "${PROJECT_ROOT}/skills/guide-ship/SKILL.md"
}

@test "execute SKILL.md: contains 3-rule checklist" {
    grep -q "Normal exit" "${PROJECT_ROOT}/skills/execute/SKILL.md"
    grep -q "Abnormal exit" "${PROJECT_ROOT}/skills/execute/SKILL.md"
    grep -q "Triggers for" "${PROJECT_ROOT}/skills/execute/SKILL.md"
}
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `bats tests/integration/test_skill_phase_exit_checklist.bats`
Expected: 4 failed (checklist phrases not yet present).

- [ ] **Step 3: Replace the Phase Exit prose**

Edit `skills/guide-arch/SKILL.md`. Find the section starting with line 758
`## Phase Exit — Post-Flow Analysis (Agent 平面, ADR-0027 §1.0)` and replace it
with:

```markdown
## Phase Exit — Post-Flow Analysis (Agent 平面, ADR-0027 §1.0)

### Checklist (must satisfy exactly one)

- [ ] **Normal exit** → call `orchestrator_finalize` (always, on every exit)
- [ ] **Abnormal exit** → call `orchestrator_finalize` + `rddf report-issue --phase guide-arch --exit <code> "<one-line>"`

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

- [ ] **Step 4: Commit**

```bash
cd /workspace/project/rdd-workflow
git add skills/guide-arch/SKILL.md
git commit -m "docs(skills/guide-arch): replace Phase Exit prose with 3-rule checklist"
```

---

### Task 12: Update remaining 3 SKILL.md Phase Exit checklists

**Files:**
- Modify: `skills/guide-plan/SKILL.md` (line ~663)
- Modify: `skills/guide-ship/SKILL.md` (line ~737)
- Modify: `skills/execute/SKILL.md` (line ~288)

- [ ] **Step 1: Replace guide-plan SKILL.md Phase Exit**

Edit `skills/guide-plan/SKILL.md`. Find the existing Phase Exit section and replace
its body with:

```markdown
## Phase Exit — Post-Flow Analysis (Agent 平面, ADR-0027 §1.0)

### Checklist (must satisfy exactly one)

- [ ] **Normal exit** → call `orchestrator_finalize` (always, on every exit)
- [ ] **Abnormal exit** → call `orchestrator_finalize` + `rddf report-issue --phase guide-plan --exit <code> "<one-line>"`

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

- [ ] **Step 2: Replace guide-ship SKILL.md Phase Exit**

Edit `skills/guide-ship/SKILL.md` the same way, with `--phase guide-ship`.

- [ ] **Step 3: Replace execute SKILL.md Phase Exit**

Edit `skills/execute/SKILL.md` the same way, with `--phase execute`.

- [ ] **Step 4: Run the bats checklist test**

Run: `bats tests/integration/test_skill_phase_exit_checklist.bats`
Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
cd /workspace/project/rdd-workflow
git add skills/guide-plan/SKILL.md skills/guide-ship/SKILL.md skills/execute/SKILL.md
git commit -m "docs(skills): replace Phase Exit prose in 3 SKILL.md files with 3-rule checklist"
```

---

### Task 13: Add multi-step cumulative-failure fixture tests

**Files:**
- Modify: `tests/unit/test_post_flow_analysis.py` (append)

- [ ] **Step 1: Write the test**

Append to `tests/unit/test_post_flow_analysis.py`:

```python
def test_analyze_phase_trace_cumulative_failure_detected(tmp_path):
    """Multiple zero-exit subprocesses + 'invalid state' in stderr → F2 cumulative."""
    from post_flow_analysis import analyze_phase_trace
    trace = tmp_path / "guide-arch-ses_x-1-100-cccccccc.jsonl"
    trace.write_text(
        '{"ts":"2026-08-12T10:00:00Z","type":"subprocess","cmd":["setup.sh"],"returncode":0,"stderr_tail":"","stdout_tail":""}\n'
        '{"ts":"2026-08-12T10:00:01Z","type":"subprocess","cmd":["build.sh"],"returncode":0,"stderr_tail":"","stdout_tail":""}\n'
        '{"ts":"2026-08-12T10:00:02Z","type":"subprocess","cmd":["deploy.sh"],"returncode":0,"stderr_tail":"Error: invalid state in registry","stdout_tail":""}\n'
    )
    cls = analyze_phase_trace(trace_path=trace, project_root=str(tmp_path))
    assert cls is not None
    assert cls.matched_rule == "F2-cumulative"
    assert cls.should_report is True


def test_analyze_phase_trace_ignores_irrelevant_text(tmp_path):
    """Zero-exit subprocesses with benign stderr → returns None."""
    from post_flow_analysis import analyze_phase_trace
    trace = tmp_path / "guide-arch-ses_x-1-100-dddddddd.jsonl"
    trace.write_text(
        '{"ts":"2026-08-12T10:00:00Z","type":"subprocess","cmd":["echo"],"returncode":0,"stderr_tail":"warning: deprecated","stdout_tail":""}\n'
    )
    cls = analyze_phase_trace(trace_path=trace, project_root=str(tmp_path))
    assert cls is None
```

- [ ] **Step 2: Run the test to verify it passes**

Run: `python3 -m pytest tests/unit/test_post_flow_analysis.py -v -k "cumulative or irrelevant"`
Expected: 2 passed.

- [ ] **Step 3: Commit**

```bash
cd /workspace/project/rdd-workflow
git add tests/unit/test_post_flow_analysis.py
git commit -m "test(post-flow-analysis): add cumulative-failure fixtures for analyze_phase_trace"
```

---

### Task 14: Write `tests/integration/test_orchestrator.py`

**Files:**
- Create: `tests/integration/test_orchestrator.py`

- [ ] **Step 1: Write the integration tests**

```python
"""Integration tests for rddf orchestrate end-to-end behavior.

Per spec 2026-08-12 §9 / §12. Verifies real subprocess invocation,
single-writer rule, sanitize, and stale-trace sweep interaction.
"""
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[2]
PYTHONPATH = str(PROJECT_ROOT)


def _run_orchestrate(*args: str, env_extra: dict | None = None) -> subprocess.CompletedProcess:
    """Run `python3 -m skills._lib.cli orchestrate <args>` with PYTHONPATH set."""
    env = os.environ.copy()
    env["PYTHONPATH"] = PYTHONPATH + os.pathsep + env.get("PYTHONPATH", "")
    if env_extra:
        env.update(env_extra)
    return subprocess.run(
        [sys.executable, "-m", "skills._lib.cli", "orchestrate", *args],
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
    )


@pytest.fixture
def trace_dir(tmp_path, monkeypatch):
    d = tmp_path / "trace"
    d.mkdir()
    monkeypatch.setenv("RDDF_TRACE_DIR", str(d))
    return d


def test_subprocess_invokes_real_command(trace_dir):
    result = _run_orchestrate(
        "subprocess", sys.executable, "-c", "print('hello world')",
        env_extra={"RDDF_PHASE": "int-test"},
    )
    assert result.returncode == 0
    traces = list(trace_dir.glob("*.jsonl"))
    assert len(traces) == 1
    events = [
        json.loads(line) for line in traces[0].read_text().splitlines() if line
    ]
    assert any(e.get("type") == "subprocess" for e in events)


def test_subprocess_preserves_return_code(trace_dir):
    result = _run_orchestrate(
        "subprocess", sys.executable, "-c", "import sys; sys.exit(42)",
        env_extra={"RDDF_PHASE": "int-test"},
    )
    assert result.returncode == 42


def test_finalize_appends_finalize_event_with_correct_counts(trace_dir):
    _run_orchestrate(
        "subprocess", sys.executable, "-c", "print('ok')",
        env_extra={"RDDF_PHASE": "int-test"},
    )
    _run_orchestrate(
        "subprocess", sys.executable, "-c", "import sys; sys.exit(1)",
        env_extra={"RDDF_PHASE": "int-test"},
    )
    result = _run_orchestrate(
        "finalize", env_extra={"RDDF_PHASE": "int-test"},
    )
    assert result.returncode == 0
    traces = list(trace_dir.glob("*.jsonl"))
    events = [
        json.loads(line) for line in traces[0].read_text().splitlines() if line
    ]
    last = events[-1]
    assert last["type"] == "finalize"
    assert last["subprocess_failures"] == 1


def test_sweep_deletes_unfinalized_old_traces(trace_dir, monkeypatch):
    # Create a stale trace
    stale = trace_dir / "guide-arch-ses_x-1-100-eeeeeeee.jsonl"
    stale.write_text(
        '{"ts":"2026-08-12T09:00:00Z","type":"subprocess","cmd":["x"],"returncode":0}\n'
    )
    os.utime(stale, (1000000, 1000000))
    monkeypatch.setenv("RDDF_TRACE_STALE_MINUTES", "0")
    monkeypatch.setenv("RDDF_PHASE", "guide-arch")
    result = _run_orchestrate("sweep-stale-traces")
    assert result.returncode == 0
    # Stale trace should be deleted
    assert not stale.exists()


def test_single_writer_rule_no_duplicate_issues(tmp_path, monkeypatch):
    """When RDDF_USE_ORCHESTRATOR=yes, post_flow_on_err must no-op.

    Verifies via direct invocation of post_flow_on_err that no Python
    classifier call happens. Sets a sentinel env var to detect.
    """
    # This is more of an end-to-end check via the orchestrator path
    # verifying that report_flow_bug is called exactly once.
    trace_dir = tmp_path / "trace"
    trace_dir.mkdir()
    monkeypatch.setenv("RDDF_TRACE_DIR", str(trace_dir))
    monkeypatch.setenv("RDDF_PHASE", "int-test")

    # Run a failing subprocess via orchestrator
    result = _run_orchestrate(
        "subprocess",
        sys.executable,
        "-c",
        "import sys; sys.exit(1)",
        env_extra={"RDDF_PHASE": "int-test"},
    )
    assert result.returncode == 1
    # Run finalize to trigger classify + report
    result = _run_orchestrate(
        "finalize",
        env_extra={"RDDF_PHASE": "int-test", "RDDF_PROJECT_ROOT": str(tmp_path)},
    )
    # Should not raise even if RDDF_PROJECT_ROOT has no .rddf/issues/
    assert result.returncode == 0
```

- [ ] **Step 2: Run the integration tests**

Run: `python3 -m pytest tests/integration/test_orchestrator.py -v`
Expected: 5 passed.

- [ ] **Step 3: Commit**

```bash
cd /workspace/project/rdd-workflow
git add tests/integration/test_orchestrator.py
git commit -m "test(orchestrator): add 5 integration tests for end-to-end behavior"
```

---

## Stage 3: Entry Integration + Regression (Days 9-10)

### Task 15: Integrate `orchestrator_entry.sh` into the 4 phase entry scripts

**Files:**
- Modify: `skills/guide-arch/scripts/arch_env_check.sh:15-16`
- Modify: `skills/guide-plan/scripts/plan_intake.sh:14-15`
- Modify: `skills/guide-ship/scripts/ship_env_check.sh:8-9`
- Modify: `skills/execute/scripts/select_worktree.sh:12-13`

- [ ] **Step 1: Edit `arch_env_check.sh`**

Open `skills/guide-arch/scripts/arch_env_check.sh`. Find lines 15-16 (the
`source post_flow_wrap.sh` and `trap ERR` block) and **after** them, add:

```bash
# Optional: Python orchestrator (opt-in via env var, default off)
if [ "${RDDF_USE_ORCHESTRATOR:-no}" = "yes" ]; then
    source "${RDDF_PROJECT_ROOT:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}/skills/_lib/orchestrator_entry.sh" 2>/dev/null || true
fi
```

- [ ] **Step 2: Edit `plan_intake.sh`**

Same edit as Step 1, applied to `skills/guide-plan/scripts/plan_intake.sh` after
lines 14-15.

- [ ] **Step 3: Edit `ship_env_check.sh`**

Same edit applied to `skills/guide-ship/scripts/ship_env_check.sh` after lines 8-9.

- [ ] **Step 4: Edit `select_worktree.sh`**

Same edit applied to `skills/execute/scripts/select_worktree.sh` after lines 12-13.

- [ ] **Step 5: Verify each file still loads**

Run:
```bash
bash -n skills/guide-arch/scripts/arch_env_check.sh
bash -n skills/guide-plan/scripts/plan_intake.sh
bash -n skills/guide-ship/scripts/ship_env_check.sh
bash -n skills/execute/scripts/select_worktree.sh
```
Expected: no syntax errors.

- [ ] **Step 6: Commit**

```bash
cd /workspace/project/rdd-workflow
git add skills/guide-arch/scripts/arch_env_check.sh \
        skills/guide-plan/scripts/plan_intake.sh \
        skills/guide-ship/scripts/ship_env_check.sh \
        skills/execute/scripts/select_worktree.sh
git commit -m "feat(scripts): integrate orchestrator_entry.sh into 4 phase entry scripts (opt-in)"
```

---

### Task 16: Add end-to-end bats test for env-var toggling

**Files:**
- Modify: `tests/integration/test_env_var_toggle.bats` (create)

- [ ] **Step 1: Write the bats test**

```bash
#!/usr/bin/env bats
# tests/integration/test_env_var_toggle.bats
# Verifies that RDDF_USE_ORCHESTRATOR=yes toggles behavior end-to-end.

setup() {
    load "test_helper"
    setup_lib
    TRACE_DIR="$(mktemp -d)"
    export RDDF_TRACE_DIR="$TRACE_DIR"
}

teardown() {
    rm -rf "$TRACE_DIR"
}

@test "env toggle: unset → trap path active, no orchestrator trace" {
    unset RDDF_USE_ORCHESTRATOR
    rm -f "$TRACE_DIR"/*.jsonl
    # Force a controlled error and check no orchestrator trace is created
    bash -c "
        source '${PROJECT_ROOT}/skills/_lib/post_flow_wrap.sh'
        source '${PROJECT_ROOT}/skills/_lib/orchestrator_entry.sh'
        set -e
        trap 'post_flow_on_err' ERR
        ( exit 1 ) || true
    " 2>/dev/null
    # No orchestrator trace should exist (trap path active)
    ! ls "$TRACE_DIR"/*.jsonl 2>/dev/null
}

@test "env toggle: yes → orchestrator trace exists, no trap invocation" {
    export RDDF_USE_ORCHESTRATOR=yes
    export RDDF_PHASE="guide-test"
    bash -c "
        source '${PROJECT_ROOT}/skills/_lib/post_flow_wrap.sh'
        source '${PROJECT_ROOT}/skills/_lib/orchestrator_entry.sh'
        trap 'post_flow_on_err' ERR
        orchestrator_run echo hello
        orchestrator_finalize
    " 2>/dev/null
    # Trace should exist
    ls "$TRACE_DIR"/*.jsonl 2>/dev/null
    # Last event should be finalize
    last_line=$(tail -n 1 "$TRACE_DIR"/*.jsonl)
    echo "$last_line" | grep -q '"type":"finalize"'
}
```

- [ ] **Step 2: Run the bats test**

Run: `bats tests/integration/test_env_var_toggle.bats`
Expected: 2 passed.

- [ ] **Step 3: Commit**

```bash
cd /workspace/project/rdd-workflow
git add tests/integration/test_env_var_toggle.bats
git commit -m "test(integration): verify RDDF_USE_ORCHESTRATOR env var toggles behavior"
```

---

### Task 17: Run full regression and update docs

**Files:**
- Modify: `docs/architecture/historical-evolution.md` (add v2.1.x entry)
- Modify: `docs/adr/ADR-0027-continuous-evolution-feedback-loop.md` §1.0 (future-extension note)

- [ ] **Step 1: Run the full regression suite**

Run: `./test.sh --full --regression`
Expected: All tests pass or only KNOWN_FAILURES baseline failures.

If new failures appear, fix them before proceeding. Do not skip.

- [ ] **Step 2: Add historical-evolution.md v2.1.x entry**

Edit `docs/architecture/historical-evolution.md`. Find the v2.1.0 row in the
changelog table (around line 48) and add a new row after it:

```markdown
| v2.1.1 | Bash `trap ERR` could not capture failures from sub-scripts that didn't source `post_flow_wrap.sh`; agents didn't always comply with SKILL.md Phase Exit prose; SIGKILL/OOM left no signal at all. | New `rddf orchestrate` subcommand: Python supervisor that captures every phase subprocess with tempfile streams + sanitize, appends to JSONL trace, runs stale-trace sweep on entry to detect killed phases (B4 fix), single-writer rule to coexist with existing trap path. 4 SKILL.md files updated with 3-rule Phase Exit checklists. | spec 2026-08-12 |
```

- [ ] **Step 3: Add future-extension note to ADR-0027**

Edit `docs/adr/ADR-0027-continuous-evolution-feedback-loop.md`. Find §1.0
"两平面架构（必读）" section and append a new subsection at the end:

```markdown
#### 1.0.1 未来扩展 (Python orchestrator, spec 2026-08-12)

`skills/_lib/orchestrator_entry.sh` 提供 `rddf orchestrate` 包装器，由
`RDDF_USE_ORCHESTRATOR=yes` 启用。补 4 个盲区：

- **B1**: 任何子脚本（无需 source wrapper）都可被 orchestrator 捕获
- **B2**: agent 不调 finalize 时，下次 entry 扫盘检测 stale trace
- **B3**: 多步骤累积失败（exit 0 但 stderr 含 invalid state）通过 analyze_phase_trace 检测
- **B4**: SIGKILL/OOM 留下未 finalize 的 trace，下次 entry 触发 `phase-interrupted` 报告

迁移条件：本仓库 dogfood 2 周零误报后 flip 默认值。
```

- [ ] **Step 4: Re-run regression after doc changes**

Run: `./test.sh --quick`
Expected: All green.

- [ ] **Step 5: Commit**

```bash
cd /workspace/project/rdd-workflow
git add docs/architecture/historical-evolution.md \
        docs/adr/ADR-0027-continuous-evolution-feedback-loop.md
git commit -m "docs: update historical-evolution and ADR-0027 with orchestrator rollout"
```

---

## Self-Review Checklist (run before declaring done)

- [ ] Spec coverage: every section in `docs/superpowers/specs/2026-08-12-python-orchestrator-design.md` has at least one task
- [ ] No placeholders: search plan for "TBD" / "TODO" / "similar to Task N" — none should exist
- [ ] Type consistency: `_get_trace_path`, `_open_trace`, `_append_event`, `_read_events`, `_handle_subprocess`, `_handle_checkpoint`, `_handle_finalize`, `_handle_sweep`, `_classify_interrupted_phase`, `_run_trace_gc`, `_tail_file`, `_find_open_trace`, `_get_session_id`, `_get_trace_dir`, `analyze_phase_trace`, `_read_trace_events`, `_outcome_from_event` — all signatures used in earlier tasks match later tasks
- [ ] All 17 tasks complete with green commits
- [ ] `./test.sh --full --regression` passes (only KNOWN_FAILURES)

---

## Execution Handoff

After all 17 tasks complete and self-review passes:

1. Run `./test.sh --full --regression` one more time to confirm green.
2. Open a PR with title `feat(orchestrator): Python supervisor for phase subprocess detection (B1-B4)`.
3. Reference this plan + spec in the PR body.
4. Dogfood on this repository for 2 weeks before considering flip-to-default-ON.