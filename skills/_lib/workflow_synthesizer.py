"""Read-only workflow state synthesizer for the guide recommender.

Produces a structured ``WorkflowRecommendation`` by reading sessions.json,
handoff files, iteration.json, and git worktree state. Never raises -
all read failures surface as fallback recommendations. Never writes -
strictly read-only (no state file mutation, no openspec CLI calls).

Design contract
---------------
- **Read-only**: no file is ever written, renamed, or backed up.
  All reads delegate to ``skills._lib.state_reader`` (which itself is
  read-only) plus a single read-only ``git worktree list --porcelain``
  subprocess call.
- **Never raises**: any unexpected exception in ``synthesize()`` is
  caught and surfaced as a fallback recommendation with
  ``confidence="low"``. Callers can always safely call ``synthesize()``.
- **Deterministic**: same inputs -> same output. No time-dependent
  logic, no randomness. ``unblocked_changes`` and ``orphaned_sessions``
  are sorted for deterministic ordering.
- **Standard library only**: no new external dependencies. Uses
  ``dataclasses``, ``os``, ``subprocess``, ``typing`` from stdlib plus
  the existing ``skills._lib.state_reader`` module.

Consumed by
-----------
- ``skills/guide/SKILL.md`` (recommender entry point)

Consumes (read-only)
---------------------
- ``skills/_lib/state_reader.py`` (existing data layer)
- ``git worktree list --porcelain`` (read-only subprocess)

Decision tree (13-path priority, mirrors scan-state.sh::scan_state)
-------------------------------------------------------------------
Priority order (highest first):
    1.  arch-handoff missing                     -> guide-arch (high)
    2.  arch-handoff present, adr_count < 1      -> guide-arch (high, recover)
    3.  arch done, plan-handoff missing          -> guide-plan (high)
    4.  plan-handoff present, active_changes==0  -> guide-ship (high, cleanup)
    5.  plan-handoff present, active_changes>0   -> guide-ship (high)
    6.  worktree with incomplete tasks           -> guide-ship (medium)
    7.  detached openspec worktrees              -> guide-ship (medium)
    8.  worktree tasks all completed             -> guide-ship (medium, archive)
    9.  committed change in HEAD, no worktree    -> guide-ship (medium)
    10. no roadmap.md                            -> guide-arch (low)
    11. no openspec/changes/                     -> guide-plan (low)
    12. proposal-suggestions.md has pending      -> guide-plan (low)
    13. default                                  -> guide-ship (low)

Paths 10-13 are implicitly unreachable because earlier paths (1, 3, 4-5)
catch all those states first. The 13-path enumeration is preserved for
parity with scan-state.sh documentation but the actual decision tree
short-circuits at paths 1-9.

Confidence levels:
    - ``high``: paths 1-5 (handoff-based, deterministic)
    - ``medium``: paths 6-9 (worktree/git-based)
    - ``low``: paths 10-13 (fallback) + never-raises fallback
"""
from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from typing import Optional, Tuple

from skills._lib import state_reader


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PhaseStatus:
    """One phase (arch/plan/ship) status snapshot.

    Fields:
        phase: ``"arch"`` | ``"plan"`` | ``"ship"``
        done: ``True`` if the phase has emitted its handoff sentinel
            (or, for ship, has recorded archived changes in iteration.json)
        detail: human-readable detail string
            (e.g. ``"adr_count=5"``, ``"active_changes=3"``,
            ``"changes=4, archived=2"``, ``"no handoff"``)
    """
    phase: str
    done: bool
    detail: str


