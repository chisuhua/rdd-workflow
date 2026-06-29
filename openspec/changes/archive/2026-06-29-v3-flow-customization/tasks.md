## Task 1: Create FlowCustomizer + TriggerEngine

**Files:**
- Create: `skills/_lib/flow_customizer.py`
- Create: `skills/_lib/trigger_engine.py`
- Create: `tests/unit/test_flow_customizer.py`
- Create: `tests/unit/test_trigger_engine.py`

- [ ] **Step 1: TDD — Write test_trigger_engine.py**

```python
"""Tests for TriggerEngine — safe condition evaluation (ADR-0012)."""
import pytest
from skills._lib.trigger_engine import TriggerEngine


def test_always_trigger():
    assert TriggerEngine.evaluate("always", {}) is True


def test_changes_any_has_security():
    ctx = {"changes": [{"name": "add-auth", "tags": ["security"]}]}
    assert TriggerEngine.evaluate("changes.any(has_security_impact)", ctx) is True


def test_changes_any_no_security():
    ctx = {"changes": [{"name": "fix-typo", "tags": ["docs"]}]}
    assert TriggerEngine.evaluate("changes.any(has_security_impact)", ctx) is False


def test_empty_changes():
    assert TriggerEngine.evaluate("changes.any(has_security_impact)", {"changes": []}) is False


def test_unknown_function_returns_false():
    assert TriggerEngine.evaluate("unknown()", {}) is False
```

- [ ] **Step 2: Run — confirm ModuleNotFoundError**

- [ ] **Step 3: Create trigger_engine.py**

```python
"""TriggerEngine — safe condition evaluation for step triggers (ADR-0012).

Restricted predicate syntax: only built-in functions, no eval.
"""
from __future__ import annotations
import re
from typing import Any, Dict


class TriggerEngine:
    """Evaluate trigger conditions using restricted syntax."""

    _BUILTIN_FUNCTIONS: Dict[str, str] = {
        "has_security_impact": "security",
    }

    @classmethod
    def evaluate(cls, condition: str, context: Dict) -> bool:
        if condition == "always":
            return True

        match = re.match(r"^changes\.any\((\w+)\)$", condition)
        if match:
            func_name = match.group(1)
            changes = context.get("changes", [])
            tag = cls._BUILTIN_FUNCTIONS.get(func_name)
            if tag:
                return any(tag in c.get("tags", []) for c in changes)
            return False

        return False
```

- [ ] **Step 4: Run trigger engine tests — verify pass**

- [ ] **Step 5: TDD — Write test_flow_customizer.py (6 tests)**

```python
"""Tests for FlowCustomizer — merge flow.yaml customizations with templates."""
import pytest
from skills._lib.flow_customizer import FlowCustomizer


def test_no_customizations_identity():
    template = {"steps": [{"id": "a"}, {"id": "b"}]}
    result = FlowCustomizer.merge(template, {"customizations": {}})
    assert len(result["steps"]) == 2


def test_insert_after():
    template = {"steps": [{"id": "a"}, {"id": "b"}]}
    flow = {"customizations": {"plan": [{"insert_after": "a", "step": {"id": "c"}}]}}
    result = FlowCustomizer.merge(template, flow, phase="plan")
    assert [s["id"] for s in result["steps"]] == ["a", "c", "b"]


def test_insert_before():
    template = {"steps": [{"id": "a"}, {"id": "b"}]}
    flow = {"customizations": {"plan": [{"insert_before": "b", "step": {"id": "c"}}]}}
    result = FlowCustomizer.merge(template, flow, phase="plan")
    assert [s["id"] for s in result["steps"]] == ["a", "c", "b"]


def test_replace_skill():
    template = {"steps": [{"id": "a", "action": "default"}]}
    flow = {"customizations": {"plan": [{"replace": "a", "overrides": {"skill": "custom"}}]}}
    result = FlowCustomizer.merge(template, flow, phase="plan")
    assert result["steps"][0]["skill"] == "custom"


def test_multiple_customizations():
    template = {"steps": [{"id": "a"}, {"id": "b"}, {"id": "c"}]}
    flow = {"customizations": {"plan": [
        {"insert_after": "a", "step": {"id": "x"}},
        {"replace": "b", "overrides": {"skill": "custom"}},
    ]}}
    result = FlowCustomizer.merge(template, flow, phase="plan")
    ids = [s["id"] for s in result["steps"]]
    assert "x" in ids
    assert result["steps"][ids.index("b")].get("skill") == "custom"


def test_unknown_phase_identity():
    template = {"steps": [{"id": "a"}]}
    flow = {"customizations": {"plan": [{"insert_after": "a", "step": {"id": "x"}}]}}
    result = FlowCustomizer.merge(template, flow, phase="ship")
    assert len(result["steps"]) == 1
```

