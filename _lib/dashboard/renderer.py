"""Dashboard renderer - formats ``DashboardData`` into one of three modes.

Modes:
    ``terminal`` (default when stdout is a TTY)
        Box-drawing characters + emoji. 7 sections, each under a
        header bar. Designed for interactive ``rddf dashboard`` runs.

    ``json``
        Single JSON object via ``dataclasses.asdict(data)``. Suitable
        for CI / scripting / piping into ``jq``.

    ``plain``
        ASCII-only, no emoji, no box-drawing. Suitable for CI logs
        where Unicode rendering is unreliable, or for piped output
        where the consumer can't handle control characters.

Auto-degrade:
    If ``mode`` is ``"terminal"`` but ``os.isatty(sys.stdout.fileno())``
    is False (stdout is a pipe/file), the renderer automatically
    switches to ``plain``. This can be overridden by passing
    ``mode="terminal"`` explicitly along with a non-None
    ``output_file`` (forces terminal mode into the file).

Sections (per task brief):
    1. Workflow Phase   - arch / plan / ship status with emoji icons
    2. Session          - current binding from sessions
    3. Changes          - table: name, status, tasks, plan
                          (includes ⚠️ divergence lines when present)
    4. Worktrees        - list from ``git worktree list``
    5. Features         - feature_view from iteration.json
    6. Roadmap          - phase + per-phase (done/total) counts
    7. Pending          - proposal-suggestions count

This module imports only from the dashboard package's own ``__init__``
(to get the dataclass types for typing) and the Python stdlib. No
external dependencies.
"""
from __future__ import annotations

import dataclasses
import json
import os
import sys
from typing import Optional

from skills._lib.dashboard import DashboardData


# ---------------------------------------------------------------------------
# Emoji / icon maps
# ---------------------------------------------------------------------------

# Status -> emoji icon. Keys cover the iteration.json status enum plus
# a few dashboard-internal aliases (committed, done).
_STATUS_ICON = {
    "planned":      "📋",
    "proposed":     "📋",
    "in_worktree":  "🔧",
    "review":       "🔧",
    "completed":    "✅",
    "done":         "✔",
    "archived":     "📦",
    "committed":    "💼",
    "unknown":      "?",
}

# Plain-mode equivalents (ASCII only, no emoji). Single character to
# preserve column alignment with the terminal mode.
_STATUS_ICON_PLAIN = {
    "planned":      "+",
    "proposed":     "+",
    "in_worktree":  "*",
    "review":       "*",
    "completed":    "v",
    "done":          "v",
    "archived":     "-",
    "committed":    "$",
    "unknown":      "?",
}

# Session state -> emoji
_SESSION_ICON = {
    "active":    "📍",
    "orphaned":  "⚠️",
    "completed": "✅",
    "failed":    "❌",
    "abandoned": "🗑️",
}
_SESSION_ICON_PLAIN = {
    "active":    "*",
    "orphaned":  "!",
    "completed": "v",
    "failed":    "x",
    "abandoned": "-",
}