@dataclass(frozen=True)
class WorkflowRecommendation:
    """Structured recommendation output from ``synthesize()``.

    Fields:
        suggested_action: e.g. ``"guide-plan"``, ``"guide-ship"``,
            ``"guide-arch"``
        reason: one-sentence human-readable reason (Chinese, matches
            scan-state.sh output for backward compatibility)
        confidence: ``"high"`` | ``"medium"`` | ``"low"``
        phase_status: tuple of 3 ``PhaseStatus`` entries (arch, plan, ship)
        unblocked_changes: change names ready to ship, sorted
            alphabetically for determinism. Empty tuple when no
            iteration.json or no ready changes.
        active_session: ``rds_id`` bound to ``OPENCODE_SESSION_ID``
            environment variable, or ``None`` when env var is unset
            or no matching active session exists.
        orphaned_sessions: ``rds_id`` list with ``state="orphaned"``,
            sorted by ``started_at`` descending (newest first). Empty
            tuple when no orphaned sessions.
    """
    suggested_action: str
    reason: str
    confidence: str
    phase_status: Tuple[PhaseStatus, ...]
    unblocked_changes: Tuple[str, ...]
    active_session: Optional[str]
    orphaned_sessions: Tuple[str, ...]


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def synthesize(project_root: str) -> WorkflowRecommendation:
    """Read state and produce a recommendation. Never raises.

    On any unexpected exception, returns a fallback recommendation
    of ``("guide-ship", "fallback: synthesizer error", "low")`` with
    empty ``unblocked_changes`` / ``orphaned_sessions`` and ``None``
    ``active_session``.

    Args:
        project_root: absolute path to the project root (where
            ``.rddf/state/`` lives). Relative paths work but may
            confuse callers; prefer absolute.

    Returns:
        A frozen ``WorkflowRecommendation`` dataclass instance.
    """
    try:
        arch_handoff = state_reader.read_arch_handoff(project_root)
        plan_handoff = state_reader.read_plan_handoff(project_root)
        iteration = state_reader.read_iteration(project_root)
        sessions = state_reader.read_sessions(project_root)

        phase_status = _build_phase_status(arch_handoff, plan_handoff, iteration)
        unblocked = _unblocked_changes(iteration)
        active = _active_session(sessions)
        orphaned = _orphaned_sessions(sessions)

        suggested, reason, confidence = _decision_tree(
            project_root, arch_handoff, plan_handoff, iteration
        )
        return WorkflowRecommendation(
            suggested_action=suggested,
            reason=reason,
            confidence=confidence,
            phase_status=phase_status,
            unblocked_changes=unblocked,
            active_session=active,
            orphaned_sessions=orphaned,
        )
    except Exception:
        return _fallback_recommendation()


# ---------------------------------------------------------------------------
# Phase status builders
# ---------------------------------------------------------------------------


def _build_phase_status(
    arch_h: Optional[dict],
    plan_h: Optional[dict],
    iteration: Optional[dict],
) -> Tuple[PhaseStatus, ...]:
    """Build the 3-entry phase status tuple.

    Returns a tuple of 3 ``PhaseStatus`` entries (arch, plan, ship).
    Each entry has a human-readable ``detail`` string with key metrics.
    """
    # arch
    if arch_h is not None:
        arch_done = True
        arch_detail = f"adr_count={arch_h.get('adr_count', 0)}"
    else:
        arch_done = False
        arch_detail = "no handoff"

    # plan
    if plan_h is not None:
        plan_done = True
        plan_detail = f"active_changes={plan_h.get('active_changes', 0)}"
    else:
        plan_done = False
        plan_detail = "no handoff"

    # ship (best-effort from iteration)
    ship_detail = "no worktree"
    if iteration is not None and isinstance(iteration, dict):
        changes = iteration.get("changes", [])
        if isinstance(changes, list):
            archived = [
                c for c in changes
                if isinstance(c, dict) and c.get("status") == "archived"
            ]
            ship_detail = f"changes={len(changes)}, archived={len(archived)}"

    return (
        PhaseStatus("arch", arch_done, arch_detail),
        PhaseStatus("plan", plan_done, plan_detail),
        PhaseStatus("ship", False, ship_detail),
    )


# ---------------------------------------------------------------------------
# Derived recommendation fields
# ---------------------------------------------------------------------------


