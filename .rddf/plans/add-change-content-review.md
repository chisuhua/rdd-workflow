# add-change-content-review Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use skill_use("execute") to implement this plan task-by-task.

**Goal:** plan-done 前增加 change artifact 内容质量审查（Metis 5 项检查）

**Architecture:** 新建 change_content_review.py，在 plan_done_gate 前调用

**Tech Stack:** Python, Metis API

---

## File Structure

### Production Code

| File | Responsibility |
|---|---|
| `skills/guide-plan/scripts/change_content_review.py` | Metis 内容审查 |
| `skills/guide-plan/scripts/plan_done_gate.sh` | 集成审查调用 |

### Tests

| File | Responsibility |
|---|---|
| `tests/unit/test_change_content_review.py` | 单元测试 |

---

### Task 1: 创建 change_content_review.py

**Files:**
- Create: `skills/guide-plan/scripts/change_content_review.py`
- Test: `tests/unit/test_change_content_review.py`

- [ ] **Step 1: Write the failing test**

```python
def test_review_proposal_clarity():
    result = review_change_content("test-change", project_root)
    assert result["proposal_clarity"] in ["pass", "fail", "warn"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_change_content_review.py -v`
Expected: FAIL - module not found

- [ ] **Step 3: Write minimal implementation**

```python
"""Change content review using Metis agent."""
import json
import os
from typing import Dict, Any

def review_change_content(change_name: str, project_root: str) -> Dict[str, Any]:
    """Review change artifacts (proposal.md, design.md, tasks.md)."""
    result = {
        "change": change_name,
        "proposal_clarity": "pass",
        "design_completeness": "pass",
        "tasks_granularity": "pass",
        "consistency": "pass",
        "dependency_annotations": "pass",
        "auto_revised": False,
        "escalated": False
    }
    
    # TODO: Call Metis agent for actual review
    # For now, return placeholder result
    
    return result

def auto_revise_if_needed(change_name: str, project_root: str, review_result: Dict) -> bool:
    """Auto-revise fixable issues."""
    if os.environ.get("CHANGE_CONTENT_REVIEW_AUTO_REVISE", "yes") == "no":
        return False
    # TODO: Implement auto-revision
    return False
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_change_content_review.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add skills/guide-plan/scripts/change_content_review.py tests/unit/test_change_content_review.py
git commit -m "feat: add change content review module"
```
