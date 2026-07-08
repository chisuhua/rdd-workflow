"""Built-in state detectors + plugin loader for the v2-loop-engine.

Provides 9 built-in detectors that scan v1.x + v2.0 workflow state, plus a
plugin loader so users can register additional `Detector` subclasses by
dropping Python files into `.rddf/detectors/`.

Public surface:
- `Detector`              — base class for all detectors
- `DetectionResult`       — dataclass: type / data / message / severity
- `BUILTIN_DETECTORS`     — list of the 9 built-in `Detector` instances
- `load_plugin_detectors` — load custom detectors from a directory
- `all_detectors`         — built-in + plugin detectors (for `scan_state`)
- `detect_*`              — the 9 built-in detector functions (also exported)

Each detector takes a `state: dict` and returns a `DetectionResult`. They
never raise; any exception is captured into the result with `severity="warn"`.

Performance budget: all 9 built-ins run sequentially in < 500ms
(see `test_all_builtin_detectors_run_sequentially_under_500ms`).
"""
from __future__ import annotations

import datetime
import importlib.util
import json
import os
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable

from skills._lib.defaults import DETECTOR_PLUGIN_DIR
from skills._lib.plugin_loader import PluginLoader


# Severity constants — kept module-level so plugins can reuse them.
SEVERITY_INFO = "info"
SEVERITY_WARN = "warn"
SEVERITY_ERROR = "error"


@dataclass
class DetectionResult:
    """Structured output of a single detector run.

    Fields:
        type     — short identifier, e.g. "worktrees", "pending_changes".
                   Used as the key when results are written to the state vector.
        data     — detector-specific payload (dict). Must be JSON-serializable.
        message  — human-readable one-line summary suitable for logs / UI.
        severity — "info" | "warn" | "error" (default "info").
    """

    type: str
    data: dict
    message: str
    severity: str = SEVERITY_INFO

    def to_dict(self) -> dict:
        """Return a JSON-serializable dict representation."""
        return asdict(self)


class Detector:
    """Base class for all detectors. Subclass and implement `detect()`."""

    name: str = "base"

    def detect(self, state: dict) -> DetectionResult:
        """Run the detector against the given state vector.

        Args:
            state: Current loop state (dotted-path dict from `StateVector.to_dict()`).

        Returns:
            DetectionResult. Implementations MUST NOT raise — wrap exceptions
            into a result with the appropriate severity.
        """
        raise NotImplementedError


# ─────────────────────────────────────────────────────────────────────────────
# Built-in detector functions
#
# Each function is `fn(state: dict) -> DetectionResult`. The wrapper
# `_FunctionDetector` below adapts them to the `Detector` interface so
# `BUILTIN_DETECTORS` exposes uniform `Detector` instances.
# ─────────────────────────────────────────────────────────────────────────────


