"""WaveScheduler - auto-detect when blocked changes become unblocked.

Consumes iteration.json (v4 schema) and optional deps-analysis.json (v1),
returns Recommendation list for changes whose blockers have resolved to
archived/completed status. Designed to be called from:
  - guide-ship Phase 3 post-archive hook
  - guide-plan / guide-ship entry hooks

Does NOT auto-invoke guide-plan/guide-ship - only emits recommendations
for the user to confirm.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class Recommendation:
    """A single recommendation to advance a change through its wave.

    Fields:
        name: The change name to advance.
        current_status: The change's current status in iteration.json
                       ('planned' or 'proposed').
        blocked_by: Name of the change that was blocking this one.
        blocker_status: Status of the blocker when it resolved
                       ('archived' or 'completed').
        wave: 'fill' for planned->propose transition,
              'ship' for proposed->guide-ship transition.
        reason: Human-readable explanation.
        source: Where the blocker info came from -
               'iteration.blocker', 'manual_deps', or 'deps.blocks'.
    """
    name: str
    current_status: str
    blocked_by: str
    blocker_status: str
    wave: str
    reason: str
    source: str


class WaveScheduler:
    """Detect when blocked changes become unblocked and emit recommendations.

    Pure-Python, no IO. Callers (bash wrappers) handle file loading.
    """

    # Statuses that count as "blocker resolved".
    _RESOLVED_STATUSES = ("archived", "completed")

    def detect_unblocked(self, iteration_data: dict, deps_data: Optional[dict] = None) -> list[Recommendation]:
        """Scan iteration_data for changes whose blockers have resolved.

        Args:
            iteration_data: Parsed iteration.json (v4 schema).
            deps_data: Optional parsed deps-analysis.json (v1) for
                      supplementary 'blocks' info. Currently unused;
                      reserved for future enhancement.

        Returns:
            List of Recommendation for changes ready to advance.
            Empty list if no changes are ready or input is empty.
        """
        if not iteration_data or not isinstance(iteration_data, dict):
            return []
        changes = iteration_data.get("changes") or []
        if not changes:
            return []
        # Index by name for blocker lookup
        by_name: dict[str, dict] = {
            c.get("name"): c for c in changes if c.get("name")
        }
        recs: list[Recommendation] = []
        for c in changes:
            name = c.get("name")
            if not name:
                continue
            status = c.get("status")
            if status == "planned":
                wave = "fill"
            elif status == "proposed":
                wave = "ship"
            else:
                continue  # archived/completed/in_worktree/review - skip

            # Resolve blocker: iteration.blocker (deps static analysis) takes
            # priority; if absent, fall back to manual_deps[0]. Track all
            # manual_deps for multi-check (ADR-0022).
            manual_deps = c.get("manual_deps") or []
            blocker_name = c.get("blocker")
            source = "iteration.blocker"
            if blocker_name:
                # iteration.blocker is set; use it as primary signal
                blocker_entry = by_name.get(blocker_name)
                if blocker_entry is None:
                    continue  # Blocker not tracked, can't confirm resolution
                blocker_status: str = blocker_entry.get("status") or ""
                if blocker_status not in self._RESOLVED_STATUSES:
                    continue  # Primary blocker unresolved
                # If manual_deps also present, ALL must be resolved
                if manual_deps:
                    unresolved_md = self._unresolved_manual_deps(manual_deps, by_name)
                    if unresolved_md:
                        continue  # Some manual_deps still blocking
            elif manual_deps:
                # No iteration.blocker but manual_deps declared - use manual_deps
                unresolved_md = self._unresolved_manual_deps(manual_deps, by_name)
                if unresolved_md:
                    continue
                # All manual_deps resolved; pick first as blocked_by for reporting
                blocker_name = manual_deps[0]
                blocker_entry = by_name.get(blocker_name)
                resolved_status = blocker_entry.get("status") if blocker_entry else None
                blocker_status = resolved_status if resolved_status in self._RESOLVED_STATUSES else "archived"
                source = "manual_deps"
            else:
                continue  # No blocker signal at all
            # Build reason
            if source == "manual_deps":
                reason = f"manual_deps {manual_deps} all resolved ({blocker_name} is {blocker_status})"
            else:
                reason = f"blocker '{blocker_name}' is {blocker_status}"

            recs.append(Recommendation(
                name=name,
                current_status=status,
                blocked_by=blocker_name,
                blocker_status=blocker_status,
                wave=wave,
                reason=reason,
                source=source,
            ))
        return recs

    def _unresolved_manual_deps(self, manual_deps: list[str], by_name: dict[str, dict]) -> list[str]:
        """Return manual_deps entries not yet in _RESOLVED_STATUSES.

        A manual_dep is 'unresolved' if its entry is missing from by_name
        OR its status is not in _RESOLVED_STATUSES.
        """
        unresolved: list[str] = []
        for dep_name in manual_deps:
            dep_entry = by_name.get(dep_name)
            if dep_entry is None:
                unresolved.append(dep_name)
                continue
            if dep_entry.get("status") not in self._RESOLVED_STATUSES:
                unresolved.append(dep_name)
        return unresolved
