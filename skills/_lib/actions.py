"""Built-in actions + subprocess wrapper for the loop engine (v2.0).

7 built-in actions cover v1.x workflow operations. Custom actions can be added
by dropping Python files in `.rddf/actions/` that subclass `Action`.

Per the v2-loop-engine spec (detectors-actions/spec.md):
- actions-builtin-set: 7 built-ins returning `ActionResult(success, data, error)`
- actions-plugin-extension: load `Action` subclasses from `.rddf/actions/`
- Action execution: subprocess with stdout/stderr captured + result recorded
- Action timeout: 30-minute wall-clock cap
"""
from __future__ import annotations
import subprocess
import importlib.util
import json
import datetime
import os
from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import Optional

from skills._lib.event_log import EventLog
from skills._lib.event_types import EventType, Severity
from skills._lib.plugin_loader import PluginLoader
from skills._lib.defaults import ACTION_PLUGIN_DIR


# ─────────────────────────────────────────────────────────────────────────────
# Result dataclass + subprocess wrapper
# ─────────────────────────────────────────────────────────────────────────────


@dataclass
class ActionResult:
    """Result of an action execution. `success` is the contract; `data` carries
    action-specific output; `error` is a human-readable failure summary."""
    success: bool
    data: dict = field(default_factory=dict)
    error: Optional[str] = None

    def to_dict(self) -> dict:
        return asdict(self)


def run_subprocess(cmd: list, timeout_seconds: int = 30 * 60) -> ActionResult:
    """Run a subprocess with timeout. Returns ActionResult with stdout/stderr.

    On success: `data = {stdout, stderr, returncode}`, `success=True`, `error=None`.
    On non-zero exit: `success=False`, `error="exit N: <stderr-truncated>"`.
    On TimeoutExpired: `success=False`, `data["timed_out"]=True`, `error="Timeout after Ns"`.
    """
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout_seconds,
        )
        success = result.returncode == 0
        return ActionResult(
            success=success,
            data={
                "stdout": result.stdout,
                "stderr": result.stderr,
                "returncode": result.returncode,
            },
            error=None if success else f"exit {result.returncode}: {result.stderr[:200]}",
        )
    except subprocess.TimeoutExpired:
        return ActionResult(
            success=False,
            data={"timed_out": True, "timeout_seconds": timeout_seconds},
            error=f"Timeout after {timeout_seconds}s",
        )
    except Exception as e:
        return ActionResult(
            success=False,
            data={"exception": str(e)},
            error=str(e),
        )


# ─────────────────────────────────────────────────────────────────────────────
# Action base class
# ─────────────────────────────────────────────────────────────────────────────


class Action:
    """Base class for all actions. Subclass and set `name`."""
    name: str = "base"

    def execute(self, params: dict, event_log: EventLog) -> ActionResult:
        raise NotImplementedError


# ─────────────────────────────────────────────────────────────────────────────
# Built-in actions
# ─────────────────────────────────────────────────────────────────────────────


def action_create_worktree(params: dict, event_log: EventLog) -> ActionResult:
    """Create a git worktree. params: {branch: str, path: str}"""
    branch = params.get("branch")
    path = params.get("path")
    if not branch or not path:
        result = ActionResult(success=False, error="branch and path required")
    else:
        result = run_subprocess(
            ["git", "worktree", "add", "-b", branch, path],
            timeout_seconds=60,
        )
    event_log.record(
        EventType.EXECUTION_UNIT_COMPLETED,
        Severity.INFO if result.success else Severity.ERROR,
        f"worktree create: {branch} -> {path}",
        context=result.to_dict(),
    )
    return result