# Feature status -> emoji
_FEATURE_ICON = {
    "blocked":     "🚫",
    "in_progress": "🔧",
    "ready":       "📋",
    "done":        "✅",
    "ungrouped":   "•",
}
_FEATURE_ICON_PLAIN = {
    "blocked":     "B",
    "in_progress": "*",
    "ready":       "+",
    "done":        "v",
    "ungrouped":   ".",
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def render(
    data: DashboardData,
    mode: str = "terminal",
    output_file: Optional[str] = None,
) -> str:
    """Render ``data`` as a string in the requested mode.

    Args:
        data: A ``DashboardData`` instance from ``collect()``.
        mode: One of ``"terminal"``, ``"json"``, ``"plain"``.
            Defaults to ``"terminal"``.
        output_file: Optional path to write the rendered output to.
            When ``None``, the rendered string is returned but not
            written. When set, the file is written AND the string is
            returned (caller may still use it for logging).

    Returns:
        The rendered dashboard as a string. Always ends with a newline
        when non-empty.

    Auto-degrade behavior:
        If ``mode == "terminal"`` and stdout is not a TTY (piped /
        redirected) AND no ``output_file`` is given, the renderer
        automatically switches to ``plain`` mode. This matches the
        spec §4.5: "TTY -> colored + emoji + box-drawing; non-TTY ->
        auto-degrade to plain".

        If ``output_file`` is given, the auto-degrade is skipped - the
        caller explicitly wants terminal-mode output in a file (e.g.
        for snapshot tests).
    """
    if mode not in ("terminal", "json", "plain"):
        raise ValueError(
            f"invalid mode {mode!r}; must be one of 'terminal', 'json', 'plain'"
        )

    # Auto-degrade: terminal -> plain when not a TTY and no file target.
    if mode == "terminal" and output_file is None and not _stdout_is_tty():
        mode = "plain"

    if mode == "json":
        out = _render_json(data)
    elif mode == "plain":
        out = _render_plain(data)
    else:
        out = _render_terminal(data)

    if output_file is not None:
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(out)

    return out


# ---------------------------------------------------------------------------
# JSON mode
# ---------------------------------------------------------------------------


def _render_json(data: DashboardData) -> str:
    """Render as a single JSON object via ``dataclasses.asdict``.

    The output is a flat object with one key per section, suitable for
    piping into ``jq`` or consuming from another script. Tuple values
    (``roadmap_counts``) are converted to lists by the json encoder.
    """
    as_dict = dataclasses.asdict(data)
    # ``roadmap_counts`` is dict[str, tuple[int, int]]; asdict keeps the
    # tuples. json.dumps serializes tuples as arrays, which is what we
    # want - no manual conversion needed.
    return json.dumps(as_dict, indent=2, ensure_ascii=False, default=str) + "\n"


# ---------------------------------------------------------------------------
# Terminal mode (box-drawing + emoji)
# ---------------------------------------------------------------------------

# Box-drawing primitives. Defined once so the plain renderer can
# substitute ASCII equivalents without touching layout logic.
_BOX_TL = "╔"
_BOX_TR = "╗"
_BOX_BL = "╚"
_BOX_BR = "╝"
_BOX_H = "═"
_BOX_V = "║"


def _render_terminal(data: DashboardData) -> str:
    """Render the 7-section terminal view with box-drawing + emoji."""
    lines: list[str] = []
    width = 72  # inner content width (box sides not counted)

    # Title bar
    lines.append(_box_header("RDDF Dashboard", width))
    lines.append(f"{_BOX_V} project: {data.project_root}".ljust(width + 2)[: width + 2] + _BOX_V)
    lines.append(_box_separator(width))

    # Section 1: Workflow Phase
    lines.extend(_section_workflow_terminal(data, width))
    lines.append(_box_separator(width))

    # Section 2: Session
    lines.extend(_section_session_terminal(data, width))
    lines.append(_box_separator(width))

    # Section 3: Changes (includes divergence warnings inline)
    lines.extend(_section_changes_terminal(data, width))
    lines.append(_box_separator(width))

    # Section 4: Worktrees
    lines.extend(_section_worktrees_terminal(data, width))
    lines.append(_box_separator(width))

    # Section 5: Features
    lines.extend(_section_features_terminal(data, width))
    lines.append(_box_separator(width))

    # Section 6: Roadmap
    lines.extend(_section_roadmap_terminal(data, width))
    lines.append(_box_separator(width))

    # Section 7: Pending
    lines.extend(_section_pending_terminal(data, width))

    # Footer
    lines.append(_box_footer(width))

    return "\n".join(lines) + "\n"


def _box_header(title: str, width: int) -> str:
    return (
        _BOX_TL
        + _BOX_H * (width + 2)
        + _BOX_TR
        + "\n"
        + _BOX_V
        + " "
        + title.center(width)
        + " "
        + _BOX_V
    )


def _box_separator(width: int) -> str:
    return "╟" + "─" * (width + 2) + "╢"


def _box_footer(width: int) -> str:
    return _BOX_BL + _BOX_H * (width + 2) + _BOX_BR


def _content_line(text: str, width: int) -> str:
    """Wrap text into the box content area (truncate if too long)."""
    # Account for the leading space and trailing space inside the box.
    inner = width
    if len(text) > inner:
        text = text[: inner - 1] + "…"
    return _BOX_V + " " + text.ljust(inner) + " " + _BOX_V


def _section_workflow_terminal(data: DashboardData, width: int) -> list[str]:
    lines: list[str] = []
    lines.append(_content_line("1. Workflow Phase", width))
    arch = data.arch
    plan = data.plan

    # Arch status
    if arch.arch_complete_at:
        lines.append(
            _content_line(f"  ✅ Arch  complete  ({arch.arch_complete_at})", width)
        )
    else:
        lines.append(_content_line("  ⏳ Arch  not started", width))

    if arch.adr_count is not None:
        lines.append(_content_line(f"         ADRs: {arch.adr_count}", width))
    if arch.current_phase:
        lines.append(_content_line(f"         Phase: {arch.current_phase}", width))

    # Plan status
    if plan.plan_complete_at:
        lines.append(
            _content_line(f"  💼 Plan  done  ({plan.plan_complete_at})", width)
        )
        if plan.active_changes is not None:
            lines.append(
                _content_line(f"         Active changes: {plan.active_changes}", width)
            )
        if plan.committed_changes:
            lines.append(
                _content_line(
                    f"         Committed: {', '.join(plan.committed_changes)}",
                    width,
                )
            )
    elif arch.plan_started_at:
        lines.append(_content_line("  🔧 Plan  in progress", width))
    else:
        lines.append(_content_line("  ⏳ Plan  not started", width))

    # Ship status
    if plan.ship_started_at:
        lines.append(
            _content_line(f"  🔧 Ship in progress  (started {plan.ship_started_at})", width)
        )
    elif plan.plan_complete_at:
        lines.append(_content_line("  📋 Ship ready to start", width))
    else:
        lines.append(_content_line("  ⏳ Ship waiting on plan", width))

    return lines


def _section_session_terminal(data: DashboardData, width: int) -> list[str]:
    lines: list[str] = []
    lines.append(_content_line("2. Session", width))
    if not data.sessions:
        lines.append(_content_line("  (no sessions)", width))
        return lines

    current = next((s for s in data.sessions if s.is_current), None)
    if current:
        icon = _SESSION_ICON.get(current.state, "?")
        lines.append(
            _content_line(f"  {icon} current: {current.session_id}", width)
        )
        lines.append(_content_line(f"         kind: {current.kind}", width))
        if current.goal:
            lines.append(_content_line(f"         goal: {current.goal}", width))
        if current.attached_changes:
            lines.append(
                _content_line(
                    f"         changes: {', '.join(current.attached_changes)}",
                    width,
                )
            )
        if current.last_heartbeat:
            lines.append(
                _content_line(f"         heartbeat: {current.last_heartbeat}", width)
            )
    else:
        lines.append(_content_line("  (no active session)", width))

    # List other sessions (non-current) briefly
    others = [s for s in data.sessions if not s.is_current]
    if others:
        lines.append(_content_line(f"  other sessions ({len(others)}):", width))
        for s in others[:5]:
            icon = _SESSION_ICON.get(s.state, "?")
            lines.append(
                _content_line(f"    {icon} {s.session_id}  [{s.kind}/{s.state}]", width)
            )
        if len(others) > 5:
            lines.append(_content_line(f"    ... +{len(others) - 5} more", width))

    return lines


def _section_changes_terminal(data: DashboardData, width: int) -> list[str]:
    lines: list[str] = []
    lines.append(_content_line("3. Changes", width))
    if not data.changes:
        lines.append(_content_line("  (no changes tracked)", width))
    else:
        # Header row
        lines.append(
            _content_line(
                f"  {'NAME':<32} {'STATUS':<12} {'TASKS':<8} {'PLAN':<4}",
                width,
            )
        )
        active_changes = [c for c in data.changes if c.status != "archived"]
        archived_changes = [c for c in data.changes if c.status == "archived"]
        archived_changes.sort(
            key=lambda c: (c.archived_at or "", c.added_at or ""),
            reverse=True,
        )
        archived_limit = 5
        archived_shown = archived_changes[:archived_limit]
        archived_hidden = len(archived_changes) - len(archived_shown)
        for c in active_changes + archived_shown:
            icon = _STATUS_ICON.get(c.status, "?")
            tasks = (
                f"{c.tasks_done}/{c.tasks_total}"
                if c.tasks_total
                else "-"
            )
            plan = "✅" if c.plan_path else "-"
            name = c.name[:32]
            status_disp = f"{icon} {c.status}"
            lines.append(
                _content_line(
                    f"  {name:<32} {status_disp:<14} {tasks:<8} {plan:<4}",
                    width,
                )
            )
        if archived_hidden > 0:
            lines.append(
                _content_line(
                    f"  ... +{archived_hidden} archived change(s) hidden "
                    f"(showing most recent {archived_limit})",
                    width,
                )
            )

    # Divergence warnings (inline in Section 3 per task brief)
    if data.divergence_warnings:
        lines.append(_content_line("  ⚠️  divergence warnings:", width))
        for w in data.divergence_warnings:
            lines.append(_content_line(f"     - {w}", width))

    return lines


def _section_worktrees_terminal(data: DashboardData, width: int) -> list[str]:
    lines: list[str] = []
    lines.append(_content_line("4. Worktrees", width))
    if not data.worktrees:
        lines.append(_content_line("  (no worktrees)", width))
        return lines

    for w in data.worktrees:
        branch = w.branch or "-"
        change = w.change_name or "-"
        lines.append(
            _content_line(f"  • {w.path}", width)
        )
        lines.append(_content_line(f"         branch: {branch}  change: {change}", width))
    return lines


def _section_features_terminal(data: DashboardData, width: int) -> list[str]:
    lines: list[str] = []
    lines.append(_content_line("5. Features", width))
    if not data.features:
        lines.append(_content_line("  (no features)", width))
        return lines

    lines.append(
        _content_line(
            f"  {'NAME':<24} {'STATUS':<14} {'DONE':<8} {'GROUP':<6}",
            width,
        )
    )
    for f in data.features:
        icon = _FEATURE_ICON.get(f.status, "?")
        done = f"{f.archived_count}/{f.change_count}"
        lines.append(
            _content_line(
                f"  {f.name:<24} {icon} {f.status:<12} {done:<8} {f.parallel_group:<6}",
                width,
            )
        )
    return lines


def _section_roadmap_terminal(data: DashboardData, width: int) -> list[str]:
    lines: list[str] = []
    lines.append(_content_line("6. Roadmap", width))
    if data.roadmap_phase:
        lines.append(_content_line(f"  current phase: {data.roadmap_phase}", width))
    else:
        lines.append(_content_line("  current phase: (unknown)", width))

    if data.roadmap_counts:
        for phase_id, (done, total) in data.roadmap_counts.items():
            lines.append(_content_line(f"    {phase_id}: {done}/{total}", width))
    return lines


def _section_pending_terminal(data: DashboardData, width: int) -> list[str]:
    lines: list[str] = []
    lines.append(_content_line("7. Pending", width))

    # 7a: Pending suggestions
    if data.pending_suggestions > 0:
        lines.append(
            _content_line(
                f"  📋 {data.pending_suggestions} pending proposal suggestion(s)",
                width,
            )
        )
        lines.append(
            _content_line(
                f"  {'NAME':<30} {'PRI':<6} {'STATUS':<18} {'PHASE':<10}",
                width,
            )
        )
        for s in data.suggestions:
            status_col = (
                f"{_STATUS_ICON.get(s.status, '📋')} {s.status}"
            )
            lines.append(
                _content_line(
                    f"  {s.name[:30]:<30} "
                    f"{s.priority or '-':<6} "
                    f"{status_col:<18} "
                    f"{s.phase or '-':<10}",
                    width,
                )
            )
    else:
        lines.append(_content_line("  (no pending suggestions)", width))

    # 7b: Approved proposals
    lines.append(_content_line("  7b. Approved proposals", width))
    if data.approved_proposals:
        not_impl = sum(1 for r in data.approved_proposals if r.section == "approved")
        impl = sum(1 for r in data.approved_proposals if r.section == "implemented")
        summary = f"    {len(data.approved_proposals)} total"
        if not_impl:
            summary += f"  ({not_impl} not yet implemented)"
        if impl:
            summary += f"  ({impl} implemented)"
        lines.append(_content_line(summary, width))

        # Show ALL "approved" (not yet implemented) entries
        pending_rows = [r for r in data.approved_proposals if r.section == "approved"]
        if pending_rows:
            lines.append(_content_line("    not yet implemented:", width))
            for r in pending_rows:
                lines.append(
                    _content_line(
                        f"      📋 {r.name}  ({r.priority or '-'}, {r.date or '-'})",
                        width,
                    )
                )

        impl_rows = [r for r in data.approved_proposals if r.section == "implemented"]
        impl_rows.sort(key=lambda r: (r.date or "", r.name), reverse=True)
        impl_limit = 5
        impl_shown = impl_rows[:impl_limit]
        impl_hidden = len(impl_rows) - len(impl_shown)
        if impl_shown:
            lines.append(_content_line("    implemented (most recent first):", width))
            lines.append(
                _content_line(
                    f"    {'NAME':<28} {'PRI':<5} {'DATE':<11}",
                    width,
                )
            )
            for r in impl_shown:
                lines.append(
                    _content_line(
                        f"    ✅ {r.name[:27]:<28} "
                        f"{r.priority or '-':<5} "
                        f"{(r.date or '-')[:11]:<11}",
                        width,
                    )
                )
        if impl_hidden > 0:
            lines.append(
                _content_line(
                    f"    ... +{impl_hidden} implemented hidden "
                    f"(showing most recent {impl_limit})",
                    width,
                )
            )
    else:
        lines.append(_content_line("    (no approved proposals)", width))

    return lines


# ---------------------------------------------------------------------------
# Plain mode (ASCII only)
# ---------------------------------------------------------------------------

# ASCII box substitutes - keep widths consistent with terminal mode so
# automated diff checks (visual-qa style) can compare layouts cleanly.
_P_BOX_H = "-"
_P_BOX_V = "|"
_P_SEP = "+"


def _render_plain(data: DashboardData) -> str:
    """Render the 7-section view in ASCII-only / no-emoji form.

    Same content and section ordering as terminal mode, but every
    non-ASCII character is replaced with an ASCII equivalent. Used for
    CI logs and piped output where Unicode rendering is unreliable.
    """
    lines: list[str] = []
    width = 72

    # Title
    lines.append("+" + "-" * (width + 2) + "+")
    lines.append("| " + "RDDF Dashboard".center(width) + " |")
    lines.append("| " + ("project: " + data.project_root).ljust(width) + " |")
    lines.append("+" + "-" * (width + 2) + "+")

    # Section 1: Workflow Phase
    lines.append(_p_section_workflow(data, width))
    # Section 2: Session
    lines.append(_p_section_session(data, width))
    # Section 3: Changes
    lines.append(_p_section_changes(data, width))
    # Section 4: Worktrees
    lines.append(_p_section_worktrees(data, width))
    # Section 5: Features
    lines.append(_p_section_features(data, width))
    # Section 6: Roadmap
    lines.append(_p_section_roadmap(data, width))
    # Section 7: Pending
    lines.append(_p_section_pending(data, width))

    lines.append("+" + "-" * (width + 2) + "+")

    # Filter out empty sections (returns a list of strings joined by newline;
    # we keep the per-section helpers returning a single possibly-multiline
    # string for readability).
    non_empty = [ln for ln in lines if ln.strip()]
    return "\n".join(non_empty) + "\n"


def _p_line(text: str, width: int) -> str:
    inner = width
    if len(text) > inner:
        text = text[: inner - 1] + "..."
    return "| " + text.ljust(inner) + " |"


def _p_section_workflow(data: DashboardData, width: int) -> str:
    out: list[str] = []
    out.append(_p_line("1. Workflow Phase", width))
    arch = data.arch
    plan = data.plan

    if arch.arch_complete_at:
        out.append(_p_line(f"  [v] Arch  complete  ({arch.arch_complete_at})", width))
    else:
        out.append(_p_line("  [ ] Arch  not started", width))
    if arch.adr_count is not None:
        out.append(_p_line(f"         ADRs: {arch.adr_count}", width))
    if arch.current_phase:
        out.append(_p_line(f"         Phase: {arch.current_phase}", width))

    if plan.plan_complete_at:
        out.append(_p_line(f"  [$] Plan  done  ({plan.plan_complete_at})", width))
        if plan.active_changes is not None:
            out.append(_p_line(f"         Active changes: {plan.active_changes}", width))
        if plan.committed_changes:
            out.append(
                _p_line(
                    f"         Committed: {', '.join(plan.committed_changes)}",
                    width,
                )
            )
    elif arch.plan_started_at:
        out.append(_p_line("  [*] Plan  in progress", width))
    else:
        out.append(_p_line("  [ ] Plan  not started", width))

    if plan.ship_started_at:
        out.append(
            _p_line(f"  [*] Ship in progress  (started {plan.ship_started_at})", width)
        )
    elif plan.plan_complete_at:
        out.append(_p_line("  [+] Ship ready to start", width))
    else:
        out.append(_p_line("  [ ] Ship waiting on plan", width))

    return "\n".join(out)


def _p_section_session(data: DashboardData, width: int) -> str:
    out: list[str] = []
    out.append(_p_line("2. Session", width))
    if not data.sessions:
        out.append(_p_line("  (no sessions)", width))
        return "\n".join(out)

    current = next((s for s in data.sessions if s.is_current), None)
    if current:
        icon = _SESSION_ICON_PLAIN.get(current.state, "?")
        out.append(_p_line(f"  {icon} current: {current.session_id}", width))
        out.append(_p_line(f"         kind: {current.kind}", width))
        if current.goal:
            out.append(_p_line(f"         goal: {current.goal}", width))
        if current.attached_changes:
            out.append(
                _p_line(
                    f"         changes: {', '.join(current.attached_changes)}",
                    width,
                )
            )
        if current.last_heartbeat:
            out.append(_p_line(f"         heartbeat: {current.last_heartbeat}", width))
    else:
        out.append(_p_line("  (no active session)", width))

    others = [s for s in data.sessions if not s.is_current]
    if others:
        out.append(_p_line(f"  other sessions ({len(others)}):", width))
        for s in others[:5]:
            icon = _SESSION_ICON_PLAIN.get(s.state, "?")
            out.append(_p_line(f"    {icon} {s.session_id}  [{s.kind}/{s.state}]", width))
        if len(others) > 5:
            out.append(_p_line(f"    ... +{len(others) - 5} more", width))
    return "\n".join(out)


def _p_section_changes(data: DashboardData, width: int) -> str:
    out: list[str] = []
    out.append(_p_line("3. Changes", width))
    if not data.changes:
        out.append(_p_line("  (no changes tracked)", width))
    else:
        out.append(
            _p_line(
                f"  {'NAME':<32} {'STATUS':<14} {'TASKS':<8} {'PLAN':<4}",
                width,
            )
        )
        active_changes = [c for c in data.changes if c.status != "archived"]
        archived_changes = [c for c in data.changes if c.status == "archived"]
        archived_changes.sort(
            key=lambda c: (c.archived_at or "", c.added_at or ""),
            reverse=True,
        )
        archived_limit = 5
        archived_shown = archived_changes[:archived_limit]
        archived_hidden = len(archived_changes) - len(archived_shown)
        for c in active_changes + archived_shown:
            icon = _STATUS_ICON_PLAIN.get(c.status, "?")
            tasks = (
                f"{c.tasks_done}/{c.tasks_total}"
                if c.tasks_total
                else "-"
            )
            plan = "v" if c.plan_path else "-"
            name = c.name[:32]
            status_disp = f"{icon} {c.status}"
            out.append(
                _p_line(
                    f"  {name:<32} {status_disp:<14} {tasks:<8} {plan:<4}",
                    width,
                )
            )
        if archived_hidden > 0:
            out.append(
                _p_line(
                    f"  ... +{archived_hidden} archived change(s) hidden "
                    f"(showing most recent {archived_limit})",
                    width,
                )
            )

    if data.divergence_warnings:
        out.append(_p_line("  [!] divergence warnings:", width))
        for w in data.divergence_warnings:
            out.append(_p_line(f"     - {w}", width))
    return "\n".join(out)


def _p_section_worktrees(data: DashboardData, width: int) -> str:
    out: list[str] = []
    out.append(_p_line("4. Worktrees", width))
    if not data.worktrees:
        out.append(_p_line("  (no worktrees)", width))
        return "\n".join(out)
    for w in data.worktrees:
        branch = w.branch or "-"
        change = w.change_name or "-"
        out.append(_p_line(f"  - {w.path}", width))
        out.append(_p_line(f"         branch: {branch}  change: {change}", width))
    return "\n".join(out)


def _p_section_features(data: DashboardData, width: int) -> str:
    out: list[str] = []
    out.append(_p_line("5. Features", width))
    if not data.features:
        out.append(_p_line("  (no features)", width))
        return "\n".join(out)
    out.append(
        _p_line(
            f"  {'NAME':<24} {'STATUS':<14} {'DONE':<8} {'GROUP':<6}",
            width,
        )
    )
    for f in data.features:
        icon = _FEATURE_ICON_PLAIN.get(f.status, "?")
        done = f"{f.archived_count}/{f.change_count}"
        out.append(
            _p_line(
                f"  {f.name:<24} {icon} {f.status:<12} {done:<8} {f.parallel_group:<6}",
                width,
            )
        )
    return "\n".join(out)


def _p_section_roadmap(data: DashboardData, width: int) -> str:
    out: list[str] = []
    out.append(_p_line("6. Roadmap", width))
    if data.roadmap_phase:
        out.append(_p_line(f"  current phase: {data.roadmap_phase}", width))
    else:
        out.append(_p_line("  current phase: (unknown)", width))
    if data.roadmap_counts:
        for phase_id, (done, total) in data.roadmap_counts.items():
            out.append(_p_line(f"    {phase_id}: {done}/{total}", width))
    return "\n".join(out)


def _p_section_pending(data: DashboardData, width: int) -> str:
    out: list[str] = []
    out.append(_p_line("7. Pending", width))

    if data.pending_suggestions > 0:
        out.append(
            _p_line(
                f"  [+] {data.pending_suggestions} pending proposal suggestion(s)",
                width,
            )
        )
        out.append(
            _p_line(
                f"  {'NAME':<30} {'PRI':<6} {'STATUS':<18} {'PHASE':<10}",
                width,
            )
        )
        for s in data.suggestions:
            status_col = (
                f"{_STATUS_ICON_PLAIN.get(s.status, '+')} {s.status}"
            )
            out.append(
                _p_line(
                    f"  {s.name[:30]:<30} "
                    f"{s.priority or '-':<6} "
                    f"{status_col:<18} "
                    f"{s.phase or '-':<10}",
                    width,
                )
            )
    else:
        out.append(_p_line("  (no pending suggestions)", width))

    out.append(_p_line("  7b. Approved proposals", width))
    if data.approved_proposals:
        not_impl = sum(1 for r in data.approved_proposals if r.section == "approved")
        impl = sum(1 for r in data.approved_proposals if r.section == "implemented")
        summary = f"    {len(data.approved_proposals)} total"
        if not_impl:
            summary += f"  ({not_impl} not yet implemented)"
        if impl:
            summary += f"  ({impl} implemented)"
        out.append(_p_line(summary, width))

        pending_rows = [r for r in data.approved_proposals if r.section == "approved"]
        if pending_rows:
            out.append(_p_line("    not yet implemented:", width))
            for r in pending_rows:
                out.append(
                    _p_line(
                        f"      [+] {r.name}  ({r.priority or '-'}, {r.date or '-'})",
                        width,
                    )
                )

        impl_rows = [r for r in data.approved_proposals if r.section == "implemented"]
        impl_rows.sort(key=lambda r: (r.date or "", r.name), reverse=True)
        impl_limit = 5
        impl_shown = impl_rows[:impl_limit]
        impl_hidden = len(impl_rows) - len(impl_shown)
        if impl_shown:
            out.append(_p_line("    implemented (most recent first):", width))
            out.append(
                _p_line(
                    f"    {'NAME':<28} {'PRI':<5} {'DATE':<11}",
                    width,
                )
            )
            for r in impl_shown:
                out.append(
                    _p_line(
                        f"    [v] {r.name[:27]:<28} "
                        f"{r.priority or '-':<5} "
                        f"{(r.date or '-')[:11]:<11}",
                        width,
                    )
                )
        if impl_hidden > 0:
            out.append(
                _p_line(
                    f"    ... +{impl_hidden} implemented hidden "
                    f"(showing most recent {impl_limit})",
                    width,
                )
            )
    else:
        out.append(_p_line("    (no approved proposals)", width))
    return "\n".join(out)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _stdout_is_tty() -> bool:
    """Return True if stdout is a TTY. Safe to call when stdout is closed."""
    try:
        return os.isatty(sys.stdout.fileno())
    except (OSError, ValueError):
        # ValueError: stdout fileno() returned -1 (closed).
        # OSError: underlying fd inaccessible.
        return False


__all__ = ["render"]
