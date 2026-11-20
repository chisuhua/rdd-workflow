"""Dashboard package - data collection and rendering for the ``rddf dashboard`` CLI.

This package is a pure library consumed by ``skills._lib.cli.dashboard_cmd``
(and any other caller that wants a unified view of rdd-workflow project
state). It is NOT standalone executable - there is no ``__main__.py`` here
by design (see ``docs/superpowers/specs/2026-07-20-dashboard-design.md``
§4.3: "dashboard/ is a pure library").

Layering:

    state_reader.py (Task 1 - 8 read-only functions)
            ^
            |  imports
            |
    dashboard/__init__.py  (dataclasses + collect() -> DashboardData)
            ^
            |  imports
            |
    dashboard/renderer.py  (render(data, mode) -> str)

``collect()`` calls the 8 state_reader functions and assembles a
``DashboardData`` dataclass instance. It also computes
``divergence_warnings`` by cross-checking disk changes against iteration.json
entries (e.g. iteration lists a change as "proposed" but its directory under
``openspec/changes/`` has been deleted, or a directory exists but iteration
has no record of it).

``render()`` formats a ``DashboardData`` into one of three modes:
``terminal`` (box-drawing + emoji, default when stdout is a TTY),
``json`` (via ``dataclasses.asdict``), and ``plain`` (ASCII only, no emoji,
no box chars - for CI logs and piped output).

Emoji mapping (per task brief):
    ✅  complete / done / archived
    🔧  active / in-worktree
    📋  planned / proposed
    💼  committed (plan-done)
    ✔  done (generic)
    📦  archived
    📍  current session
"""
from __future__ import annotations

from dataclasses import dataclass, field
import os
import re
from typing import Optional

from skills._lib.state_reader import (
    list_change_dirs,
    list_worktrees,
    read_arch_handoff,
    read_iteration,
    read_plan_handoff,
    read_improvement_entries,
    read_roadmap_state,
    read_sessions,
)

from _lib.dashboard.improvement_status import classify_improvement_status


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass
class ArchInfo:
    """Summary of the arch handoff (``.rddf/state/.arch-handoff.json``).

    All fields are ``None`` when arch has not been completed yet (file
    missing or unreadable). ``collect()`` never raises on a missing
    handoff - it just produces an ``ArchInfo()`` with all-None fields so
    the renderer can show "N/A" cleanly.
    """

    arch_complete_at: Optional[str] = None
    adr_count: Optional[int] = None
    roadmap_exists: Optional[bool] = None
    current_phase: Optional[str] = None
    plan_started_at: Optional[str] = None
    adr_dir: Optional[str] = None
    roadmap_path: Optional[str] = None
    architecture_dir: Optional[str] = None
    adr_pattern: Optional[str] = None


@dataclass
class PlanInfo:
    """Summary of the plan handoff (``.rddf/state/.plan-handoff.json``)."""

    plan_complete_at: Optional[str] = None
    committed_changes: list[str] = field(default_factory=list)
    active_changes: Optional[int] = None
    ship_started_at: Optional[str] = None


@dataclass
class ChangeEntry:
    """One row in the Changes section of the dashboard.

    Mirrors the subset of iteration.json change fields needed for
    rendering. ``tasks_done``/``tasks_total`` default to 0 (older
    iteration entries may not track tasks). ``verification`` is an
    independent object introduced in iteration v7 (per
    fix-rdd-verifier-lifecycle-dashboard); missing entries are
    treated as ``legacy`` for archived changes and ``unknown`` for
    active changes.
    """

    name: str
    status: str
    phase: Optional[str] = None
    category: Optional[str] = None
    priority: Optional[str] = None
    tasks_done: int = 0
    tasks_total: int = 0
    plan_path: Optional[str] = None
    blocker: Optional[str] = None
    worktree_path: Optional[str] = None
    added_at: Optional[str] = None
    archived_at: Optional[str] = None
    verification: Optional[dict] = None

    @property
    def verification_state(self) -> str:
        """Derived verification state for rendering.

        Priority:
          1. explicit verification.state when present
          2. ``legacy`` for archived changes (never fabricate passed)
          3. ``unknown`` for active changes without verification data
        """
        if self.verification:
            state = self.verification.get("state")
            if state:
                return state
        if self.status in ("archived", "archived_partial"):
            return "legacy"
        return "unknown"

    @property
    def archive_ready(self) -> bool:
        """True only when verification.state is passed/bypassed and archive_ready=true."""
        if not self.verification:
            return False
        state = self.verification.get("state")
        return state in ("passed", "bypassed") and bool(self.verification.get("archive_ready"))


