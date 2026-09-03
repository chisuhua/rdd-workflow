"""Read-only audit of unmapped proposals.

Per Wave 2 Task 3.1 (Stage 2.5 P0-3 follow-up): produces a prioritized
list of `.rddf/improvements/*.md` files without a `roadmap_ref`,
grouped by priority, with a heuristic project_id suggestion (substring
match against Phase Skeleton Theme column / fragment 主题). Pure
derived view; no mutation.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from _lib.planner_sync import discover_projects
from _lib.planner_attach import list_valid_projects

__all__ = ["AuditRow", "build_audit_rows", "render_markdown", "suggest_project_id"]


@dataclass
class AuditRow:
    propro: str
    priority: str
    feedback_status: str
    suggested_project_id: str | None


def suggest_project_id(proposal_name: str, valid_projects: Iterable[str]) -> str | None:
    """Return the first Theme that matches the proposal name (ignoring separators).

    Both the proposal name and the theme are normalized by stripping
    non-alphanumeric characters, then a substring match is performed
    (case-sensitive). This catches hyphenated proposal names like
    `add-foo-bar` against themes like `foo bar`. No fuzzy / semantic
    matching beyond that. Returns None when no Theme matches.
    """
    import re as _re
    normalized_proposal = _re.sub(r"[^A-Za-z0-9]", "", proposal_name)
    for theme in valid_projects:
        if not theme:
            continue
        normalized_theme = _re.sub(r"[^A-Za-z0-9]", "", theme)
        if normalized_theme and normalized_theme in normalized_proposal:
            return theme
    return None


def build_audit_rows(project_root: Path) -> list[AuditRow]:
    valid_projects = list_valid_projects(project_root)
    projects = discover_projects(project_root)
    rows: list[AuditRow] = []
    for p in projects:
        if p["mapped"]:
            continue
        rows.append(AuditRow(
            propro=p["proposal"],
            priority=p.get("priority") or "P2",
            feedback_status=p.get("feedback_status") or "none",
            suggested_project_id=suggest_project_id(p["proposal"], valid_projects),
        ))
    priority_rank = {"P0": 0, "P1": 1, "P2": 2, "P3": 3}
    rows.sort(key=lambda r: (priority_rank.get(r.priority, 9), r.propro))
    return rows


def render_markdown(rows: list[AuditRow]) -> str:
    if not rows:
        return "_No unmapped proposals._\n"
    lines = [
        "| Proposal | Priority | Feedback | Suggested project_id |",
        "|----------|----------|----------|----------------------|",
    ]
    for r in rows:
        sug = r.suggested_project_id if r.suggested_project_id else "_(manual)_"
        lines.append(f"| {r.propro} | {r.priority} | {r.feedback_status} | {sug} |")
    return "\n".join(lines) + "\n"