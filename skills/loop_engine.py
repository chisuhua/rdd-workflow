"""LoopEngine — the AI-native execution engine for spec-workflow v2.0.

Implements 5-building-block cycle: verify_goal → scan_state → generate_plan →
execute_plan → verify_results → adapt. Safety mechanisms enforced at engine layer.
"""
from __future__ import annotations
from enum import Enum
from typing import Any, Optional
from skills._lib.state_vector import StateVector
from skills._lib.event_log import EventLog
from skills._lib.event_types import EventType, Severity, Event
from skills._lib.loop_state import LoopState
from skills._lib.config import ConfigParser


class LoopStatus(str, Enum):
    """Loop termination statuses."""
    SUCCESS = "success"
    MAX_ITERATIONS_EXCEEDED = "max_iterations_exceeded"
    MAX_RETRIES_EXCEEDED = "max_retries_exceeded"
    OSCILLATION_DETECTED = "oscillation_detected"
    CIRCUIT_BROKEN = "circuit_broken"
    ERROR = "error"


class _OscillationDetected(Exception):
    """Internal signal to break out of run() when oscillation is detected."""
    pass


class _CircuitBroken(Exception):
    """Internal signal to break out of run() when circuit breaker trips."""
    pass


class LoopEngine:
    """Main loop engine. Call .run() to execute cycle until goal or safety trigger."""

    # SAFETY_DEFAULTS are code-level fallback when config doesn't specify.
    # Config-provided values override these via ConfigParser.parse().
    SAFETY_DEFAULTS = {
        "max_iterations": 100,
        "max_retries": 3,
        "oscillation_window": 5,
        "oscillation_distinct_threshold": 2,
        "circuit_breaker_threshold": 3,
        "action_timeout_seconds": 30 * 60,
    }

    def __init__(
        self,
        state: StateVector,
        event_log: EventLog,
        config: Optional[ConfigParser] = None,
        mode: Optional[Any] = None,
    ):
        self.state = state
        self.event_log = event_log
        # CORRECT API: ConfigParser only exposes .parse(runtime_overrides) → dict
        # It does NOT have get_loop_safety() or get(). Use .parse() then .get().
        self.config = config or ConfigParser()
        cfg = self.config.parse()
        loop_cfg = cfg.get("loop", {})
        # Merge: SAFETY_DEFAULTS < loop_cfg (loop_cfg wins)
        self.safety = {
            "max_iterations": loop_cfg.get("max_iterations", self.SAFETY_DEFAULTS["max_iterations"]),
            "max_retries": loop_cfg.get("max_retries", self.SAFETY_DEFAULTS["max_retries"]),
            "oscillation_window": loop_cfg.get("oscillation_window", self.SAFETY_DEFAULTS["oscillation_window"]),
            "oscillation_distinct_threshold": loop_cfg.get("oscillation_distinct_threshold", self.SAFETY_DEFAULTS["oscillation_distinct_threshold"]),
            "circuit_breaker_threshold": loop_cfg.get("circuit_breaker_threshold", self.SAFETY_DEFAULTS["circuit_breaker_threshold"]),
            "action_timeout_seconds": loop_cfg.get("action_timeout_seconds", self.SAFETY_DEFAULTS["action_timeout_seconds"]),
        }
        self.loop_state = LoopState()

        # Mode is wired in §7. Lazy import to avoid circular dependency.
        # If the human_nodes/interaction_modes modules are not yet present,
        # default to a no-op stub (loop engine core works without them).
        self.mode = self._resolve_mode(mode, cfg)

    def _resolve_mode(self, mode: Any, cfg: dict) -> Any:
        """Resolve interaction mode — explicit param > config > default stub."""
        if mode is not None:
            return mode
        try:
            from skills._lib.human_nodes import HumanNodeRegistry
            from skills._lib.interaction_modes import make_mode
            registry = HumanNodeRegistry()
            mode_name = cfg.get("interaction", {}).get("mode", "hybrid")
            return make_mode(mode_name, registry)
        except ImportError:
            # Stub mode — interaction_modes not yet implemented
            class _StubMode:
                name = "stub"
                def should_pause(self, trigger, context):
                    return False
            return _StubMode()

    def verify_goal(self, goal_predicate: str) -> bool:
        """Evaluate goal predicate against current state vector.

        Predicate is a Python expression using dotted-path access against state dict.
        Example: "plan_side['active_change'] is None"

        Uses restricted eval (no builtins) — only the state dict is in scope.
        """
        state_dict = self.state.to_dict()
        try:
            return bool(eval(goal_predicate, {"__builtins__": {}}, state_dict))
        except Exception as e:
            self.event_log.record(
                EventType.ERROR_OCCURRED,
                Severity.ERROR,
                f"Goal predicate eval failed: {e}",
                context={"predicate": goal_predicate},
            )
            return False

    def run(self, goal_predicate: str, max_iterations: Optional[int] = None) -> LoopStatus:
        """Execute loop cycle until goal achieved or safety trigger."""
        max_iter = max_iterations or self.safety["max_iterations"]
        self.loop_state.goal = goal_predicate
        self.loop_state.iteration = 0
        self.event_log.record(
            EventType.LOOP_STARTED, Severity.INFO,
            f"Loop started with goal: {goal_predicate}",
            context={"max_iterations": max_iter, "safety": self.safety},
        )

        try:
            while self.loop_state.iteration < max_iter:
                self.loop_state.iteration += 1
                # Update state vector iteration counter (for observability)
                try:
                    self.state.update_field("loop_state.iteration", self.loop_state.iteration)
                except Exception:
                    # Schema may be locked — non-fatal
                    pass

                if self.verify_goal(goal_predicate):
                    self.event_log.record(
                        EventType.LOOP_COMPLETED, Severity.INFO,
                        f"Goal achieved at iteration {self.loop_state.iteration}",
                    )
                    return LoopStatus.SUCCESS

                # Check safety mechanisms before each block
                self._check_oscillation()
                self._check_circuit_breaker()

                # 5 building blocks
                self.scan_state()
                self.generate_plan()
                self.execute_plan()
                self.verify_results()
                self.adapt()

            self.event_log.record(
                EventType.WARNING_ISSUED, Severity.WARN,
                f"Max iterations ({max_iter}) exceeded",
            )
            return LoopStatus.MAX_ITERATIONS_EXCEEDED
        except _OscillationDetected:
            return LoopStatus.OSCILLATION_DETECTED
        except _CircuitBroken:
            return LoopStatus.CIRCUIT_BROKEN

    def _check_oscillation(self) -> None:
        """Detect oscillating loop — same few states repeatedly."""
        self.loop_state.recent_state_hashes.append(self.loop_state.snapshot_hash())
        window = self.safety["oscillation_window"]
        if len(self.loop_state.recent_state_hashes) >= window:
            recent = self.loop_state.recent_state_hashes[-window:]
            if len(set(recent)) <= self.safety["oscillation_distinct_threshold"]:
                self.event_log.record(
                    EventType.WARNING_ISSUED, Severity.WARN,
                    f"Oscillation detected: last {window} states <= {self.safety['oscillation_distinct_threshold']} distinct",
                    context={"recent_states": recent},
                )
                # Raise to terminate run loop
                raise _OscillationDetected()

    def _check_circuit_breaker(self) -> None:
        """3 consecutive failures triggers circuit break."""
        if self.loop_state.consecutive_failures >= self.safety["circuit_breaker_threshold"]:
            self.event_log.record(
                EventType.ERROR_OCCURRED, Severity.ERROR,
                f"Circuit breaker: {self.loop_state.consecutive_failures} consecutive failures",
            )
            raise _CircuitBroken()

    # ─────────────────────────────────────────────────────────────────────
    # 5 building blocks (stub implementations — wired in §7)
    # ─────────────────────────────────────────────────────────────────────

    def scan_state(self) -> None:
        """Run all detectors and populate loop_state.detections."""
        # Wired in §7 — falls through silently in §1 skeleton
        pass

    def generate_plan(self) -> None:
        """Match detectors → actions, build execution plan."""
        # Wired in §7
        pass

    def execute_plan(self) -> None:
        """Execute each action in plan."""
        # Wired in §7
        pass

    def verify_results(self) -> bool:
        """Verify execution results meet goal. Stub returns False."""
        return False

    def adapt(self) -> None:
        """Adapt strategy based on results. Stub does nothing."""
        pass