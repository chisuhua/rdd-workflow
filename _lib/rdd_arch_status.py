"""Stage 3 Change 4: rdd-arch status aggregator.

Aggregates .arch-handoff.json (arch-owned) + .planner-feedback.json (planner-owned)
into a one-line status view consumed by `rddf arch status` and rdd-arch Phase 1.

Per ADR-0028: read-only consumer; rdd-arch does NOT write to .planner-feedback.json.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional


def _handoff_path(project_root: str) -> str:
    return os.path.join(project_root, ".rddf", "state", ".arch-handoff.json")


def _feedback_path(project_root: str) -> str:
    return os.path.join(project_root, ".rddf", "state", ".planner-feedback.json")


def _safe_read_json(path: str) -> Optional[Dict[str, Any]]:
    if not os.path.exists(path):
        return None
    try:
        with open(path) as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None


def build_arch_status(project_root: str) -> Dict[str, Any]:
    """Aggregate arch-handoff + planner-feedback into a status dict.

    Returns:
        {
          "arch": {complete_at, adr_count, current_phase, ...} | None,
          "planner": {open_critical, open_warning, ..., stale_count} | None,
          "planner_branch": str | None,
          "planner_commit": str | None,
        }
    """
    handoff = _safe_read_json(_handoff_path(project_root))
    feedback = _safe_read_json(_feedback_path(project_root))

    arch_section: Optional[Dict[str, Any]] = None
    if handoff:
        arch_section = {
            "complete_at": handoff.get("arch_complete_at"),
            "adr_count": handoff.get("adr_count", 0),
            "current_phase": handoff.get("current_phase", "default"),
            "version": handoff.get("version", 2),
        }

    planner_section: Optional[Dict[str, Any]] = None
    planner_branch: Optional[str] = None
    planner_commit: Optional[str] = None
    if feedback:
        summary = feedback.get("summary", {})
        stale_count = sum(1 for e in feedback.get("feedbacks", []) if e.get("stale"))
        planner_section = {
            "open_critical": summary.get("open_critical", 0),
            "open_warning": summary.get("open_warning", 0),
            "open_info": summary.get("open_info", 0),
            "acknowledged": summary.get("acknowledged", 0),
            "resolved": summary.get("resolved", 0),
            "dismissed": summary.get("dismissed", 0),
            "open_total": (
                summary.get("open_critical", 0)
                + summary.get("open_warning", 0)
                + summary.get("open_info", 0)
            ),
            "stale_count": stale_count,
        }
        planner_branch = feedback.get("branch")
        planner_commit = feedback.get("codebase_commit")

    return {
        "arch": arch_section,
        "planner": planner_section,
        "planner_branch": planner_branch,
        "planner_commit": planner_commit,
    }


def format_status_line(status: Dict[str, Any]) -> str:
    """Format arch status as a single line for rdd-arch Phase 1 + CLI summary.

    Examples:
      - 'rdd-arch: phase-1 | 3 ADRs | Planner: 1 critical, 0 warning, 1 stale'
      - 'rdd-arch: (no arch-done yet) | Planner: No planner feedback'
      - 'rdd-arch: phase-1 | 3 ADRs | Planner: No planner feedback'
    """
    arch = status.get("arch")
    planner = status.get("planner")

    if arch:
        prefix = f"rdd-arch: {arch['current_phase']} | {arch['adr_count']} ADRs"
    else:
        prefix = "rdd-arch: (no arch-done yet)"

    if planner is None:
        planner_part = "Planner: No planner feedback"
    else:
        oc = planner["open_critical"]
        ow = planner["open_warning"]
        oi = planner["open_info"]
        stale = planner["stale_count"]
        planner_part = (
            f"Planner: {oc} critical, {ow} warning, {oi} info"
            + (f", {stale} stale" if stale else "")
        )

    return f"{prefix} | {planner_part}"