def action_generate_plan(params: dict, event_log: EventLog) -> ActionResult:
    """Generate an implementation plan. params: {change: str, output: str}.

    v2.0 contract: dispatches to the spec-workflow/writing-plans skill (no
    external dependency, no detection chain). When called from an AI session,
    the caller is expected to follow up with
    skill_use("spec-workflow/writing-plans") to fill in the real plan
    content; this action emits a clear marker so downstream consumers
    (execute.md, status.md) can detect the pending state.

    Returns ActionResult(success, data={"path", "mode", "status"}, error).
    """
    change = params.get("change", "")
    output = params.get(
        "output",
        f".rddf/plans/{change}.md" if change else ".rddf/plans/auto-generated.md",
    )

    if not change:
        result = ActionResult(success=False, error="change parameter required")
        event_log.record(
            EventType.EXECUTION_UNIT_COMPLETED,
            Severity.ERROR,
            "plan generation failed: missing change",
            context=result.to_dict(),
        )
        return result

    out_path = Path(output)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    if os.environ.get("SKIP_PROMETHEUS_PLANNING", "no").lower() == "yes":
        out_path.write_text(
            f"# Placeholder plan for {change}\n\n"
            f"Generated at {datetime.datetime.now().isoformat()}\n"
            f"Source: SKIP_PROMETHEUS_PLANNING=yes — no real plan content.\n"
        )
        result = ActionResult(success=True, data={"path": str(out_path), "mode": "skip"})
        event_log.record(
            EventType.EXECUTION_UNIT_COMPLETED,
            Severity.INFO,
            f"plan generated (skip mode): {change}",
            context=result.to_dict(),
        )
        return result

    writing_plans_script = Path(__file__).parent.parent / "spec-workflow-writing-plans.md"
    if not writing_plans_script.exists():
        result = ActionResult(
            success=False,
            data={"path": str(out_path), "mode": "missing-skill"},
            error=f"spec-workflow/writing-plans skill not found at {writing_plans_script}",
        )
        event_log.record(
            EventType.EXECUTION_UNIT_COMPLETED,
            Severity.ERROR,
            f"plan generation failed: missing spec-workflow/writing-plans skill",
            context=result.to_dict(),
        )
        return result

    marker = (
        f"# Plan generation requested for {change}\n\n"
        f"**Status**: pending — awaiting spec-workflow/writing-plans skill invocation\n"
        f"**Output path**: {out_path}\n"
        f"**Generated at**: {datetime.datetime.now().isoformat()}\n\n"
        f"## Next step\n\n"
        f"Run `skill_use(\"spec-workflow/writing-plans\")` from the AI session, then re-invoke "
        f"this action. The skill will populate this file with the real plan content.\n"
    )
    out_path.write_text(marker)
    result = ActionResult(
        success=True,
        data={
            "path": str(out_path),
            "mode": "self-contained",
            "status": "pending-ai-invocation",
        },
    )
    event_log.record(
        EventType.EXECUTION_UNIT_COMPLETED,
        Severity.INFO,
        f"plan generation marker created: {change} (mode: self-contained)",
        context=result.to_dict(),
    )
    return result


def action_execute_worktree(params: dict, event_log: EventLog) -> ActionResult:
    """Execute a worktree's contents. params: {path: str, command: str (space-separated)}"""
    path = params.get("path", ".")
    cmd_str = params.get("command", "echo no-op")
    cmd_list = cmd_str.split() if isinstance(cmd_str, str) else list(cmd_str)
    result = run_subprocess(cmd_list, timeout_seconds=30 * 60)
    event_log.record(
        EventType.EXECUTION_UNIT_COMPLETED,
        Severity.INFO if result.success else Severity.ERROR,
        f"execute worktree {path}: {cmd_str}",
        context=result.to_dict(),
    )
    return result


def action_archive_change(params: dict, event_log: EventLog) -> ActionResult:
    """Archive an openspec change. params: {change: str}

    Renames `openspec/changes/{change}` → `openspec/changes/archive/{YYYY-MM-DD}-{change}`.
    """
    change = params.get("change")
    if not change:
        result = ActionResult(success=False, error="change required")
    else:
        src = Path(f"openspec/changes/{change}")
        dst_dir = Path("openspec/changes/archive")
        date_prefix = datetime.date.today().isoformat()
        dst = dst_dir / f"{date_prefix}-{change}"
        if not src.exists():
            result = ActionResult(success=False, error=f"change not found: {src}")
        else:
            try:
                dst_dir.mkdir(parents=True, exist_ok=True)
                src.rename(dst)
                result = ActionResult(
                    success=True,
                    data={"archived_to": str(dst), "date": date_prefix},
                )
            except Exception as e:
                result = ActionResult(
                    success=False,
                    data={"exception": str(e)},
                    error=str(e),
                )
    event_log.record(
        EventType.EXECUTION_UNIT_COMPLETED,
        Severity.INFO if result.success else Severity.ERROR,
        f"archived change: {change}",
        context=result.to_dict(),
    )
    return result


def action_cleanup_stale(params: dict, event_log: EventLog) -> ActionResult:
    """Clean up stale git worktrees. params: {dry_run: bool (default True)}.

    Lists worktrees via `git worktree list --porcelain` and removes those
    that are not the main worktree. Dry-run mode reports without removing."""
    dry_run = bool(params.get("dry_run", True))
    list_result = run_subprocess(
        ["git", "worktree", "list", "--porcelain"],
        timeout_seconds=10,
    )
    if not list_result.success:
        result = ActionResult(
            success=False,
            data={"list_error": list_result.to_dict()},
            error="failed to list worktrees",
        )
    else:
        cleaned = []
        cwd = str(Path.cwd())
        for line in list_result.data.get("stdout", "").splitlines():
            if line.startswith("worktree ") and ".." not in line:
                wt_path = line.split(" ", 1)[1]
                # Never remove the main worktree.
                if wt_path == cwd:
                    continue
                if not dry_run:
                    run_subprocess(
                        ["git", "worktree", "remove", wt_path, "--force"],
                        timeout_seconds=30,
                    )
                cleaned.append(wt_path)
        result = ActionResult(
            success=True,
            data={"cleaned": cleaned, "dry_run": dry_run, "count": len(cleaned)},
        )
    event_log.record(
        EventType.EXECUTION_UNIT_COMPLETED,
        Severity.INFO if result.success else Severity.ERROR,
        f"cleanup {'dry-run' if dry_run else 'executed'}: {result.data.get('count', 0)} item(s)",
        context=result.to_dict(),
    )
    return result


