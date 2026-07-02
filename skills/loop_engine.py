"""LoopEngine — the AI-native execution engine for spec-workflow v2.0.

Implements 5-building-block cycle: verify_goal → scan_state → generate_plan →
execute_plan → verify_results → adapt. Safety mechanisms enforced at engine layer.
"""
from __future__ import annotations
from enum import Enum
from typing import Any, Optional
import ast
import operator
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


_SAFE_NODES = frozenset({
    ast.Expression, ast.Compare, ast.BoolOp, ast.BinOp,
    ast.Name, ast.Attribute, ast.Subscript, ast.Index,
    ast.Load, ast.Store, ast.Del, ast.AugLoad, ast.AugStore,
    ast.Str, ast.Num, ast.NameConstant, ast.Constant,
    ast.Tuple, ast.List, ast.Dict, ast.Set, ast.UnaryOp,
    ast.Eq, ast.NotEq, ast.Lt, ast.LtE, ast.Gt, ast.GtE,
    ast.Is, ast.IsNot, ast.In, ast.NotIn,
    ast.And, ast.Or, ast.Not,
    ast.UAdd, ast.USub, ast.Not,
    ast.Slice, ast.ExtSlice, ast.Index,
    ast.keyword,
    ast.Pass, ast.Break, ast.Continue,
})

_SAFE_OPS = {
    ast.Eq: operator.eq, ast.NotEq: operator.ne,
    ast.Lt: operator.lt, ast.LtE: operator.le,
    ast.Gt: operator.gt, ast.GtE: operator.ge,
    ast.Is: operator.is_, ast.IsNot: operator.is_not,
    ast.In: lambda a, b: a in b, ast.NotIn: lambda a, b: a not in b,
    ast.And: lambda a, b: a and b, ast.Or: lambda a, b: a or b,
    ast.Not: operator.not_,
    ast.Add: operator.add, ast.Sub: operator.sub,
    ast.UAdd: operator.pos, ast.USub: operator.neg,
}


def _safe_eval_goal(expression: str, context: dict) -> bool:
    """Evaluate a goal predicate using AST node whitelist.

    Supports patterns used by LoopEngine:
      - ``plan_side['active_change'] is None``
      - ``state.iteration < 100``
      - ``detectors[0].result == 'pass'``

    Returns False for any unparseable, unwhitelisted, or runtime-errored expression.
    """
    try:
        tree = ast.parse(expression, mode='eval')
    except SyntaxError:
        return False

    # Validate every node against the whitelist
    for node in ast.walk(tree):
        if not isinstance(node, tuple(_SAFE_NODES)):
            return False

    try:
        code = compile(tree, '<safe_eval>', 'eval')
        result = eval(code, {"__builtins__": {}}, context)
        return bool(result)
    except Exception:
        return False


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
            return _safe_eval_goal(goal_predicate, state_dict)
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

    def scan_state(self) -> None:
        """Run all detectors and populate loop_state.detections as plain dicts."""
        from skills._lib.detectors import all_detectors
        detectors = all_detectors()
        results = [d.detect(self.state.to_dict()) for d in detectors]
        self.loop_state.detections = [
            r.to_dict() if hasattr(r, "to_dict") else
            ({"type": getattr(r, "type", ""),
              "data": getattr(r, "data", {}),
              "message": getattr(r, "message", ""),
              "severity": getattr(r, "severity", "info")}
             if not isinstance(r, dict) else r)
            for r in results
        ]
        try:
            self.state.update_field("loop_state.current_phase", "scan_state")
            self.state.update_field("loop_state.iteration", self.loop_state.iteration)
        except Exception:
            pass
        self.event_log.record(
            EventType.SCAN_COMPLETED, Severity.INFO,
            f"scanned {len(results)} detectors",
            context={"count": len(results)},
        )

    def generate_plan(self) -> None:
        """Match detectors → actions. 1:1 mapping via `action_<detector_type>`."""
        from skills._lib.actions import all_actions
        action_objs = all_actions()
        action_map = {a.name: a for a in action_objs}
        plan = []
        for det in self.loop_state.detections:
            if isinstance(det, dict):
                det_type = det.get("type")
                det_data = det.get("data", {})
            else:
                det_type = getattr(det, "type", None)
                det_data = getattr(det, "data", {})
            if not det_type:
                continue
            action_name = f"action_{det_type}"
            if action_name in action_map:
                plan.append((action_map[action_name], det_data))
        self.loop_state.plan = plan
        try:
            self.state.update_field("loop_state.current_phase", "generate_plan")
        except Exception:
            pass

    def execute_plan(self) -> None:
        """Execute each action with retry-on-failure up to max_retries."""
        executed = []
        for action, params in self.loop_state.plan:
            result = None
            for attempt in range(self.safety["max_retries"]):
                try:
                    result = action.execute(params, self.event_log)
                except Exception as exc:
                    result = None
                    self.loop_state.errors.append(f"action raised: {exc}")
                    self.loop_state.consecutive_failures += 1
                    continue
                if result and getattr(result, "success", False):
                    break
                self.loop_state.consecutive_failures += 1
            else:
                if result is not None and getattr(result, "error", None):
                    self.loop_state.errors.append(result.error)
            executed.append(result)
            if result and getattr(result, "success", False):
                self.loop_state.consecutive_failures = 0

        self.loop_state.executed = [
            (r.to_dict() if hasattr(r, "to_dict") else
             {"success": getattr(r, "success", False),
              "data": getattr(r, "data", {}),
              "error": getattr(r, "error", None)}
             if r is not None else {"success": False, "error": "no result"})
            for r in executed
        ]
        try:
            self.state.update_field("loop_state.current_phase", "execute_plan")
        except Exception:
            pass

    def verify_results(self) -> bool:
        """Return True iff all executed actions succeeded and at least one ran."""
        if not self.loop_state.executed:
            return False
        successes = sum(
            1 for r in self.loop_state.executed
            if (r.get("success") if isinstance(r, dict) else getattr(r, "success", False))
        )
        return successes == len(self.loop_state.executed) and successes > 0

    def adapt(self) -> None:
        """Update phase marker to 'adapt' on the state vector."""
        try:
            self.state.update_field("loop_state.current_phase", "adapt")
        except Exception:
            pass