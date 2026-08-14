# preserve-orchestrator-command-stdout Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use skill_use("execute") to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `rddf orchestrate subprocess` pass child process stdout/stderr through to the caller's terminal by default (tee mode), with async reader subprocess copying output to trace file, and an env-var opt-out (`RDDF_ORCHESTRATOR_CAPTURE=tee|capture|passthrough`) for legacy dogfooding or zero-overhead escape hatches.

**Architecture:** Refactor `_handle_subprocess` in `_lib/cli/orchestrate_cmd.py` from synchronous PIPE capture (current `subprocess.run(stdout=tempfile)`) to a three-mode dispatch:

- **`tee` (default)**: `Popen(stdout=sys.stdout, stderr=sys.stderr)` for main subprocess (inherit → passthrough) + dedicated reader subprocess re-running same command with `PIPE` to drain into trace file. Reader is decoupled, dies safely.
- **`capture` (legacy)**: Original PIPE capture preserved (ADR-0027 §1.0.1 behavior). New `RDDF_ORCHESTRATOR_CAPTURE=capture` opt-in.
- **`passthrough` (escape hatch)**: Main subprocess inherits stdout/stderr (no PIPE), no reader subprocess spawned, no trace file written. Zero overhead.

`O_NONBLOCK` on reader subprocess's PIPE writes via `fcntl` prevents deadlock on 100MB+ output. File rotation at `RDDF_ORCHESTRATOR_TRACE_MAX_BYTES` (default 100MB) renames current to `<trace>.1`. Trace JSONL gains `stdout_capture_mode` field per subprocess event + `reader_died` boolean.

**Tech Stack:** Python 3.11+ (`subprocess.Popen`, `fcntl`, `os.set_blocking`), pytest 7.x (unit tests), bats 1.10+ (integration tests), bash (`orchestrator_entry.sh` env passthrough).

**OpenSpec change artifacts** (canonical): `openspec/changes/preserve-orchestrator-command-stdout/{proposal,design,tasks}.md` + `specs/orchestrator-output/spec.md` (4 ADDED Requirements: stdout-passthrough, async-tee, pipe-buffer-protection, capture-mode-env + stdout-mode-traceable + ci-compatibility).

---

## File Structure

### Production Code

| File | Responsibility |
|---|---|
| `_lib/cli/orchestrate_cmd.py` | MODIFY: add capture-mode dispatch, async reader subprocess, O_NONBLOCK, rotation, schema field |
| `skills/_lib/orchestrator_entry.sh` | MODIFY: passthrough env var to Python (`export RDDF_ORCHESTRATOR_CAPTURE` before `_orchestrator_py` call) |
| `tests/conftest.py` (if needed) | MODIFY: ensure `RDDF_TRACE_DIR` is per-test tmp |

### Tests

| File | Responsibility |
|---|---|
| `tests/unit/test_orchestrator_tee.py` | NEW: pytest unit tests for mode parsing, schema, rotation, reader_died detection |
| `tests/integration/test_orchestrator_stdout_passthrough.bats` | NEW: bats tests for real long-output (1MB / 100MB / O_NONBLOCK / passthrough) |

### Documentation

| File | Responsibility |
|---|---|
| `docs/architecture/extension-points.md` | MODIFY: append "Orchestrator 输出策略" section |
| `CHANGELOG.md` | MODIFY: add Unreleased entry for v2.1 |

---

## Pre-flight

- [ ] **Verify baseline tests pass before changes**

```bash
cd /workspace/project/rdd-workflow
bats tests/smoke.bats
pytest tests/unit/test_orchestrator_entry.py -q --tb=short 2>/dev/null || echo "no py test, OK"
```

- [ ] **Locate _handle_subprocess implementation**

```bash
grep -n "_handle_subprocess\|stdout=stdout_tmp\|stderr=stderr_tmp" _lib/cli/orchestrate_cmd.py | head -10
```

- [ ] **Confirm fcntl is available on Linux/macOS (POSIX)**

```bash
python3 -c "import fcntl, os; print('fcntl OK')"
```

---

### Task 1: Capture mode plumbing (env var parsing)

**Files:** `_lib/cli/orchestrate_cmd.py`, `tests/unit/test_orchestrator_tee.py`

- [ ] **Step 1.1: Write failing unit test** — env-var parsing

In `tests/unit/test_orchestrator_tee.py` (NEW file):

```python
"""Unit tests for orchestrator stdout capture mode (tee/capture/passthrough).

Per openspec/changes/preserve-orchestrator-command-stdout.
"""
from __future__ import annotations

import pytest
from _lib.cli.orchestrate_cmd import _resolve_capture_mode


@pytest.mark.parametrize(
    "env_value,expected",
    [
        ("tee", "tee"),
        ("capture", "capture"),
        ("passthrough", "passthrough"),
        ("", "tee"),  # default = tee
        ("garbage", "tee"),  # invalid → default tee
    ],
)
def test_resolve_capture_mode(env_value: str, expected: str, monkeypatch: pytest.MonkeyPatch) -> None:
    if env_value:
        monkeypatch.setenv("RDDF_ORCHESTRATOR_CAPTURE", env_value)
    else:
        monkeypatch.delenv("RDDF_ORCHESTRATOR_CAPTURE", raising=False)
    assert _resolve_capture_mode() == expected
```

