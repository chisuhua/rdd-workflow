"""ASCII flowchart generator — reads state vector + event log, renders progress."""
from __future__ import annotations
from skills._lib.core.state_vector import StateVector
from skills._lib.core.event_log import EventLog


PHASE_LABELS = {
    "verify_goal": "[1] Verify Goal",
    "scan_state": "[2] Scan State",
    "generate_plan": "[3] Generate Plan",
    "execute_plan": "[4] Execute Plan",
    "verify_results": "[5] Verify Results",
    "adapt": "[6] Adapt",
}


class FlowchartGenerator:
    """Generate ASCII flowchart of current loop progress."""

    def __init__(self, state: StateVector, event_log: EventLog):
        self.state = state
        self.event_log = event_log

    def render(self) -> str:
        """Render the flowchart as a multi-line ASCII string."""
        sd = self.state.to_dict()
        loop_state = sd.get("loop_state", {})
        current_phase = loop_state.get("current_phase") or "verify_goal"
        iteration = loop_state.get("iteration", 0)
        gate_status = sd.get("arch_side", {}).get("gate_status", "ok")
        errors = self.event_log.query(severity="error", limit=5)
        warnings = self.event_log.query(severity="warn", limit=5)

        lines = [
            "┌─ Loop Engine Progress ─────────────────────────┐",
            f"│ Iteration: {iteration:<35} │",
            f"│ Gate:      {gate_status:<35} │",
            f"│ Phase:     {PHASE_LABELS.get(current_phase, current_phase):<35} │",
            "│                                                 │",
            "│ Flow:                                           │",
            "│   verify_goal → scan_state → generate_plan      │",
            "│        ↓                                       │",
            "│   execute_plan → verify_results → adapt         │",
            "│        ↓                                       │",
            "│   (loop or exit)                                │",
        ]
        if errors:
            lines.append("│                                                 │")
            lines.append(f"│ Recent errors ({len(errors)}):".ljust(48) + "│")
            for e in errors[:3]:
                msg = e.message[:38]
                lines.append(f"│   ! {msg}".ljust(48) + "│")
        if warnings:
            lines.append("│                                                 │")
            lines.append(f"│ Recent warnings ({len(warnings)}):".ljust(48) + "│")
            for w in warnings[:2]:
                msg = w.message[:38]
                lines.append(f"│   ~ {msg}".ljust(48) + "│")
        lines.append("└─────────────────────────────────────────────────┘")
        return "\n".join(lines)