@dataclass
class SessionEntry:
    """One row in the Sessions section."""

    session_id: str
    kind: str
    state: str
    owner_opencode_session_id: Optional[str] = None
    goal: Optional[str] = None
    started_at: Optional[str] = None
    last_heartbeat: Optional[str] = None
    attached_changes: list[str] = field(default_factory=list)
    is_current: bool = False


@dataclass
class WorktreeEntry:
    """One row in the Worktrees section.

    ``list_worktrees()`` in state_reader returns this shape directly;
    we re-declare it here so the dashboard package is self-documenting
    and so renderers can rely on the dataclass type.
    """

    path: str
    branch: Optional[str] = None
    head: Optional[str] = None
    bare: bool = False
    change_name: Optional[str] = None  # derived from branch (openspec/<name>)


@dataclass
class FeatureSummary:
    """One row in the Features section.

    Derived from iteration.json's ``feature_view`` block. A feature is
    a group of related changes (see ADR-0020 / feature_view_schema.json).
    """

    name: str
    status: str
    change_count: int = 0
    archived_count: int = 0
    depends_on: list[str] = field(default_factory=list)
    blocks: list[str] = field(default_factory=list)
    parallel_group: int = 0
    conflicts_with: list[str] = field(default_factory=list)
    rollup_basis: Optional[str] = None


@dataclass
class SuggestionEntry:
    """One row in the Pending (proposal suggestions) section of the dashboard.

    Mirrors the fields from improvement-suggestions.md entries that are
    relevant for dashboard display. The full ``description`` field is
    omitted because it is too long for a table row.
    """

    name: str
    priority: Optional[str] = None
    source: Optional[str] = None
    status: str = "pending"
    phase: Optional[str] = None
    category: Optional[str] = None
    effort: Optional[str] = None


@dataclass
class ApprovedProposalEntry:
    """One row in the Approved section of the dashboard.

    Mirrors a parsed ``improvement-approved.md`` table row. ``section`` is
    ``"approved"`` when the row lives under ``## 已批准提案`` (尚未
    实施) or ``"implemented"`` when it lives under ``## 已实施``.
    """

    name: str
    priority: Optional[str] = None
    date: Optional[str] = None
    section: str = "approved"


@dataclass
class DashboardData:
    """Top-level container passed to ``render()``.

    Every section's data is a separate field so renderers and tests can
    inspect partial state. ``divergence_warnings`` is populated by
    ``collect()`` when disk changes and iteration.json disagree.
    """

    project_root: str
    arch: ArchInfo = field(default_factory=ArchInfo)
    plan: PlanInfo = field(default_factory=PlanInfo)
    changes: list[ChangeEntry] = field(default_factory=list)
    sessions: list[SessionEntry] = field(default_factory=list)
    worktrees: list[WorktreeEntry] = field(default_factory=list)
    features: list[FeatureSummary] = field(default_factory=list)
    roadmap_phase: Optional[str] = None
    roadmap_counts: dict[str, tuple[int, int]] = field(default_factory=dict)
    pending_suggestions: int = 0
    suggestions: list[SuggestionEntry] = field(default_factory=list)
    approved_proposals: list[ApprovedProposalEntry] = field(default_factory=list)
    divergence_warnings: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# collect()
# ---------------------------------------------------------------------------