- [ ] **Step 1.2: Verify test fails**

```bash
cd /workspace/project/rdd-workflow
pytest tests/unit/test_orchestrator_tee.py::test_resolve_capture_mode -v
```
Expected: `ImportError: cannot import name '_resolve_capture_mode'`.

- [ ] **Step 1.3: Implement `_resolve_capture_mode`**

In `_lib/cli/orchestrate_cmd.py`, add near top (after imports):

```python
def _resolve_capture_mode() -> str:
    """Read RDDF_ORCHESTRATOR_CAPTURE env var. Returns one of tee|capture|passthrough.

    Default: tee. Invalid values fall back to tee (safe).
    """
    raw = os.environ.get("RDDF_ORCHESTRATOR_CAPTURE", "").strip().lower()
    if raw in ("tee", "capture", "passthrough"):
        return raw
    return "tee"
```

- [ ] **Step 1.4: Verify test passes**

```bash
pytest tests/unit/test_orchestrator_tee.py::test_resolve_capture_mode -v
```
Expected: 5 tests pass.

- [ ] **Step 1.5: Defer commit** (per `COMMIT_IN_EXECUTE` default — worktree aggregate commit at archive time)

---

### Task 2: tee mode — async reader subprocess + stdout passthrough

**Files:** `_lib/cli/orchestrate_cmd.py`, `tests/unit/test_orchestrator_tee.py`

- [ ] **Step 2.1: Write failing unit test** — `_run_tee_mode` emits subprocess event with `stdout_capture_mode: "tee"` and `reader_died: false`

Append to `tests/unit/test_orchestrator_tee.py`:

```python
import json
import subprocess
import sys
from pathlib import Path


def _run_orchestrate_subprocess(args: list[str], env_extra: dict) -> subprocess.CompletedProcess:
    """Helper: invoke orchestrate_cmd subprocess action via subprocess.run."""
    repo_root = Path(__file__).resolve().parents[1]
    env = {
        "PYTHONPATH": f"{repo_root}:{repo_root}/_lib",
        "RDDF_PROJECT_ROOT": str(repo_root),
        "RDDF_PHASE": "unit-test-tee",
    }
    env.update(env_extra)
    return subprocess.run(
        [sys.executable, str(repo_root / "_lib" / "cli" / "orchestrate_cmd.py"),
         "subprocess", *args],
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
    )


def test_tee_mode_emits_capture_mode_field(tmp_path: Path) -> None:
    """tee mode records stdout_capture_mode='tee' and inherits caller stdout."""
    trace_dir = tmp_path / "trace"
    result = _run_orchestrate_subprocess(
        ["bash", "-c", 'echo "hello from tee"'],
        env_extra={
            "RDDF_TRACE_DIR": str(trace_dir),
            "RDDF_ORCHESTRATOR_CAPTURE": "tee",
        },
    )
    assert result.returncode == 0, result.stderr
    jsonl_files = list(trace_dir.glob("*.jsonl"))
    assert len(jsonl_files) == 1, f"expected 1 trace, got {len(jsonl_files)}"
    events = [json.loads(line) for line in jsonl_files[0].read_text().splitlines() if line]
    subprocess_events = [e for e in events if e.get("type") == "subprocess"]
    assert len(subprocess_events) == 1
    assert subprocess_events[0]["stdout_capture_mode"] == "tee"
    assert subprocess_events[0]["reader_died"] is False
```

- [ ] **Step 2.2: Verify test fails**

```bash
cd /workspace/project/rdd-workflow
pytest tests/unit/test_orchestrator_tee.py::test_tee_mode_emits_capture_mode_field -v
```
Expected: AssertionError on `stdout_capture_mode` key.

- [ ] **Step 2.3: Refactor `_handle_subprocess` to dispatch by capture mode**

Replace `_handle_subprocess` body in `_lib/cli/orchestrate_cmd.py` with mode-aware dispatch:

```python
def _handle_subprocess(
    cmd: list[str],
    trace_dir: Path,
    timeout: Optional[int] = None,
) -> int:
    """Run a subprocess and record its result.

    Dispatch based on RDDF_ORCHESTRATOR_CAPTURE:
      - tee (default): main inherits stdout/stderr; reader subprocess drains
        same command into trace file. Reader failure is non-fatal.
      - capture: legacy PIPE capture (ADR-0027 §1.0.1).
      - passthrough: main inherits stdout/stderr; no reader; no trace write.

    Returns the subprocess return code (timeout → 124).
    """
    if timeout is None:
        timeout = int(os.environ.get("RDDF_ORCHESTRATE_TIMEOUT", "600"))

    _handle_sweep(trace_dir)
    phase = os.environ.get("RDDF_PHASE", "unknown")
    capture_mode = _resolve_capture_mode()

    if capture_mode == "passthrough":
        return _run_passthrough(cmd, timeout)
    if capture_mode == "capture":
        return _run_legacy_capture(cmd, phase, trace_dir, timeout)
    return _run_tee_mode(cmd, phase, trace_dir, timeout)
```

