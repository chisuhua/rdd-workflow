"""Three interaction modes for the loop engine: Loop, Menu, Hybrid.

ADR-0002 (spec-workflow): users choose their autonomy level per invocation.
Mode is selectable at construction time and switchable at runtime via the
`make_mode` factory or by passing a new `InteractionMode` instance to
`LoopEngine(..., mode=...)`.

Semantics
---------
- **Loop**   — fully autonomous. Skips every human-in-loop node UNLESS the
              engine is currently in an error state (then it pauses so the
              user can intervene).
- **Menu**   — fully manual. Pauses at every human-in-loop node.
- **Hybrid** (default) — auto for routine nodes, manual at the configured
              subset of `human_nodes`. Errors always pause regardless of
              whitelist membership.

The decision is centralised in `should_pause(trigger, context)` which
the loop engine consults before invoking `HumanNodeRegistry.verify`.
"""
from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Optional, Set, Dict, Any

from skills._lib.loop.human_nodes import HumanNodeRegistry, NodeTrigger


class InteractionMode(ABC):
    """Abstract base for interaction modes.

    Subclasses must:
    - set `name` (string class attribute) — used by CLI flags / config keys
    - implement `should_pause(trigger, context)` — returns True iff the
      engine should halt and surface a human-decision UI for this node.
    """

    name: str = "base"

    def __init__(self, registry: HumanNodeRegistry):
        self.registry = registry

    @abstractmethod
    def should_pause(self, trigger: NodeTrigger, context: Dict[str, Any]) -> bool:
        """Decide whether to pause for human input at this node.

        `trigger` is the current NodeTrigger the engine is about to verify.
        `context` is a free-form dict provided by the engine — the
        convention is `context["error"]` being True when the engine is in
        an error state (failed action, retry exhausted, etc.).
        """
        raise NotImplementedError


class LoopMode(InteractionMode):
    """Fully autonomous. Skips human nodes except on error."""
    name = "loop"

    def should_pause(self, trigger: NodeTrigger, context: Dict[str, Any]) -> bool:
        # Only error states warrant human interruption.
        return bool(context.get("error", False))


class MenuMode(InteractionMode):
    """Fully manual. Pauses at every decision point."""
    name = "menu"

    def should_pause(self, trigger: NodeTrigger, context: Dict[str, Any]) -> bool:
        # Always pause — the user wants to see every menu.
        return True


class HybridMode(InteractionMode):
    """Default mode. Auto for routine, manual at configured key nodes.

    The `human_nodes` whitelist is a set of node names (e.g.
    `{"arch.adr_create", "ship.archive_confirm"}`) at which the loop
    pauses for user confirmation. Errors always override the whitelist
    so the user can intervene on failures regardless of node type.
    """

    name = "hybrid"

    def __init__(
        self,
        registry: HumanNodeRegistry,
        human_nodes: Optional[Set[str]] = None,
    ):
        super().__init__(registry)
        self.human_nodes: Set[str] = set(human_nodes) if human_nodes else set()

    def should_pause(self, trigger: NodeTrigger, context: Dict[str, Any]) -> bool:
        # Errors always pause — even non-whitelisted nodes get user attention.
        if context.get("error", False):
            return True
        # Otherwise pause only at whitelisted decision points.
        return trigger.name in self.human_nodes


def make_mode(
    name: str,
    registry: HumanNodeRegistry,
    **kwargs: Any,
) -> InteractionMode:
    """Factory for interaction modes. `name` ∈ {"loop", "menu", "hybrid"}.

    Extra kwargs are forwarded to the mode constructor. `HybridMode`
    accepts `human_nodes: Set[str]`; `LoopMode` / `MenuMode` ignore extras.

    Raises:
        ValueError: if `name` is not a recognised mode.
    """
    if name == "loop":
        return LoopMode(registry)
    if name == "menu":
        return MenuMode(registry)
    if name == "hybrid":
        # Forward only the human_nodes kwarg if provided; ignore others.
        human_nodes = kwargs.get("human_nodes", set())
        if not isinstance(human_nodes, set):
            human_nodes = set(human_nodes)
        return HybridMode(registry, human_nodes=human_nodes)
    raise ValueError(f"Unknown mode: {name!r}. Expected one of: loop, menu, hybrid.")