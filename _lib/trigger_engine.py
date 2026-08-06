"""TriggerEngine — flow.yaml trigger condition evaluator (ADR-0012).

Resolves a string trigger condition against a runtime context dict so that
flow.yaml can express gate-style customisations declaratively:

    trigger: always
    trigger: changes.any(security)

This milestone implements the minimum grammar needed by the ship-side
executor:

- ``"always"``               → always True (ignores context)
- ``"changes.any(<tag>)"``   → True iff any change in
                               ``context["changes"]`` has ``<tag>`` in its
                               ``tags`` list. Empty changes (or missing
                               ``changes`` key) → False.
- anything else              → False (unknown / unparseable)

The evaluator is deliberately small and side-effect free so it can be
called from anywhere — flow customiser, tribunal, dry-run preview — without
needing to plumb dependencies through.
"""
from __future__ import annotations

from typing import Any, Dict, List


class TriggerEngine:
    """Stateless evaluator for flow.yaml trigger expressions."""

    @staticmethod
    def evaluate(condition: str, context: Dict[str, Any]) -> bool:
        """Resolve ``condition`` against ``context`` and return a boolean.

        See module docstring for the supported grammar.
        """
        if not isinstance(condition, str):
            return False

        cond = condition.strip()
        if cond == "always":
            return True

        prefix = "changes.any("
        if cond.startswith(prefix) and cond.endswith(")"):
            tag = cond[len(prefix):-1].strip()
            if not tag:
                return False
            changes: List[Dict[str, Any]] = context.get("changes") or []
            for change in changes:
                tags = change.get("tags") or []
                if tag in tags:
                    return True
            return False

        return False