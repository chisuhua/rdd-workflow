"""Loop iteration state — in-memory state passed between 5 building blocks."""
from __future__ import annotations
from dataclasses import dataclass, field


@dataclass
class LoopState:
    """Mutable in-memory state for one loop iteration."""
    goal: str = ""
    iteration: int = 0
    detections: list = field(default_factory=list)   # List[DetectionResult / dict]
    plan: list = field(default_factory=list)         # List[(Action, params)]
    executed: list = field(default_factory=list)     # List[ActionResult / dict]
    errors: list = field(default_factory=list)       # List[str]
    consecutive_failures: int = 0
    recent_state_hashes: list = field(default_factory=list)  # for oscillation detection

    def snapshot_hash(self) -> str:
        """Hashable representation of current state for oscillation detection."""
        items = []
        for d in self.detections:
            if isinstance(d, dict):
                items.append((d.get("type", ""), str(d.get("data", {}))))
            else:
                items.append((getattr(d, "type", ""), str(getattr(d, "data", {}))))
        return str(sorted(items))