Add three new functions below the existing helpers (replace the old `_handle_subprocess` body content with calls to these):

```python
def _run_passthrough(cmd: list[str], timeout: int) -> int:
    """passthrough mode: inherit stdout/stderr, no reader, no trace write."""
    try:
        proc = subprocess.run(
            cmd,
            shell=False,
            stdout=None,
            stderr=None,
            timeout=timeout,
        )
        return proc.returncode
    except subprocess.TimeoutExpired:
        return 124


def _run_legacy_capture(cmd: list[str], phase: str, trace_dir: Path, timeout: int) -> int:
    """capture mode: original PIPE capture (move old _handle_subprocess body here)."""
    from skills._lib.loop.sanitizer import sanitize

    trace = _open_trace(phase=phase)
    rc = 124
    stdout_tail = ""
    stderr_tail = ""
    duration_ms = 0
    timed_out = False

    stdout_tmp = tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".out", encoding="utf-8")
    stderr_tmp = tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".err", encoding="utf-8")
    started = time.monotonic()
    try:
        proc = subprocess.run(
            cmd, shell=False, stdout=stdout_tmp, stderr=stderr_tmp, timeout=timeout,
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
        try:
            stdout_tail = sanitize(stdout_tail).sanitized_text
        except Exception as e:
            print(f"warning: sanitizer failed on stdout: {e}", file=sys.stderr)
            stdout_tail = stdout_tail[:4096]
        try:
            stderr_tail = sanitize(stderr_tail).sanitized_text
        except Exception as e:
            print(f"warning: sanitizer failed on stderr: {e}", file=sys.stderr)
            stderr_tail = stderr_tail[:4096]
    finally:
        os.unlink(stdout_tmp.name)
        os.unlink(stderr_tmp.name)

    _append_event(trace, {
        "type": "subprocess",
        "cmd": cmd,
        "returncode": rc,
        "stdout_tail": stdout_tail,
        "stderr_tail": stderr_tail,
        "duration_ms": duration_ms,
        "timeout": timed_out,
        "stdout_capture_mode": "capture",
        "reader_died": False,
    })
    trace.close()
    return rc


def _run_tee_mode(cmd: list[str], phase: str, trace_dir: Path, timeout: int) -> int:
    """tee mode: main inherits stdout/stderr; reader subprocess drains to trace."""
    trace = _open_trace(phase=phase)
    reader_died = False
    started = time.monotonic()
    rc = 124
    timed_out = False

    main_proc: Optional[subprocess.Popen] = None
    reader_proc: Optional[subprocess.Popen] = None
    try:
        main_proc = subprocess.Popen(
            cmd, shell=False,
            stdout=sys.stdout, stderr=sys.stderr,
        )
        # Spawn reader: same command, PIPE → trace file. Decoupled lifecycle.
        reader_proc = _spawn_reader(cmd, trace_dir, phase, timeout)
        rc = main_proc.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        timed_out = True
        rc = 124
        if main_proc is not None and main_proc.poll() is None:
            main_proc.kill()
            main_proc.wait()
    finally:
        # Drain reader subprocess non-blockingly; capture exit or crash
        if reader_proc is not None:
            try:
                reader_proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                reader_proc.kill()
                reader_died = True
            if reader_proc.returncode not in (0, None):
                # Reader died before draining fully → mark as failure but continue
                reader_died = True

    duration_ms = int((time.monotonic() - started) * 1000)
    stdout_tail = ""  # tee mode: caller sees it live; no tail needed
    stderr_tail = ""
    _append_event(trace, {
        "type": "subprocess",
        "cmd": cmd,
        "returncode": rc,
        "stdout_tail": stdout_tail,
        "stderr_tail": stderr_tail,
        "duration_ms": duration_ms,
        "timeout": timed_out,
        "stdout_capture_mode": "tee",
        "reader_died": reader_died,
    })
    trace.close()
    return rc


def _spawn_reader(cmd: list[str], trace_dir: Path, phase: str, timeout: int) -> subprocess.Popen:
    """Spawn reader subprocess that drains cmd stdout/stderr into trace JSONL.

    Uses _open_trace to append to the same trace as main flow.
    Sets O_NONBLOCK on its stdout/stderr pipes to prevent buffer deadlock
    on large output (Linux/macOS; Windows falls back to default).
    """
    import fcntl

    trace = _open_trace(phase=phase)
    proc = subprocess.Popen(
        cmd, shell=False,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )
    # Make PIPE non-blocking on POSIX
    try:
        if proc.stdout is not None:
            fd = proc.stdout.fileno()
            flags = fcntl.fcntl(fd, fcntl.F_GETFL)
            fcntl.fcntl(fd, fcntl.F_SETFL, flags | os.O_NONBLOCK)
        if proc.stderr is not None:
            fd = proc.stderr.fileno()
            flags = fcntl.fcntl(fd, fcntl.F_GETFL)
            fcntl.fcntl(fd, fcntl.F_SETFL, flags | os.O_NONBLOCK)
    except (OSError, AttributeError):
        pass  # Windows: O_NONBLOCK not supported on pipes; tolerate

    # Reader's stdout/stderr streams are drained into the trace events
    # (via separate _append_event per drained line; implementation in Task 4).
    return proc
```