def collect(project_root: str) -> DashboardData:
    """Collect dashboard state by calling the 8 state_reader functions.

    This function is read-only: it never writes to any state file. It
    is also fault-tolerant: if any individual state_reader function
    raises (corrupt JSON, permission denied, subprocess timeout, ...),
    the corresponding section of the returned ``DashboardData`` is left
    at its empty default and other sections render normally. This
    matches the spec's error-handling table (§5: "Any individual file
    failure -> Other sections render normally").

    Divergence detection:
        1. ``list_change_dirs(project_root)`` returns change directories
           on disk (non-archive, under ``openspec/changes/``).
        2. ``read_iteration(project_root)`` returns the in-memory change
           list (each entry has a ``name`` and ``status``).
        3. If iteration lists a change as ``proposed``/``in_worktree``/
           ``planned`` but its directory is missing on disk, append a
           warning.
        4. If a directory exists on disk but iteration has no record of
           it (no entry with that name), append a warning. We skip this
           for changes listed in ``plan.committed_changes`` - those may
           not have been picked up by iteration hooks yet (small race
           window after plan-done).

    Args:
        project_root: Absolute path to the git repo root (or worktree
            root - state_reader handles worktree-safe resolution).

    Returns:
        A populated ``DashboardData`` instance. Always returns; never
        raises.
    """
    data = DashboardData(project_root=project_root)

    # ---- Section 1: Arch handoff ----
    try:
        arch = read_arch_handoff(project_root)
    except Exception:
        arch = None
    if arch:
        data.arch = ArchInfo(
            arch_complete_at=arch.get("arch_complete_at"),
            adr_count=arch.get("adr_count"),
            roadmap_exists=arch.get("roadmap_exists"),
            current_phase=arch.get("current_phase"),
            plan_started_at=arch.get("plan_started_at"),
            adr_dir=arch.get("adr_dir"),
            roadmap_path=arch.get("roadmap_path"),
            architecture_dir=arch.get("architecture_dir"),
            adr_pattern=arch.get("adr_pattern"),
        )

    # ---- Section 1 (cont.): Plan handoff ----
    try:
        plan = read_plan_handoff(project_root)
    except Exception:
        plan = None
    if plan:
        data.plan = PlanInfo(
            plan_complete_at=plan.get("plan_complete_at"),
            committed_changes=list(plan.get("committed_changes") or []),
            active_changes=plan.get("active_changes"),
            ship_started_at=plan.get("ship_started_at"),
        )

    # ---- Section 3: Changes (from iteration.json) ----
    try:
        iter_data = read_iteration(project_root)
    except Exception:
        iter_data = None
    iter_names: set[str] = set()
    if iter_data:
        for c in iter_data.get("changes", []):
            name = c.get("name")
            if not name:
                continue
            iter_names.add(name)
            data.changes.append(
                ChangeEntry(
                    name=name,
                    status=c.get("status", "unknown"),
                    phase=c.get("phase"),
                    category=c.get("category"),
                    priority=c.get("priority"),
                    tasks_done=int(c.get("tasks_done") or 0),
                    tasks_total=int(c.get("tasks_total") or 0),
                    plan_path=c.get("plan_path"),
                    blocker=c.get("blocker"),
                    worktree_path=c.get("worktree_path"),
                    added_at=c.get("added_at"),
                    archived_at=c.get("archived_at"),
                    verification=c.get("verification"),
                )
            )

    # ---- Section 2: Sessions (mark current) ----
    try:
        sessions = read_sessions(project_root)
    except Exception:
        sessions = None
    if sessions:
        owner_id = os.environ.get("OPENCODE_SESSION_ID")
        current_id = None
        if owner_id:
            owned = [
                s for s in sessions
                if s.get("owner_opencode_session_id") == owner_id
                and s.get("state") != "abandoned"
            ]
            owned.sort(key=lambda s: s.get("started_at") or "", reverse=True)
            if owned:
                current_id = owned[0].get("session_id")
        if current_id is None:
            active = [s for s in sessions if s.get("state") == "active"]
            active.sort(key=lambda s: s.get("started_at") or "", reverse=True)
            current_id = active[0].get("session_id") if active else None
        for s in sessions:
            data.sessions.append(
                SessionEntry(
                    session_id=s.get("session_id", "?"),
                    kind=s.get("kind", "?"),
                    state=s.get("state", "?"),
                    owner_opencode_session_id=s.get("owner_opencode_session_id"),
                    goal=_goal_to_str(s.get("goal")),
                    started_at=s.get("started_at"),
                    last_heartbeat=s.get("last_heartbeat"),
                    attached_changes=list(s.get("attached_changes") or []),
                    is_current=(s.get("session_id") == current_id),
                )
            )

    # ---- Section 4: Worktrees (from git) ----
    try:
        wts = list_worktrees()
    except Exception:
        wts = []
    for w in wts:
        # state_reader returns branch as a full ref ("refs/heads/openspec/<name>");
        # strip to a short display name and derive change_name when it's
        # an openspec worktree branch.
        full_branch = w.get("branch")
        change_name: Optional[str] = None
        short_branch = full_branch
        if short_branch and short_branch.startswith("refs/heads/"):
            short_branch = short_branch[len("refs/heads/"):]
            if short_branch.startswith("openspec/"):
                change_name = short_branch[len("openspec/"):]
        data.worktrees.append(
            WorktreeEntry(
                path=w.get("path") or "?",
                branch=short_branch,
                head=w.get("head"),
                bare=bool(w.get("bare", False)),
                change_name=change_name,
            )
        )

    # ---- Section 5: Features (from iteration.feature_view) ----
    if iter_data:
        fv = iter_data.get("feature_view") or {}
        for fname, fdata in (fv.get("features") or {}).items():
            data.features.append(
                FeatureSummary(
                    name=fdata.get("name", fname),
                    status=fdata.get("status", "unknown"),
                    change_count=int(fdata.get("change_count") or 0),
                    archived_count=int(fdata.get("archived_count") or 0),
                    depends_on=list(fdata.get("depends_on") or []),
                    blocks=list(fdata.get("blocks") or []),
                    parallel_group=int(fdata.get("parallel_group") or 0),
                    conflicts_with=list(fdata.get("conflicts_with") or []),
                    rollup_basis=fdata.get("rollup_basis"),
                )
            )

    # ---- Section 6: Roadmap (from roadmap-state.json) ----
    try:
        rstate = read_roadmap_state(project_root)
    except Exception:
        rstate = None
    if rstate:
        data.roadmap_phase = rstate.get("current_phase")
        counts: dict[str, tuple[int, int]] = {}
        for phase_id, phase_data in (rstate.get("phases") or {}).items():
            total = sum(
                len(c.get("changes", []))
                for c in (phase_data.get("categories") or {}).values()
            )
            done = sum(
                len(c.get("completed_changes", []))
                for c in (phase_data.get("categories") or {}).values()
            )
            counts[phase_id] = (done, total)
        data.roadmap_counts = counts
    elif data.arch.current_phase:
        # Fallback: arch handoff's current_phase when roadmap-state.json
        # is absent (common in projects that never ran `roadmap init`).
        data.roadmap_phase = data.arch.current_phase

    # ---- Section 7: Pending (.rddf/improvements/ + improvement-approved.md + archive bypass) ----
    # Shared implementation: `collect_pending()` is the single reader of the
    # improvement truth source. `rddf status` Mode A consumes the same
    # function (see _lib/cli/status_cmd.py), so the two views cannot drift.
    try:
        snapshot = collect_pending(project_root)
        data.suggestions.extend(snapshot.suggestions)
        data.approved_proposals.extend(snapshot.approved_proposals)
        data.pending_suggestions = len(data.suggestions)
    except Exception:
        pass

    # ---- Divergence detection ----
    try:
        disk_changes = set(list_change_dirs(project_root))
    except Exception:
        disk_changes = set()

    # 1. iteration has a non-terminal entry but disk dir is gone
    terminal_statuses = {"archived"}
    for c in data.changes:
        if c.status in terminal_statuses:
            continue
        if c.name and c.name not in disk_changes:
            data.divergence_warnings.append(
                f"iteration.json lists '{c.name}' as {c.status!r} "
                f"but its directory is missing from openspec/changes/"
            )

    # 2. disk dir exists but iteration has no record of it
    committed = set(data.plan.committed_changes)
    for name in disk_changes:
        if name in iter_names:
            continue
        if name in committed:
            # plan-done just landed; iteration hook may not have fired
            # yet - this is a known small race, not a real divergence.
            continue
        data.divergence_warnings.append(
            f"directory openspec/changes/{name}/ exists on disk "
            f"but iteration.json has no entry for it"
        )

    # 3. improvement-approved.md "approved" section has matching archive/<date>-name/
    # but the entry was not moved to "implemented" section. This drift was
    # historically caused by sweep_implemented_proposals not being wired into
    # the archive flow (fix-proposal-approved-sync, P0 2026-08-21).
    archive_dirs = []
    archive_dir = os.path.join(project_root, "openspec/changes/archive")
    if os.path.isdir(archive_dir):
        for entry in os.listdir(archive_dir):
            m = re.match(r"\d{4}-\d{2}-\d{2}-(.+)", entry)
            if m:
                archive_dirs.append(m.group(1))
    archive_names = set(archive_dirs)
    for row in data.approved_proposals:
        if row.section == "approved" and row.name in archive_names:
            data.divergence_warnings.append(
                f"improvement-approved.md lists '{row.name}' as approved "
                f"but openspec/changes/archive/ shows it archived "
                f"(re-run sweep_implemented_proposals to fix)"
            )

    return data