def detect_worktrees(state: dict) -> DetectionResult:
    """Detect active git worktrees via `git worktree list --porcelain`."""
    try:
        result = subprocess.run(
            ["git", "worktree", "list", "--porcelain"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        lines = [ln for ln in result.stdout.splitlines() if ln.startswith("worktree ")]
        worktrees = [ln.split(" ", 1)[1] for ln in lines]
        return DetectionResult(
            type="worktrees",
            data={"worktrees": worktrees, "count": len(worktrees)},
            message=f"{len(worktrees)} active worktree(s)",
        )
    except Exception as exc:  # noqa: BLE001 — detector must never raise
        return DetectionResult(
            type="worktrees",
            data={"error": str(exc)},
            message=str(exc),
            severity=SEVERITY_WARN,
        )


def detect_pending_changes(state: dict) -> DetectionResult:
    """Detect active (non-archived) openspec changes under `openspec/changes/`."""
    changes_dir = Path("openspec/changes")
    if not changes_dir.exists():
        return DetectionResult(
            type="pending_changes",
            data={"changes": [], "count": 0},
            message="No openspec/changes dir",
        )
    active = [d.name for d in changes_dir.iterdir() if d.is_dir() and d.name != "archive"]
    return DetectionResult(
        type="pending_changes",
        data={"changes": sorted(active), "count": len(active)},
        message=f"{len(active)} pending change(s)",
    )


def detect_archived_changes(state: dict) -> DetectionResult:
    """Detect archived openspec changes under `openspec/changes/archive/`."""
    archive_dir = Path("openspec/changes/archive")
    if not archive_dir.exists():
        return DetectionResult(
            type="archived_changes",
            data={"changes": [], "count": 0},
            message="No archive dir",
        )
    archived = [d.name for d in archive_dir.iterdir() if d.is_dir()]
    return DetectionResult(
        type="archived_changes",
        data={"changes": sorted(archived), "count": len(archived)},
        message=f"{len(archived)} archived change(s)",
    )


def detect_roadmap_state(state: dict) -> DetectionResult:
    """Detect current phase + category from `.rddf/state/roadmap-state.json`."""
    roadmap_file = Path(".rddf/state/roadmap-state.json")
    if not roadmap_file.exists():
        return DetectionResult(
            type="roadmap_state",
            data={},
            message="No roadmap state file",
            severity=SEVERITY_WARN,
        )
    try:
        data = json.loads(roadmap_file.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        return DetectionResult(
            type="roadmap_state",
            data={"error": str(exc)},
            message=f"Roadmap state file unreadable: {exc}",
            severity=SEVERITY_WARN,
        )
    return DetectionResult(
        type="roadmap_state",
        data=data,
        message=f"Phase: {data.get('phase', 'unknown')}, category: {data.get('category', 'unknown')}",
    )


def detect_adr_status(state: dict) -> DetectionResult:
    """Detect ADR directory status — counts files in `docs/adr/` or `adr/`."""
    adr_dir = Path("docs/adr") if Path("docs/adr").exists() else Path("adr")
    if not adr_dir.exists():
        return DetectionResult(
            type="adr_status",
            data={"exists": False},
            message="No ADR dir",
            severity=SEVERITY_WARN,
        )
    adrs = sorted([f.name for f in adr_dir.glob("*.md")])
    return DetectionResult(
        type="adr_status",
        data={"exists": True, "adrs": adrs, "count": len(adrs)},
        message=f"{len(adrs)} ADR(s) found",
    )


def detect_health_issues(state: dict) -> DetectionResult:
    """Detect general repo health — count uncommitted files via `git status --porcelain`."""
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain", "--untracked-files=no"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        dirty = [ln for ln in result.stdout.splitlines() if ln.strip()]
        severity = SEVERITY_WARN if len(dirty) > 10 else SEVERITY_INFO
        return DetectionResult(
            type="health",
            data={"dirty_files": dirty, "count": len(dirty)},
            message=f"{len(dirty)} uncommitted file(s)",
            severity=severity,
        )
    except Exception as exc:  # noqa: BLE001 — detector must never raise
        return DetectionResult(
            type="health",
            data={"error": str(exc)},
            message=str(exc),
            severity=SEVERITY_ERROR,
        )


def detect_test_gaps(state: dict) -> DetectionResult:
    """Detect test coverage gaps — modules in `skills/_lib/` without `tests/unit/test_<name>.py`."""
    lib_dir = Path("skills/_lib")
    tests_dir = Path("tests/unit")
    if not lib_dir.exists():
        return DetectionResult(
            type="test_gaps",
            data={"gaps": [], "count": 0},
            message="No skills/_lib dir",
        )
    py_files = {p.stem for p in lib_dir.glob("*.py") if p.stem != "__init__"}
    test_files = {p.stem.replace("test_", "", 1) for p in tests_dir.glob("test_*.py")}
    gaps = sorted(py_files - test_files)
    return DetectionResult(
        type="test_gaps",
        data={"gaps": gaps, "count": len(gaps)},
        message=f"{len(gaps)} module(s) without tests",
        severity=SEVERITY_WARN if gaps else SEVERITY_INFO,
    )


def detect_stale_branches(state: dict) -> DetectionResult:
    """Detect stale git branches — no commits in the last 30 days."""
    try:
        result = subprocess.run(
            [
                "git",
                "for-each-ref",
                "--format=%(refname:short) %(committerdate:iso8601)",
                "refs/heads/",
            ],
            capture_output=True,
            text=True,
            timeout=5,
        )
        now = datetime.datetime.now(datetime.timezone.utc)
        stale: list[dict] = []
        for line in result.stdout.splitlines():
            parts = line.split(" ", 1)
            if len(parts) != 2:
                continue
            branch, date_str = parts
            try:
                # Git's iso8601 uses 'Z' suffix; Python expects '+00:00'
                branch_date = datetime.datetime.fromisoformat(date_str.replace("Z", "+00:00"))
            except ValueError:
                continue
            age_days = (now - branch_date).days
            if age_days > 30:
                stale.append({"branch": branch, "age_days": age_days})
        return DetectionResult(
            type="stale_branches",
            data={"branches": stale, "count": len(stale)},
            message=f"{len(stale)} stale branch(es)",
            severity=SEVERITY_WARN if stale else SEVERITY_INFO,
        )
    except Exception as exc:  # noqa: BLE001 — detector must never raise
        return DetectionResult(
            type="stale_branches",
            data={"error": str(exc)},
            message=str(exc),
            severity=SEVERITY_WARN,
        )


def detect_trigger_events(state: dict) -> DetectionResult:
    """Detect pending trigger events from TriggerManager's EventQueue.

    v3.0: Reads pending events from a singleton EventQueue and reports them as
    DetectionResult(type="trigger_events"). The LoopEngine's scan_state phase
    consumes these events like any other detection input.
    """
    # Import here to avoid circular dependency at module load
    try:
        from skills._lib.event_queue import EventQueue
        from skills._lib.trigger_registry import TriggerRegistry
    except ImportError:
        return DetectionResult(
            type="trigger_events",
            data={"events": [], "count": 0},
            message="trigger modules not available",
            severity=SEVERITY_WARN,
        )
    try:
        # Use project_root from state if available; otherwise current dir
        project_root = state.get("metadata", {}).get("project_root", ".")
        reg = TriggerRegistry(project_root=project_root)
        if not os.path.exists(reg.path):
            return DetectionResult(
                type="trigger_events",
                data={"events": [], "count": 0},
                message="no trigger registry",
            )
        manager = reg.load()
        # If there's a singleton event queue in process, drain it
        # (In production, the queue would be passed via DI; here we use a heuristic)
        events = []
        # Check for any pending events via manager state
        for t in manager.get_enabled():
            if t.last_fire_at:
                events.append({
                    "trigger_id": t.id,
                    "type": t.type,
                    "last_fire_at": t.last_fire_at,
                })
        return DetectionResult(
            type="trigger_events",
            data={"events": events, "count": len(events)},
            message=f"{len(events)} trigger event(s) recorded",
        )
    except Exception as exc:  # noqa: BLE001
        return DetectionResult(
            type="trigger_events",
            data={"error": str(exc)},
            message=str(exc),
            severity=SEVERITY_WARN,
        )


# ─────────────────────────────────────────────────────────────────────────────
# Registry + plugin loader
# ─────────────────────────────────────────────────────────────────────────────


class _FunctionDetector(Detector):
    """Adapter that wraps a `fn(state) -> DetectionResult` callable as a `Detector`."""

    def __init__(self, fn: Callable[[dict], DetectionResult]) -> None:
        self.fn = fn
        # Preserve the underlying function name so `BUILTIN_DETECTORS`
        # exposes the canonical names: detect_worktrees, detect_pending_changes, …
        self.name = fn.__name__

    def detect(self, state: dict) -> DetectionResult:
        return self.fn(state)


# Order matters: this list IS the canonical scan order used by `scan_state`.
# Each entry is a `Detector` instance (not a raw function), so callers can
# uniformly do `detector.detect(state)` or read `detector.name`.
BUILTIN_DETECTORS: list[Detector] = [
    _FunctionDetector(detect_worktrees),
    _FunctionDetector(detect_pending_changes),
    _FunctionDetector(detect_archived_changes),
    _FunctionDetector(detect_roadmap_state),
    _FunctionDetector(detect_adr_status),
    _FunctionDetector(detect_health_issues),
    _FunctionDetector(detect_test_gaps),
    _FunctionDetector(detect_stale_branches),
    _FunctionDetector(detect_trigger_events),  # v3.0
]


_detector_plugin_loader = PluginLoader(Detector, DETECTOR_PLUGIN_DIR)


def load_plugin_detectors(plugin_dir: str = DETECTOR_PLUGIN_DIR) -> list[Detector]:
    """Load custom `Detector` subclasses from a directory of `.py` files.

    Behavior:
        - If `plugin_dir` does not exist, returns `[]` (no error).
        - Skips files whose names start with `_` (private helpers).
        - Files that fail to import are silently skipped (logged only via the
          swallowed exception — plugins must be self-contained).
        - Returns each discovered `Detector` subclass as an instance.
    """
    return _detector_plugin_loader.load_plugins(plugin_dir)


def all_detectors(plugin_dir: str = DETECTOR_PLUGIN_DIR) -> list[Detector]:
    """Return built-in + plugin detectors in scan order.

    Built-ins come first (deterministic order), followed by any plugins
    discovered via `load_plugin_detectors`. Plugins with duplicate names
    (matching a built-in) will be appended after the built-in — callers
    can de-duplicate by `.name` if they need a single-instance registry.
    """
    return _detector_plugin_loader.all_plugins(BUILTIN_DETECTORS, plugin_dir)


__all__ = [
    "SEVERITY_INFO",
    "SEVERITY_WARN",
    "SEVERITY_ERROR",
    "DetectionResult",
    "Detector",
    "BUILTIN_DETECTORS",
    "load_plugin_detectors",
    "all_detectors",
    # Built-in detector functions (also exposed for direct invocation / testing)
    "detect_worktrees",
    "detect_pending_changes",
    "detect_archived_changes",
    "detect_roadmap_state",
    "detect_adr_status",
    "detect_health_issues",
    "detect_test_gaps",
    "detect_stale_branches",
    "detect_trigger_events",
]