- [ ] **Step 2.4: Verify test passes**

```bash
cd /workspace/project/rdd-workflow
pytest tests/unit/test_orchestrator_tee.py::test_tee_mode_emits_capture_mode_field -v
```
Expected: 1 pass.

- [ ] **Step 2.5: Defer commit** (worktree aggregate commit at archive time)

---

### Task 3: passthrough mode — zero overhead escape hatch

**Files:** `tests/unit/test_orchestrator_tee.py`

- [ ] **Step 3.1: Write failing unit test** — passthrough mode writes NO trace file

Append to `tests/unit/test_orchestrator_tee.py`:

```python
def test_passthrough_mode_no_trace_written(tmp_path: Path) -> None:
    """passthrough mode skips trace file creation entirely."""
    trace_dir = tmp_path / "trace"
    result = _run_orchestrate_subprocess(
        ["bash", "-c", 'echo "hi"'],
        env_extra={
            "RDDF_TRACE_DIR": str(trace_dir),
            "RDDF_ORCHESTRATOR_CAPTURE": "passthrough",
        },
    )
    assert result.returncode == 0, result.stderr
    # Zero trace files expected
    assert list(trace_dir.glob("*.jsonl")) == []
```

- [ ] **Step 3.2: Verify test fails**

```bash
pytest tests/unit/test_orchestrator_tee.py::test_passthrough_mode_no_trace_written -v
```
Expected: AssertionError on trace files count (currently `_handle_subprocess` always opens trace).

- [ ] **Step 3.3: Verify implementation already correct**

`_run_passthrough` from Task 2.3 already returns early without `_open_trace`. No further code change needed.

- [ ] **Step 3.4: Verify test passes**

```bash
pytest tests/unit/test_orchestrator_tee.py::test_passthrough_mode_no_trace_written -v
```
Expected: 1 pass.

- [ ] **Step 3.5: Defer commit**

---

### Task 4: capture mode (legacy) preserves old behavior

**Files:** `tests/unit/test_orchestrator_tee.py`

- [ ] **Step 4.1: Write failing unit test** — capture mode records `stdout_capture_mode: "capture"` and stdout_tail populated

Append:

```python
def test_capture_mode_legacy_behavior(tmp_path: Path) -> None:
    """capture mode preserves ADR-0027 §1.0.1 PIPE capture (stdout_tail populated)."""
    trace_dir = tmp_path / "trace"
    result = _run_orchestrate_subprocess(
        ["bash", "-c", 'echo "captured line"'],
        env_extra={
            "RDDF_TRACE_DIR": str(trace_dir),
            "RDDF_ORCHESTRATOR_CAPTURE": "capture",
        },
    )
    assert result.returncode == 0
    jsonl_files = list(trace_dir.glob("*.jsonl"))
    assert len(jsonl_files) == 1
    events = [json.loads(line) for line in jsonl_files[0].read_text().splitlines() if line]
    subprocess_events = [e for e in events if e.get("type") == "subprocess"]
    assert subprocess_events[0]["stdout_capture_mode"] == "capture"
    assert "captured line" in subprocess_events[0]["stdout_tail"]
```

- [ ] **Step 4.2: Verify test fails**

```bash
pytest tests/unit/test_orchestrator_tee.py::test_capture_mode_legacy_behavior -v
```
Expected: AssertionError on `stdout_capture_mode` field.

- [ ] **Step 4.3: Verify implementation already correct**

`_run_legacy_capture` from Task 2.3 already sets the field. No code change.

- [ ] **Step 4.4: Verify test passes**

```bash
pytest tests/unit/test_orchestrator_tee.py::test_capture_mode_legacy_behavior -v
```
Expected: 1 pass.

- [ ] **Step 4.5: Defer commit**

---

### Task 5: Reader subprocess drain loop (background)

**Files:** `_lib/cli/orchestrate_cmd.py`

- [ ] **Step 5.1: Implement background drain loop in `_spawn_reader`**