def _unblocked_changes(iteration: Optional[dict]) -> Tuple[str, ...]:
    """Extract change names ready to ship from iteration.json.

    A change is "unblocked" when:
        - ``status`` is ``"proposed"`` or ``"in_worktree"``
        - ``blocker`` is ``None`` or empty string

    Returns a sorted tuple of change names. Empty tuple when
    iteration is missing, invalid, or has no ready changes.
    """
    if not iteration or not isinstance(iteration, dict):
        return ()
    changes = iteration.get("changes")
    if not isinstance(changes, list):
        return ()
    ready: list = []
    for c in changes:
        if not isinstance(c, dict):
            continue
        name = c.get("name")
        if not name or not isinstance(name, str):
            continue
        if c.get("status") not in ("proposed", "in_worktree"):
            continue
        if c.get("blocker"):
            continue
        ready.append(name)
    return tuple(sorted(ready))


def _active_session(sessions: Optional[list]) -> Optional[str]:
    """Find the active session bound to ``OPENCODE_SESSION_ID``.

    Returns the ``rds_id`` of the first session with
    ``state="active"`` and ``owner_opencode_session_id`` matching the
    ``OPENCODE_SESSION_ID`` environment variable. Returns ``None``
    when the env var is unset, no sessions exist, or no match.
    """
    if not sessions:
        return None
    owner = os.environ.get("OPENCODE_SESSION_ID")
    if not owner:
        return None
    for s in sessions:
        if (
            isinstance(s, dict)
            and s.get("state") == "active"
            and s.get("owner_opencode_session_id") == owner
            and s.get("session_id")
        ):
            return s["session_id"]
    return None


def _orphaned_sessions(sessions: Optional[list]) -> Tuple[str, ...]:
    """List orphaned session rds_ids, sorted by started_at descending.

    Returns a tuple of ``rds_id`` strings for sessions with
    ``state="orphaned"``, sorted newest-first by ``started_at``.
    Empty tuple when no sessions or no orphaned sessions.
    """
    if not sessions:
        return ()
    orphaned: list = [
        s for s in sessions
        if isinstance(s, dict)
        and s.get("state") == "orphaned"
        and s.get("session_id")
    ]
    orphaned.sort(key=lambda s: str(s.get("started_at", "")), reverse=True)
    return tuple(s["session_id"] for s in orphaned)


# ---------------------------------------------------------------------------
# Worktree + git state helpers
# ---------------------------------------------------------------------------


def _list_worktrees(project_root: str) -> list:
    """List git worktrees (delegates to state_reader).

    Returns a list of dicts with keys ``path``, ``branch``,
    ``is_openspec``. Empty list on any error. Never raises.
    """
    return state_reader.list_worktrees()


def _worktree_has_incomplete_tasks(wt_path: str) -> bool:
    """Check if a worktree has any openspec change tasks.md with ``- [ ]``.

    Scans ``<wt_path>/openspec/changes/<name>/tasks.md`` for lines
    starting with ``- [ ]`` (incomplete task marker). Returns
    ``True`` on first match. Returns ``False`` when no tasks.md
    files exist or all tasks are complete. Never raises.
    """
    changes_dir = os.path.join(wt_path, "openspec", "changes")
    try:
        entries = os.listdir(changes_dir)
    except (FileNotFoundError, OSError):
        return False
    for name in entries:
        if name == "archive":
            continue
        tasks_path = os.path.join(changes_dir, name, "tasks.md")
        if not os.path.isfile(tasks_path):
            continue
        try:
            with open(tasks_path, "r", encoding="utf-8") as f:
                content = f.read()
        except (FileNotFoundError, OSError):
            continue
        # Match both "\n- [ ]" (mid-file) and "- [ ]" at file start
        if "\n- [ ]" in content or content.startswith("- [ ]"):
            return True
    return False


def _committed_change_in_head(project_root: str) -> bool:
    """Check if HEAD has a committed change (any ``.openspec.yaml``).

    Iterates ``openspec/changes/<name>/.openspec.yaml`` and uses
    ``git show HEAD:<path>`` to verify the file is committed. Returns
    ``True`` on first match. Returns ``False`` when no changes dir,
    no committed changes, or git errors. Never raises.
    """
    changes_dir = os.path.join(project_root, "openspec", "changes")
    try:
        entries = os.listdir(changes_dir)
    except (FileNotFoundError, OSError):
        return False
    for name in entries:
        if name == "archive":
            continue
        try:
            result = subprocess.run(
                ["git", "show", f"HEAD:openspec/changes/{name}/.openspec.yaml"],
                capture_output=True,
                cwd=project_root,
                timeout=5,
            )
            if result.returncode == 0:
                return True
        except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
            continue
    return False


