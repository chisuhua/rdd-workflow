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
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import IO, Any, Optional


@dataclass
class Trace:
    """Open trace file handle with phase/session metadata."""

    path: Path
    phase: str
    session_id: str
    _fh: Optional[IO[str]] = None

    def close(self) -> None:
        fh = self._fh
        if fh is not None and not fh.closed:
            fh.close()


def cmd_orchestrate(args: list[str]) -> int:
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

    parsed = parser.parse_args(args)
    trace_dir = _get_trace_dir()

    if parsed.action == "subprocess":
        return _handle_subprocess(parsed.cmd, trace_dir)
    if parsed.action == "mark-checkpoint":
        return _handle_checkpoint(parsed.name, parsed.state_marker, trace_dir)
    if parsed.action == "finalize":
        return _handle_finalize(trace_dir)
    if parsed.action == "sweep-stale-traces":
        return _handle_sweep(trace_dir)
    return 2  # unreachable


def _get_trace_dir() -> Path:
    """Return the trace directory from env or default."""
    raw = os.environ.get("RDDF_TRACE_DIR", ".rddf/state/trace")
    return Path(raw).resolve()


def _get_session_id() -> str:
    """Read rddf-session owner_opencode_session_id or generate a fresh UUID.

    Per ADR-0017 fallback: try sessions.json first, then env, then fresh UUID.
    """
    project_root = os.environ.get("RDDF_PROJECT_ROOT", ".")
    sessions_path = Path(project_root) / ".rddf" / "state" / "sessions.json"
    if sessions_path.is_file():
        try:
            data = json.loads(sessions_path.read_text())
            current = data.get("current", {})
            sid = current.get("owner_opencode_session_id")
            if sid:
                return sid
        except (OSError, json.JSONDecodeError, KeyError):
            pass
    return os.environ.get("RDDF_OPENCODE_SESSION_ID", uuid.uuid4().hex)


def _get_trace_path(phase: str, session_id: str, pid: int, epoch: int) -> Path:
    """Return path for a new trace file.

    Filename: ``<phase>-<session>-<pid>-<epoch>-<uuid>.jsonl``
    Epoch ensures uniqueness even if pid reused within same second.
    UUID suffix guards against collision from same-process multi-open.
    """
    fname = f"{phase}-{session_id}-{pid}-{epoch}-{uuid.uuid4().hex[:8]}.jsonl"
    return _get_trace_dir() / fname


def _open_trace(phase: str, session_id: Optional[str] = None) -> Trace:
    """Open or reuse a trace file for writing.

    If an unfinalized trace exists for ``phase``, append to it. Otherwise
    create a new one. Ensures ``RDDF_TRACE_DIR`` exists; raises OSError
    on permission failure.
    """
    sid = session_id or _get_session_id()
    trace_dir = _get_trace_dir()
    trace_dir.mkdir(parents=True, exist_ok=True)

    existing = _find_open_trace(trace_dir, phase)
    if existing is not None:
        fh = open(existing, "a", encoding="utf-8")
        return Trace(path=existing, phase=phase, session_id=sid, _fh=fh)

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
    fh = trace._fh
    if fh is None:
        raise RuntimeError("Trace not opened")
    fh.write(line + "\n")
    fh.flush()


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
                continue
    return events


def _find_open_trace(trace_dir: Path, phase: str) -> Optional[Path]:
    """Return the most recent trace file for ``phase`` that has no finalize event."""
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


def _handle_subprocess(
    cmd: list[str],
    trace_dir: Path,
    timeout: Optional[int] = None,
) -> int:
    """Run a subprocess and record its result to a new trace.

    Args:
        cmd: argv list (no shell). First call per phase entry also
            triggers a stale-trace sweep.
        trace_dir: target directory for the trace file.
        timeout: seconds before subprocess.TimeoutExpired. Defaults to
            ``RDDF_ORCHESTRATE_TIMEOUT`` env var or 600.

    Returns:
        The subprocess return code (timeout → 124).
    """
    from skills._lib.loop.sanitizer import sanitize

    if timeout is None:
        timeout = int(os.environ.get("RDDF_ORCHESTRATE_TIMEOUT", "600"))

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


def _handle_finalize(trace_dir: Path) -> int:
    """Close the current trace with a finalize event and trigger analysis.

    Reads all events written so far, counts subprocess failures + checkpoints,
    appends a finalize event with those counts. Calls analyze_phase_trace()
    if there were subprocess failures.
    """
    phase = os.environ.get("RDDF_PHASE", "unknown")
    trace_file = _find_open_trace(trace_dir, phase)
    if trace_file is None:
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
        except Exception as e:
            print(f"warning: analyze_phase_trace failed: {e}", file=sys.stderr)

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
    phase_filter = os.environ.get("RDDF_PHASE")

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
            continue

        mtime = trace_file.stat().st_mtime
        age_seconds = now - mtime
        if age_seconds < max_age_min * 60:
            continue

        try:
            cls = _classify_interrupted_phase(events)
            if cls is not None:
                project_root = os.environ.get("RDDF_PROJECT_ROOT", ".")
                from skills._lib.post_flow_analysis import report_flow_bug
                report_flow_bug(cls, project_root=project_root)
        except Exception as e:
            print(f"warning: sweep report failed for {trace_file.name}: {e}", file=sys.stderr)
        try:
            trace_file.unlink()
        except OSError:
            pass

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

    subprocess_events = [e for e in events if e.get("type") == "subprocess"]
    if not subprocess_events:
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
    last_returncode = last.get("returncode", 0)

    if last_returncode != 0:
        outcome = PhaseOutcome(
            phase=os.environ.get("RDDF_PHASE", "unknown"),
            exit_code=last_returncode,
            stderr=last.get("stderr_tail", ""),
            stdout_tail=last.get("stdout_tail", ""),
            traceback="",
        )
        return classify_phase_outcome(
            phase=os.environ.get("RDDF_PHASE", "unknown"),
            outcome=outcome,
        )

    return Classification(
        root_cause=ROOT_CAUSE_FLOW,
        report_category=REPORT_CATEGORY_CRASH,
        matched_rule="INTERRUPTED-WITH-OK-LAST",
        description=f"phase ended with last subprocess exit=0 but no finalize event (likely SIGKILL after success, or agent missed checklist)",
        metadata={
            "phase": "trace",
            "matched_rule": "INTERRUPTED-WITH-OK-LAST",
            "last_returncode": last_returncode,
            "subprocess_count": len(subprocess_events),
        },
        should_report=True,
        user_hint=USER_HINTS.get(ROOT_CAUSE_FLOW, ""),
    )


def _run_trace_gc(trace_dir: Path) -> None:
    """Garbage-collect old trace files."""
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

    if len(unfinalized) > 50:
        unfinalized.sort()
        for _, t in unfinalized[: len(unfinalized) - 50]:
            try:
                t.unlink()
            except OSError:
                pass


if __name__ == "__main__":
    import sys

    sys.exit(cmd_orchestrate(sys.argv[1:]))