Update `_spawn_reader` to spawn a background thread that reads reader_proc's stdout/stderr in chunks and calls `_append_event` for each event (or accumulates into a sink file). Use `selectors` for non-blocking reads on POSIX:

Replace `_spawn_reader` with:

```python
def _spawn_reader(cmd: list[str], trace_dir: Path, phase: str, timeout: int) -> subprocess.Popen:
    """Spawn reader subprocess + background drain thread.

    Drains stdout/stderr into the trace JSONL via _append_event.
    O_NONBLOCK on pipes (POSIX) prevents buffer deadlock on large output.
    Reader thread crashes → trace records `reader_died: true`.
    """
    import fcntl
    import threading

    trace = _open_trace(phase=phase)
    proc = subprocess.Popen(
        cmd, shell=False,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )
    # Set O_NONBLOCK on POSIX pipes
    try:
        for pipe in (proc.stdout, proc.stderr):
            if pipe is None:
                continue
            fd = pipe.fileno()
            flags = fcntl.fcntl(fd, fcntl.F_GETFL)
            fcntl.fcntl(fd, fcntl.F_SETFL, flags | os.O_NONBLOCK)
    except (OSError, AttributeError):
        pass  # Windows: tolerate

    def _drain(stream: Optional[IO[bytes]], label: str) -> None:
        """Read pipe chunks until EOF; append each line as a trace event."""
        if stream is None:
            return
        while True:
            try:
                chunk = stream.readline()
            except (OSError, ValueError):
                return  # pipe closed or non-blocking EAGAIN after close
            if not chunk:
                return
            try:
                _append_event(trace, {
                    "type": "reader_chunk",
                    "stream": label,
                    "data": chunk.decode("utf-8", errors="replace").rstrip("\n"),
                })
            except Exception:
                return  # trace write failed; reader thread dies silently

    t_out = threading.Thread(target=_drain, args=(proc.stdout, "stdout"), daemon=True)
    t_err = threading.Thread(target=_drain, args=(proc.stderr, "stderr"), daemon=True)
    t_out.start()
    t_err.start()
    # Stash threads on proc for later join in _run_tee_mode
    proc._reader_threads = (t_out, t_err)  # type: ignore[attr-defined]
    return proc
```

Update `_run_tee_mode`'s `finally` block to join reader threads (with timeout):

```python
finally:
    if reader_proc is not None:
        # Give reader threads up to 5s to finish
        threads = getattr(reader_proc, "_reader_threads", None)
        if threads:
            for t in threads:
                t.join(timeout=5)
        try:
            reader_proc.wait(timeout=2)
        except subprocess.TimeoutExpired:
            reader_proc.kill()
            reader_died = True
        if reader_proc.returncode not in (0, None):
            reader_died = True
```

- [ ] **Step 5.2: Run all unit tests**

```bash
cd /workspace/project/rdd-workflow
pytest tests/unit/test_orchestrator_tee.py -v
```
Expected: All 5 unit tests pass.

- [ ] **Step 5.3: Defer commit**

---

### Task 6: Trace file rotation + reader_died detection

**Files:** `_lib/cli/orchestrate_cmd.py`, `tests/unit/test_orchestrator_tee.py`

- [ ] **Step 6.1: Write failing unit test** — trace JSONL rotation at threshold

Append:

```python
def test_trace_file_rotation(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """When trace file exceeds RDDF_ORCHESTRATOR_TRACE_MAX_BYTES, rotate to .1."""
    trace_dir = tmp_path / "trace"
    trace_dir.mkdir()
    # Pre-create a trace file at 80 bytes, set threshold to 100
    large_content = "x" * 80
    (trace_dir / "unit-test-rotate-sess1-1234-1-aaaaaaaa.jsonl").write_text(large_content)
    monkeypatch.setenv("RDDF_ORCHESTRATOR_TRACE_MAX_BYTES", "100")
    monkeypatch.setenv("RDDF_TRACE_DIR", str(trace_dir))
    # Run a small subprocess — should trigger rotation check
    _run_orchestrate_subprocess(
        ["bash", "-c", "echo hi"],
        env_extra={"RDDF_ORCHESTRATOR_TRACE_MAX_BYTES": "100", "RDDF_TRACE_DIR": str(trace_dir)},
    )
    # The 80-byte file should have been rotated to .1
    rotated = list(trace_dir.glob("*.1"))
    assert len(rotated) >= 1
```

- [ ] **Step 6.2: Verify test fails**

```bash
pytest tests/unit/test_orchestrator_tee.py::test_trace_file_rotation -v
```
Expected: AssertionError (no `.1` files).

- [ ] **Step 6.3: Implement `_rotate_if_needed` and hook into `_open_trace`**

Add to `_lib/cli/orchestrate_cmd.py`:

```python
def _rotate_if_needed(trace_dir: Path, phase: str) -> None:
    """Rotate the largest trace file for `phase` if it exceeds RDDF_ORCHESTRATOR_TRACE_MAX_BYTES.

    Renames `<trace>.jsonl` → `<trace>.jsonl.1`. New runs start fresh.
    Default threshold: 100 MB. Configurable via env var.
    """
    threshold = int(os.environ.get("RDDF_ORCHESTRATOR_TRACE_MAX_BYTES", str(100 * 1024 * 1024)))
    candidates = sorted(
        trace_dir.glob(f"{phase}-*.jsonl"),
        key=lambda p: p.stat().st_size,
        reverse=True,
    )
    for candidate in candidates:
        if candidate.stat().st_size >= threshold:
            rotated = candidate.with_suffix(candidate.suffix + ".1")
            try:
                candidate.rename(rotated)
            except OSError as e:
                print(f"warning: trace rotation failed: {e}", file=sys.stderr)
            return  # one rotation per open is enough
```

Call `_rotate_if_needed(trace_dir, phase)` at top of `_open_trace`, after `trace_dir.mkdir`:

```python
def _open_trace(phase: str, session_id: Optional[str] = None) -> Trace:
    sid = session_id or _get_session_id()
    trace_dir = _get_trace_dir()
    trace_dir.mkdir(parents=True, exist_ok=True)
    _rotate_if_needed(trace_dir, phase)
    # ... (rest unchanged)
```

- [ ] **Step 6.4: Verify test passes**

```bash
pytest tests/unit/test_orchestrator_tee.py::test_trace_file_rotation -v
```
Expected: 1 pass.

- [ ] **Step 6.5: Defer commit**

---

### Task 7: orchestrator_entry.sh env passthrough

**Files:** `skills/_lib/orchestrator_entry.sh`

- [ ] **Step 7.1: Verify env passthrough already happens**

The current `_orchestrator_py` uses `subprocess.run` (via `subprocess` module in Python) which inherits env from parent. Setting `RDDF_ORCHESTRATOR_CAPTURE` in caller env reaches `_resolve_capture_mode` automatically.

**Confirm**:
```bash
cd /workspace/project/rdd-workflow
RDDF_ORCHESTRATOR_CAPTURE=passthrough bash -c '
    source skills/_lib/orchestrator_entry.sh
    RDDF_TRACE_DIR=/tmp/_verify_trace mkdir -p /tmp/_verify_trace
    orchestrator_run bash -c "echo from-passthrough"
'
ls /tmp/_verify_trace/*.jsonl 2>/dev/null && echo "❌ trace file written" || echo "✅ no trace (passthrough OK)"
rm -rf /tmp/_verify_trace
```
Expected: `✅ no trace (passthrough OK)`.

- [ ] **Step 7.2: No code change required; defer commit**

If verification fails, modify `_orchestrator_py` to explicitly pass `RDDF_ORCHESTRATOR_CAPTURE`:

```python
def _orchestrator_py():
    ...
    PYTHONPATH="${_ORCHESTRATOR_DIR}:${_skills_root}:${PYTHONPATH}" \
    RDDF_PROJECT_ROOT="$_proj_root" \
    RDDF_PHASE="${RDDF_PHASE:-unknown}" \
    RDDF_ORCHESTRATOR_CAPTURE="${RDDF_ORCHESTRATOR_CAPTURE:-}" \
        python3 "$(_orchestrate_script)" "$@"
```

---

### Task 8: Integration tests — real long output scenarios

**Files:** `tests/integration/test_orchestrator_stdout_passthrough.bats`

- [ ] **Step 8.1: Write failing bats test** — 1MB output in tee mode does not block subprocess

Create `tests/integration/test_orchestrator_stdout_passthrough.bats`:

```bash
#!/usr/bin/env bats
# Integration tests for orchestrator stdout passthrough (tee mode).
# Per openspec/changes/preserve-orchestrator-command-stdout.

setup() {
    REPO_ROOT="$(cd "${BATS_TEST_DIRNAME}/../.." && pwd)"
    WORK="$(mktemp -d)"
    export RDDF_TRACE_DIR="$WORK/.rddf/state/trace"
    export RDDF_PHASE="int-tee"
    mkdir -p "$RDDF_TRACE_DIR"
}

teardown() {
    rm -rf "$WORK"
    unset RDDF_TRACE_DIR RDDF_PHASE
}

@test "T1: tee mode 1MB output does not block subprocess" {
    RDDF_ORCHESTRATOR_CAPTURE=tee bash -c '
        source "$1/skills/_lib/orchestrator_entry.sh" 2>/dev/null
        orchestrator_run bash -c "
            for i in $(seq 100000); do echo \"line \$i\"; done
        "
        orchestrator_finalize
    ' _ "$REPO_ROOT"
    trace_files=$(ls "$RDDF_TRACE_DIR"/*.jsonl 2>/dev/null | wc -l)
    [ "$trace_files" -ge 1 ]
}

@test "T2: passthrough mode produces no trace file" {
    RDDF_ORCHESTRATOR_CAPTURE=passthrough bash -c '
        source "$1/skills/_lib/orchestrator_entry.sh" 2>/dev/null
        orchestrator_run bash -c "echo hi"
        orchestrator_finalize
    ' _ "$REPO_ROOT"
    count=$(ls "$RDDF_TRACE_DIR"/*.jsonl 2>/dev/null | wc -l)
    [ "$count" -eq 0 ]
}

@test "T3: capture mode preserves stdout_tail in trace" {
    RDDF_ORCHESTRATOR_CAPTURE=capture bash -c '
        source "$1/skills/_lib/orchestrator_entry.sh" 2>/dev/null
        orchestrator_run bash -c "echo preserved-capture-line"
        orchestrator_finalize
    ' _ "$REPO_ROOT"
    trace=$(ls "$RDDF_TRACE_DIR"/*.jsonl 2>/dev/null | head -1)
    [ -n "$trace" ]
    grep -q "preserved-capture-line" "$trace"
}

@test "T4: CI=true runs without trace corruption" {
    CI=true bash -c '
        source "$1/skills/_lib/orchestrator_entry.sh" 2>/dev/null
        orchestrator_run bash -c "echo ci-line"
        orchestrator_finalize
    ' _ "$REPO_ROOT"
    trace=$(ls "$RDDF_TRACE_DIR"/*.jsonl 2>/dev/null | head -1)
    [ -n "$trace" ]
    grep -q "ci-line" "$trace"
}

@test "T5: stdout_capture_mode field present in subprocess event" {
    RDDF_ORCHESTRATOR_CAPTURE=tee bash -c '
        source "$1/skills/_lib/orchestrator_entry.sh" 2>/dev/null
        orchestrator_run bash -c "echo mode-check"
        orchestrator_finalize
    ' _ "$REPO_ROOT"
    trace=$(ls "$RDDF_TRACE_DIR"/*.jsonl 2>/dev/null | head -1)
    grep -q '"stdout_capture_mode":"tee"' "$trace"
}
```

- [ ] **Step 8.2: Verify tests fail (or pass after Task 5+6)**

```bash
cd /workspace/project/rdd-workflow
bats tests/integration/test_orchestrator_stdout_passthrough.bats
```
Expected: All 5 tests pass.

- [ ] **Step 8.3: Defer commit**

---

### Task 9: Documentation update

**Files:** `docs/architecture/extension-points.md`, `CHANGELOG.md`

- [ ] **Step 9.1: Append "Orchestrator 输出策略" section to extension-points.md**

Find the section boundary:
```bash
grep -n "^## " docs/architecture/extension-points.md | tail -5
```

Append new section at end:

```markdown

## Orchestrator 输出策略

`rddf orchestrate subprocess` 通过 `RDDF_ORCHESTRATOR_CAPTURE` env var 控制 stdout/stderr 处理模式。三种模式：

| 模式 | 调用方实时输出 | trace 文件 | 使用场景 |
|------|---------------|-----------|---------|
| `tee` (默认) | ✅ 透传 | ✅ 异步 tee | 正常 phase 运行 |
| `capture` | ❌ 隐藏 | ✅ 同步捕获 | 旧 dogfooding 报告 |
| `passthrough` | ✅ 透传 | ❌ 无 trace | 零开销逃生口 |

**tee 模式实现**：主 subprocess 通过 `Popen(stdout=sys.stdout, stderr=sys.stderr)` 继承父进程输出；同时启动专用 reader subprocess 重跑同一命令并用 `stdout=PIPE` 异步读取到 trace 文件。Reader 进程崩溃时主流程不受影响，trace 标记 `reader_died: true`。

**O_NONBLOCK 保护**：reader subprocess 的 PIPE 文件描述符通过 `fcntl.F_SETFL | O_NONBLOCK` 设置为非阻塞模式，防止子进程输出过快导致 PIPE buffer 溢出（100MB+ 场景）。

**trace 字段**：subprocess 事件新增 `stdout_capture_mode: tee|capture|passthrough` 与 `reader_died: bool` 字段，事后审计可见。

**env var 切换**：
```bash
# 默认 tee
rddf orchestrate subprocess bash -c 'echo hi'

# 强制旧 capture 模式
RDDF_ORCHESTRATOR_CAPTURE=capture rddf orchestrate subprocess bash -c 'echo hi'

# 零开销逃生口
RDDF_ORCHESTRATOR_CAPTURE=passthrough rddf orchestrate subprocess bash -c 'echo hi'
```

**trace 文件 rotate**：超过 `RDDF_ORCHESTRATOR_TRACE_MAX_BYTES`（默认 100MB）时，当前文件重命名为 `<trace>.1`，新 trace 文件从空开始。Windows 不支持 O_NONBLOCK，tee 模式在 Windows 上行为降级（可接受）。
```

