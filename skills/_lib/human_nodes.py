"""Human-in-Loop node registry with 3 verification modes.

Seven built-in node types cover v2.0 workflow decision points:
- `arch.*` — architecture phase (ADR create, roadmap define)
- `plan.*` — planning phase (change select, propose confirm)
- `ship.*` — shipping phase (archive confirm, cleanup confirm, execute error)

Each node is verified via one of three modes:
- `HUMAN`       — caller is expected to display UI/menu and collect input.
- `MULTI_MODEL` — Tribunal (v2-advanced-features). Not yet implemented;
                  invocation raises `MultiModelUnavailableError`.
- `SCRIPT`      — runs an external command and treats exit code as pass/fail.

The script-mode dependency on `skills._lib.actions.run_subprocess` is
imported lazily inside `HumanNodeRegistry.verify()` so this module loads
even before the `actions` module ships. Tests inject a stub via
`monkeypatch.setitem(sys.modules, "skills._lib.actions", stub)` if needed.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Any, Dict, List, Set, Tuple


class VerificationMode(str, Enum):
    """How a human-in-loop node's verification is performed."""
    HUMAN = "human"
    MULTI_MODEL = "multi_model"
    SCRIPT = "script"


class MultiModelUnavailableError(NotImplementedError):
    """Raised when multi_model verification is requested before v2-advanced-features ships.

    Inherits from `NotImplementedError` so callers catching either class work,
    but the specific subclass lets callers distinguish "multi_model not yet
    available" from generic NotImplementedError raised by unimplemented methods.
    """
    pass


@dataclass
class NodeTrigger:
    """A human-in-loop node invocation."""
    name: str
    mode: VerificationMode
    params: Dict[str, Any] = field(default_factory=dict)


@dataclass
class VerificationResult:
    """Outcome of a verification invocation."""
    success: bool
    data: Dict[str, Any] = field(default_factory=dict)
    message: str = ""


# Built-in node definitions: name → required verification mode.
# Sources: openspec/changes/v2-loop-engine/specs/interaction-modes/spec.md
BUILTIN_NODE_DEFS: List[Tuple[str, VerificationMode]] = [
    ("arch.adr_create", VerificationMode.HUMAN),
    ("arch.roadmap_define", VerificationMode.HUMAN),
    ("plan.change_select", VerificationMode.HUMAN),
    ("plan.propose_confirm", VerificationMode.HUMAN),
    ("ship.archive_confirm", VerificationMode.HUMAN),
    ("ship.cleanup_confirm", VerificationMode.SCRIPT),
    ("ship.execute_error", VerificationMode.HUMAN),
]


class HumanNodeRegistry:
    """Registry of human-in-loop nodes with verification dispatch.

    Holds the canonical mapping of node name → verification mode for the
    7 built-in node types, and exposes a single `verify(trigger)` entry
    point that dispatches to the appropriate verification backend.

    HUMAN mode is intentionally a stub that returns success=True — actual
    UI/menu presentation is the caller's responsibility (e.g., the opencode
    host surfaces a confirmation dialog). The loop engine treats success
    as "user confirmed" until a richer UI integration is implemented.
    """

    _MULTI_MODEL_MESSAGE = (
        "multi_model verification requires v2-advanced-features (Tribunal). "
        "Not yet implemented."
    )

    def __init__(self, nodes: Optional[Dict[str, VerificationMode]] = None):
        # Allow injection (used by tests / future plugin loaders); default to built-ins.
        if nodes is None:
            nodes = {name: mode for name, mode in BUILTIN_NODE_DEFS}
        self._nodes: Dict[str, VerificationMode] = dict(nodes)

    # ── Introspection ────────────────────────────────────────────────────

    def list_nodes(self) -> List[NodeTrigger]:
        """Return all known nodes as NodeTrigger stubs (params empty by default)."""
        return [NodeTrigger(name=n, mode=m, params={}) for n, m in self._nodes.items()]

    def mode_for(self, name: str) -> Optional[VerificationMode]:
        """Return the verification mode configured for `name`, or None if unknown."""
        return self._nodes.get(name)

    # ── Dispatch ─────────────────────────────────────────────────────────

    def verify(self, trigger: NodeTrigger) -> VerificationResult:
        """Dispatch verification according to `trigger.mode`.

        - `MULTI_MODEL`: raises `MultiModelUnavailableError` (Tribunal not yet shipped).
        - `SCRIPT`: runs `trigger.params["command"]` and uses exit code.
        - `HUMAN`: returns a sentinel success result — caller renders UI.

        Lazy-imports `run_subprocess` from `skills._lib.actions` so this module
        is importable before that module exists.
        """
        if trigger.mode == VerificationMode.MULTI_MODEL:
            raise MultiModelUnavailableError(self._MULTI_MODEL_MESSAGE)

        if trigger.mode == VerificationMode.SCRIPT:
            return self._verify_script(trigger)

        # HUMAN mode — caller handles UI; stub returns success sentinel.
        return VerificationResult(
            success=True,
            data={"mode": "human", "node": trigger.name},
            message="human input required (caller handles UI)",
        )

    # ── Internals ────────────────────────────────────────────────────────

    def _verify_script(self, trigger: NodeTrigger) -> VerificationResult:
        """Execute the configured command and treat exit code as pass/fail."""
        from skills._lib.actions import run_subprocess  # lazy import (parallel-agent safety)

        cmd = trigger.params.get("command")
        if not cmd:
            return VerificationResult(
                success=False,
                data={},
                message="no command configured for script verification",
            )
        # Accept both list (preferred) and string commands.
        argv = cmd if isinstance(cmd, list) else str(cmd).split()
        timeout = int(trigger.params.get("timeout_seconds", 300))
        result = run_subprocess(argv, timeout_seconds=timeout)
        returncode = result.data.get("returncode", "?") if isinstance(result.data, dict) else "?"
        return VerificationResult(
            success=result.success,
            data=result.data if isinstance(result.data, dict) else {"raw": result.data},
            message=f"script exit: {returncode}",
        )