def action_update_roadmap(params: dict, event_log: EventLog) -> ActionResult:
    """Update roadmap state. params: {phase: str, category: str}

    Writes a JSON document to `.rddf/state/roadmap-state.json` containing
    `phase`, `category`, and `updated_at` (ISO 8601 UTC)."""
    phase = params.get("phase")
    category = params.get("category")
    if not phase or not category:
        result = ActionResult(success=False, error="phase and category required")
    else:
        try:
            roadmap_file = Path(".rddf/state/roadmap-state.json")
            roadmap_file.parent.mkdir(parents=True, exist_ok=True)
            data = {
                "phase": phase,
                "category": category,
                "updated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            }
            roadmap_file.write_text(json.dumps(data, indent=2))
            result = ActionResult(success=True, data=data)
        except Exception as e:
            result = ActionResult(
                success=False,
                data={"exception": str(e)},
                error=str(e),
            )
    event_log.record(
        EventType.EXECUTION_UNIT_COMPLETED,
        Severity.INFO if result.success else Severity.ERROR,
        f"roadmap updated: {phase} / {category}",
        context=result.to_dict(),
    )
    return result


def action_create_adr(params: dict, event_log: EventLog) -> ActionResult:
    """Create a new ADR. params: {title: str, status: str (default 'proposed')}

    Writes a Markdown file at `docs/adr/{NNNN}-{slug}.md` where NNNN is the
    next 4-digit sequence number (existing-count + 1) and slug is the
    lower-cased, dash-joined title."""
    title = params.get("title")
    status = params.get("status", "proposed")
    if not title:
        result = ActionResult(success=False, error="title required")
    else:
        try:
            adr_dir = Path("docs/adr")
            adr_dir.mkdir(parents=True, exist_ok=True)
            existing = sorted(adr_dir.glob("*.md"))
            next_num = len(existing) + 1
            slug = title.lower().replace(" ", "-")
            adr_path = adr_dir / f"{next_num:04d}-{slug}.md"
            adr_path.write_text(
                f"# ADR-{next_num:04d}: {title}\n\n"
                f"**Status:** {status}\n\n"
                f"## Context\n\n## Decision\n\n## Consequences\n"
            )
            result = ActionResult(
                success=True,
                data={"path": str(adr_path), "number": next_num, "slug": slug},
            )
        except Exception as e:
            result = ActionResult(
                success=False,
                data={"exception": str(e)},
                error=str(e),
            )
    event_log.record(
        EventType.EXECUTION_UNIT_COMPLETED,
        Severity.INFO if result.success else Severity.ERROR,
        f"ADR created: {result.data.get('path', '<failed>')}",
        context=result.to_dict(),
    )
    return result


# ─────────────────────────────────────────────────────────────────────────────
# Registry + plugin loader
# ─────────────────────────────────────────────────────────────────────────────


BUILTIN_ACTIONS = [
    action_create_worktree,
    action_generate_plan,
    action_execute_worktree,
    action_archive_change,
    action_cleanup_stale,
    action_update_roadmap,
    action_create_adr,
]


class _FunctionAction:
    """Wrap a built-in action function with the `name` / `execute` interface.

    Plugin subclasses of `Action` already provide this interface, so the
    registry returns a uniform shape regardless of action source."""

    def __init__(self, fn):
        self.fn = fn
        self.name = fn.__name__

    def execute(self, params: dict, event_log: EventLog) -> ActionResult:
        return self.fn(params, event_log)


_action_plugin_loader = PluginLoader(Action, ACTION_PLUGIN_DIR)


def load_plugin_actions(plugin_dir: str = ACTION_PLUGIN_DIR) -> list:
 """Load custom `Action` subclasses from `plugin_dir`.

 Skips files whose names start with `_`. Silently skips files that fail
 to import (so a broken plugin cannot break the whole engine)."""
 return _action_plugin_loader.load_plugins(plugin_dir)


def all_actions() -> list:
 """Return built-in + plugin actions in a uniform wrapper shape."""
 return _action_plugin_loader.all_plugins([_FunctionAction(fn) for fn in BUILTIN_ACTIONS])