- [ ] **Step 6: Run — confirm ModuleNotFoundError**

- [ ] **Step 7: Create flow_customizer.py**

```python
"""FlowCustomizer — merge flow.yaml customizations with phase templates (ADR-0012).

Incremental override: insert_after, insert_before, replace.
"""
from __future__ import annotations
from typing import Any, Dict, List, Optional


class FlowCustomizer:
    @staticmethod
    def merge(template: Dict, flow_config: Dict, phase: Optional[str] = None) -> Dict:
        result = {"steps": list(template.get("steps", []))}
        customizations = flow_config.get("customizations", {}).get(phase or "", [])
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
        steps = list(template["steps"])
        target_id = cust["insert_after"]
        new_step = cust["step"]
        for i, s in enumerate(steps):
            if s["id"] == target_id:
                steps.insert(i + 1, new_step)
                break
        return {"steps": steps}

    @staticmethod
    def _insert_before(template: Dict, cust: Dict) -> Dict:
        steps = list(template["steps"])
        target_id = cust["insert_before"]
        new_step = cust["step"]
        for i, s in enumerate(steps):
            if s["id"] == target_id:
                steps.insert(i, new_step)
                break
        return {"steps": steps}

    @staticmethod
    def _replace(template: Dict, cust: Dict) -> Dict:
        steps = list(template["steps"])
        target_id = cust["replace"]
        overrides = cust.get("overrides", {})
        for i, s in enumerate(steps):
            if s["id"] == target_id:
                steps[i] = {**s, **overrides}
                break
        return {"steps": steps}
```

- [ ] **Step 8: Run all flow customizer tests — verify pass**

- [ ] **Step 9: Run full unit suite**

Run: `cd /workspace/project/spec-workflow && python3 -m pytest tests/unit/ -q --tb=short`

Expected: 165 + 5 + 6 = 176 passed.

- [ ] **Step 10: Commit**

```bash
cd /workspace/project/spec-workflow && git add skills/_lib/flow_customizer.py skills/_lib/trigger_engine.py tests/unit/test_flow_customizer.py tests/unit/test_trigger_engine.py && git commit -m "feat(flow): add FlowCustomizer + TriggerEngine — ADR-0012 flow customization layer"
```

---

## Task 2: Create example flow.yaml

**Files:**
- Create: `.spec-workflow/flow.yaml.example`

- [ ] **Step 1: Create example configuration**

```yaml
# .spec-workflow/flow.yaml — 流程定制配置（示例）
# 复制此文件到 .spec-workflow/flow.yaml 并编辑
# 不配置此文件 = 使用默认阶段模板（向后兼容）
version: "2.0"

customizations:
  plan:
    # 在 generate_proposal 之后插入自定义步骤
    - insert_after: "generate_proposal"
      step:
        id: "compliance_review"
        type: "custom"
        skill: "compliance-review"
        trigger: "always"
        verification_mode: "human"

    # 用 custom-planner 替代默认 generate_proposal
    - replace: "generate_proposal"
      overrides:
        skill: "custom-planner"
        params:
          template: "detailed"

  ship:
    # 在 merge_to_main 之前插入安全审计
    - insert_before: "merge_to_main"
      step:
        id: "security_audit"
        type: "custom"
        skill: "security-review"
        trigger: "changes.any(has_security_impact)"
        on_failure: "back_to:execute_units"
```

- [ ] **Step 2: Verify YAML parseable**

- [ ] **Step 3: Commit**

```bash
cd /workspace/project/spec-workflow && git add .spec-workflow/flow.yaml.example && git commit -m "docs(flow): add example flow.yaml for ADR-0012 customization"
```

---

## Task 3: Update ADR-0012 status

**Files:**
- Modify: `docs/adr/ADR-0012-flow-customization-layer.md`
- Modify: `docs/adr/README.md`

- [ ] **Step 1: Update ADR-0012 status**

`已采纳` → `✅ 已实施`

- [ ] **Step 2: Update docs/adr/README.md**

`❌ 未实施` → `✅ 已实施`

- [ ] **Step 3: Commit**

---

## Task 4: Final verification

- [ ] **Step 1: All tests pass**
- [ ] **Step 2: openspec validate**
- [ ] **Step 3: git log clean**

---

## Self-Review

| Requirement | Task | Status |
|------------|------|--------|
| FlowCustomizer merge | T1 | ✅ insert_after/before/replace |
| TriggerEngine safe eval | T1 | ✅ restricted builtins only |
| flow.yaml example | T2 | ✅ |
| Backward compat | T1 | ✅ no customizations = identity |
| ADR status update | T3 | ✅ |
| Full test suite | T1 | ✅ 11 new tests |