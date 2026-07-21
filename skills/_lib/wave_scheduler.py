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

    def detect_unblocked(self, iteration_data: dict, deps_data: Optional[dict] = None) -> list[Recommendation]:
        """Scan iteration_data for changes whose blockers have resolved.

        Args:
            iteration_data: Parsed iteration.json (v4 schema).
            deps_data: Optional parsed deps-analysis.json (v1) for
                      supplementary 'blocks' info.

        Returns:
            List of Recommendation for changes ready to advance.
            Empty list if no changes are ready or input is empty.
        """
        return []