def _goal_to_str(goal: object) -> Optional[str]:
    """Normalize a session goal field to a string.

    The sessions.json schema allows ``goal`` to be either a structured
    dict (``{intent, subject, expected_outcome}``) or - in legacy /
    hand-edited files - a plain string. The dashboard just needs a
    one-line summary, so we render structured goals as
    ``"<intent>: <subject>"`` and pass strings through unchanged.
    """
    if goal is None:
        return None
    if isinstance(goal, str):
        return goal
    if isinstance(goal, dict):
        intent = goal.get("intent")
        subject = goal.get("subject")
        if intent and subject:
            return f"{intent}: {subject}"
        if subject:
            return str(subject)
        if intent:
            return str(intent)
        # Empty dict - fall through to None
    return None


__all__ = [
    # dataclasses
    "ArchInfo",
    "PlanInfo",
    "ChangeEntry",
    "SessionEntry",
    "WorktreeEntry",
    "FeatureSummary",
    "SuggestionEntry",
    "ApprovedProposalEntry",
    "DashboardData",
    "PendingSnapshot",
    # public API
    "collect",
    "collect_pending",
    # NOTE: ``render`` is intentionally NOT re-exported here to keep the
    # data-collection layer decoupled from the rendering layer. Callers
    # that want to render should
    # ``from skills._lib.dashboard.renderer import render``.
]