- [ ] **Step 9.2: Add Unreleased entry to CHANGELOG.md**

```bash
head -20 CHANGELOG.md  # locate Unreleased section
```

Append under `## [Unreleased]` (or create if missing):

```markdown

### Orchestrator stdout passthrough (`preserve-orchestrator-command-stdout`)

- **Default mode**: `tee` (was `capture`). Users now see live stdout from `rddf orchestrate subprocess` calls.
- **Env var**: `RDDF_ORCHESTRATOR_CAPTURE` accepts `tee` (default) | `capture` (legacy) | `passthrough` (zero-overhead).
- **Async reader**: New reader subprocess drains stdout/stderr to trace file via dedicated process with `O_NONBLOCK` pipes (POSIX).
- **Schema**: trace JSONL subprocess events gain `stdout_capture_mode` and `reader_died` fields.
- **Rotation**: trace file rotates to `<trace>.1` when exceeding `RDDF_ORCHESTRATOR_TRACE_MAX_BYTES` (default 100MB).
- **CI compat**: GitHub Actions runner output now visible (was swallowed by old capture).
- **Windows caveat**: O_NONBLOCK not supported on Windows pipes; tee mode degrades to default buffer.
```

- [ ] **Step 9.3: Defer commit**

---

### Task 10: Manual benchmark + full regression

**Files:** N/A (verification only)

- [ ] **Step 10.1: Manual benchmark — 10MB output overhead vs capture baseline**

```bash
cd /workspace/project/rdd-workflow

# Baseline: capture mode timing
time RDDF_ORCHESTRATOR_CAPTURE=capture bash -c '
    source skills/_lib/orchestrator_entry.sh
    orchestrator_run bash -c "for i in $(seq 1000000); do echo \"x\"; done"
' 2>&1 | tail -3

# New: tee mode timing
time RDDF_ORCHESTRATOR_CAPTURE=tee bash -c '
    source skills/_lib/orchestrator_entry.sh
    orchestrator_run bash -c "for i in $(seq 1000000); do echo \"x\"; done"
' 2>&1 | tail -3

# Expected: tee mode overhead ≤5% of capture mode time
```

Record results in change comment: `tee vs capture overhead: <X>% (target ≤5%)`

- [ ] **Step 10.2: Full regression test**

```bash
cd /workspace/project/rdd-workflow
./test.sh --full --regression
```
Expected: All green or only KNOWN_FAILURES.txt entries.

If new failures appear, fix before commit (per AGENTS.md archive gate rule).

- [ ] **Step 10.3: Manual acceptance: live stdout visible**

```bash
cd /workspace/project/rdd-workflow
RDDF_ORCHESTRATOR_CAPTURE=tee bash -c '
    source skills/_lib/orchestrator_entry.sh
    orchestrator_run bash -c "for i in 1 2 3; do echo \"real-time-line-\$i\"; sleep 0.5; done"
'
```
Expected: 3 lines appear in terminal **as** the subprocess produces them (not buffered until end).

- [ ] **Step 10.4: Manual acceptance: passthrough writes no trace**

```bash
cd /workspace/project/rdd-workflow
TRACE_TEST=/tmp/_tee_passthrough_verify
rm -rf "$TRACE_TEST" && mkdir -p "$TRACE_TEST"
RDDF_TRACE_DIR="$TRACE_TEST" RDDF_ORCHESTRATOR_CAPTURE=passthrough bash -c '
    source skills/_lib/orchestrator_entry.sh
    orchestrator_run bash -c "echo passthrough-test"
'
[ -z "$(ls "$TRACE_TEST"/*.jsonl 2>/dev/null)" ] && echo "✅ passthrough: no trace file" || echo "❌ trace file leaked"
rm -rf "$TRACE_TEST"
```
Expected: `✅ passthrough: no trace file`.

- [ ] **Step 10.5: Defer commit** (worktree aggregate commit at archive time)

---

## Self-review checklist (before archive)

- [ ] **Spec coverage**: Walk through `specs/orchestrator-output/spec.md` 4 ADDED Requirements:
  - orchestrator-subprocess-stdout-passthrough → Task 2 + Task 5
  - orchestrator-async-tee-to-trace → Task 5
  - orchestrator-pipe-buffer-protection → Task 5 (`O_NONBLOCK` in `_spawn_reader`)
  - orchestrator-stdout-capture-mode-env → Task 1 + Task 7
  - orchestrator-stdout-mode-traceable → Task 2 schema field
  - orchestrator-ci-compatibility → Task 8 T4
- [ ] **No placeholders**: grep for "TBD|TODO|fill in|implement later" — none expected.
- [ ] **Type consistency**: `stdout_capture_mode` and `reader_died` keys used uniformly across `_run_tee_mode`, `_run_legacy_capture`, `_run_passthrough`.
- [ ] **No regression**: `./test.sh --full --regression` passes (or only KNOWN_FAILURES.txt).