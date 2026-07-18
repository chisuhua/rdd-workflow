"""FlowCustomizer — merge flow.yaml customizations with phase templates (ADR-0012).

The customizer takes a phase-template dict (as produced by StepPipeline from
``phase_templates.yaml``) and applies the user-declared customizations from
the project's ``flow.yaml`` for the requested phase.

Supported customization shapes:

- ``{"insert_after": "<step_id>", "step": {...}}``
    Splice the given ``step`` immediately after the named step.
- ``{"insert_before": "<step_id>", "step": {...}}``
    Splice the given ``step`` immediately before the named step.
- ``{"replace": "<step_id>", "overrides": {...}}``
    Shallow-merge ``overrides`` into the named step (preserves ``id``).

The merger is non-mutating: it always returns a fresh dict with a freshly
copied ``steps`` list. Customisations for any phase other than the one being
merged are ignored — the caller picks the phase, and we only act on that
phase's list.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional


class FlowCustomizer:
    """Stateless merger that combines flow.yaml customizations with a template."""

    @staticmethod
    def merge(template: Dict, flow_config: Dict, phase: Optional[str] = None) -> Dict:
        """Return a new template dict with ``phase``'s customizations applied.

        - ``template``     — phase-template dict (must contain ``steps`` list)
        - ``flow_config``  — parsed ``flow.yaml`` (may have ``customizations``)
        - ``phase``        — which phase's customisations to apply; ``None`` or
                             an unknown phase → identity copy
        """
        result: Dict[str, Any] = {"steps": list(template.get("steps", []))}
        # Carry other template fields through verbatim (description, etc.)
        for key, value in template.items():
            if key == "steps":
                continue
            result[key] = value

        if not phase:
            return result

        customizations = (
            flow_config.get("customizations", {}).get(phase, []) if flow_config else []
        )

        for cust in customizations:
            if "insert_after" in cust:
                result = FlowCustomizer._insert_after(result, cust)
            elif "insert_before" in cust:
                result = FlowCustomizer._insert_before(result, cust)
            elif "replace" in cust:
                result = FlowCustomizer._replace(result, cust)

        return result

    @staticmethod
    def _insert_after(template: Dict, cust: Dict) -> Dict:
        steps: List[Dict[str, Any]] = list(template["steps"])
        for i, s in enumerate(steps):
            if s["id"] == cust["insert_after"]:
                steps.insert(i + 1, cust["step"])
                break
        return {**template, "steps": steps}

    @staticmethod
    def _insert_before(template: Dict, cust: Dict) -> Dict:
        steps: List[Dict[str, Any]] = list(template["steps"])
        for i, s in enumerate(steps):
            if s["id"] == cust["insert_before"]:
                steps.insert(i, cust["step"])
                break
        return {**template, "steps": steps}

    @staticmethod
    def _replace(template: Dict, cust: Dict) -> Dict:
        steps: List[Dict[str, Any]] = list(template["steps"])
        for i, s in enumerate(steps):
            if s["id"] == cust["replace"]:
                steps[i] = {**s, **cust.get("overrides", {})}
                break
        return {**template, "steps": steps}