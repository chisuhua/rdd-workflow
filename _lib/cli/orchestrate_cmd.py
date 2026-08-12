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


def _handle_checkpoint(name: str, state_marker: str, trace_dir: Path) -> int:
    """Placeholder — filled in Task 4."""
    raise NotImplementedError("filled in Task 4")


def _handle_finalize(trace_dir: Path) -> int:
    """Placeholder — filled in Task 5."""
    raise NotImplementedError("filled in Task 5")


def _handle_sweep(trace_dir: Path) -> int:
    """Sweep trace dir for stale unfinalized traces. Filled in Task 10."""
    return 0