# ---------------------------------------------------------------------------
# Decision tree
# ---------------------------------------------------------------------------


def _decision_tree(
    project_root: str,
    arch_h: Optional[dict],
    plan_h: Optional[dict],
    iteration: Optional[dict],
) -> Tuple[str, str, str]:
    """13-path priority decision tree.

    Returns a ``(suggested_action, reason, confidence)`` tuple.
    See module docstring for the full priority table.

    Paths 10-13 (no roadmap, no openspec/changes, pending proposal,
    default) are implicitly unreachable because earlier paths (1, 3,
    4-5) catch all those states first. The 13-path enumeration is
    preserved for parity with scan-state.sh documentation.
    """
    # Path 1: arch-handoff missing -> guide-arch
    if arch_h is None:
        return ("guide-arch", "无 arch-handoff -> 进入架构定义", "high")

    # Path 2: arch-handoff exists but ADR count < 1 -> guide-arch (recover)
    adr_count = arch_h.get("adr_count", 0) if isinstance(arch_h, dict) else 0
    if not isinstance(adr_count, int) or adr_count < 1:
        return (
            "guide-arch",
            "arch-done 未完成 (ADR 数量不足 -> 回到 adr-create 阶段)",
            "high",
        )

    # Path 3: arch done, plan-handoff missing -> guide-plan
    if plan_h is None:
        return ("guide-plan", "架构定义已完成 -> 进入变更生成", "high")

    # Path 4: plan-handoff exists, active_changes == 0 -> guide-ship (cleanup)
    active_changes = (
        plan_h.get("active_changes", 0) if isinstance(plan_h, dict) else 0
    )
    if not isinstance(active_changes, int):
        active_changes = 0
    if active_changes == 0:
        return (
            "guide-ship",
            "plan-handoff 残留 (无活跃 change -> 进入 ship 清理/归档)",
            "high",
        )

    # Paths 6-9: worktree + git state (only reached when plan-handoff
    # says active_changes > 0; we still check worktree state because
    # handoff may be stale).
    worktrees = _list_worktrees(project_root)
    openspec_wts = [w for w in worktrees if w.get("is_openspec")]

    # Path 6: worktree with incomplete tasks -> guide-ship
    for wt in openspec_wts:
        wt_path = wt.get("path")
        if wt_path and _worktree_has_incomplete_tasks(wt_path):
            return (
                "guide-ship",
                "worktree 存在,任务未完成 -> 继续执行",
                "medium",
            )

    # Path 7 / 8: detached openspec worktrees (with or without complete tasks)
    if openspec_wts:
        return (
            "guide-ship",
            f"{len(openspec_wts)} 个 worktree 在跑（可能在分离终端）",
            "medium",
        )

    # Path 9: committed change in HEAD, no worktree -> guide-ship
    if _committed_change_in_head(project_root):
        return ("guide-ship", "有已 commit 的 change 待建 worktree", "medium")

    # Path 5 (default for this branch): plan-handoff exists,
    # active_changes > 0, no worktree activity -> guide-ship
    return ("guide-ship", "变更生成已完成 -> 进入变更执行", "high")


# ---------------------------------------------------------------------------
# Fallback
# ---------------------------------------------------------------------------


def _fallback_recommendation() -> WorkflowRecommendation:
    """Build the never-raises fallback recommendation.

    Used when ``synthesize()`` catches an unexpected exception. The
    fallback always points to ``guide-ship`` with ``confidence="low"``
    so the recommender still produces output (and ``scan-state.sh``
    fallback in ``guide.md`` will further refine it).
    """
    return WorkflowRecommendation(
        suggested_action="guide-ship",
        reason="fallback: synthesizer error",
        confidence="low",
        phase_status=(
            PhaseStatus("arch", False, "unknown"),
            PhaseStatus("plan", False, "unknown"),
            PhaseStatus("ship", False, "unknown"),
        ),
        unblocked_changes=(),
        active_session=None,
        orphaned_sessions=(),
    )