# ---------------------------------------------------------------------------
# Shared "改进提案状态" collector (single implementation)
# ---------------------------------------------------------------------------


@dataclass
class PendingSnapshot:
    """改进提案状态的采集结果（纯磁盘读）。

    Attributes:
        suggestions: 非终态、未 approved、未归档的改进提案（待办池）。
        approved_proposals: ``improvement-approved.md`` 中的已批准提案。
        errors: 读不动 / 格式损坏的 improvement 文件（逐条降级，不炸全表）。
    """

    suggestions: list[SuggestionEntry] = field(default_factory=list)
    approved_proposals: list[ApprovedProposalEntry] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


def _archived_change_names(project_root: str) -> set[str]:
    """Names of changes already archived under ``openspec/changes/archive/``."""
    archive_dir = os.path.join(project_root, "openspec", "changes", "archive")
    names: set[str] = set()
    if not os.path.isdir(archive_dir):
        return names
    try:
        entries = os.listdir(archive_dir)
    except OSError:
        return names
    for entry in entries:
        m = re.match(r"\d{4}-\d{2}-\d{2}-(.+)", entry)
        if m:
            names.add(m.group(1))
    return names


def collect_pending(project_root: str) -> PendingSnapshot:
    """收集改进提案状态（纯磁盘读，**无 iteration.json 依赖**）。

    数据源：
      - ``.rddf/improvements/*.md`` 的 front-matter（``状态`` / ``优先级`` /
        ``阶段`` / ``分类``，中英别名由 ``read_improvement_entries`` 归一）
      - ``improvement-approved.md``（已批准提案）
      - ``openspec/changes/archive/<date>-<name>/``（已归档 ⇒ 不再是待办）

    与 dashboard Section 7 的原实现等价，差异有二：
      1. **逐条容错**：单个 improvement 文件的 front-matter 损坏（例如
         ``状态`` 解析成非字符串）只降级该行并记入 ``errors``，不再让
         ``except Exception: pass`` 把整张表静默变空。
      2. **显式错误面**：``errors`` 非空时调用方应提示用户（status 是首屏
         默认命令，静默比 dashboard 危险）。
    """
    snap = PendingSnapshot()

    try:
        from skills._lib.parse_approved import parse_approved_proposals_detailed

        approved_rows = parse_approved_proposals_detailed(
            os.path.join(project_root, "improvement-approved.md")
        )
    except Exception:
        approved_rows = []
    approved = {row.name for row in approved_rows}
    for row in approved_rows:
        snap.approved_proposals.append(
            ApprovedProposalEntry(
                name=row.name,
                priority=row.priority,
                date=row.date,
                section=row.section,
            )
        )

    try:
        improvement_entries = read_improvement_entries(project_root)
    except Exception as exc:
        snap.errors.append(f"read_improvement_entries failed: {exc}")
        improvement_entries = []

    archived_names = _archived_change_names(project_root)

    for entry in improvement_entries:
        name = entry.get("name", "?")
        if name in approved or name in archived_names:
            continue
        try:
            terminal, label = classify_improvement_status(entry.get("status") or "")
        except Exception as exc:
            # Per-entry degradation: a single malformed front-matter must
            # not blank the whole table (the old `except Exception: pass`
            # around the whole section did exactly that).
            snap.errors.append(f"{name}: {exc}")
            continue
        if terminal:
            continue
        snap.suggestions.append(
            SuggestionEntry(
                name=name,
                priority=entry.get("priority") or entry.get("优先级"),
                source=entry.get("source") or entry.get("来源"),
                status=label,
                phase=entry.get("phase") or entry.get("阶段"),
                category=entry.get("category") or entry.get("分类"),
                effort=entry.get("effort"),
            )
        )

    return snap
