# add-proposal-deps-and-features Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use skill_use("execute") to implement this plan task-by-task.

**Goal:** 提案级依赖和特性元数据支持（范围已缩小：仅补齐元数据解析和拓扑排序）

**Architecture:** 新增 proposal_deps_analyzer.py，在 propose 阶段消费依赖元数据

**Tech Stack:** Python, YAML, Markdown

---

## File Structure

### Production Code

| File | Responsibility |
|---|---|
| `skills/propose/scripts/proposal_deps_analyzer.py` | 解析提案依赖和特性元数据 |
| `skills/guide-plan/SKILL.md` | 集成拓扑排序创建 |

### Tests

| File | Responsibility |
|---|---|
| `tests/unit/test_proposal_deps_analyzer.py` | 单元测试 |

---

### Task 1: 创建 proposal_deps_analyzer.py

**Files:**
- Create: `skills/propose/scripts/proposal_deps_analyzer.py`
- Test: `tests/unit/test_proposal_deps_analyzer.py`

- [ ] **Step 1: Write the failing test**

```python
def test_parse_deps_metadata():
    content = """
    **依赖**: [add-bar, add-baz]
    **特性**: wave-core
    """
    result = parse_proposal_metadata(content)
    assert result["deps"] == ["add-bar", "add-baz"]
    assert result["feature"] == "wave-core"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_proposal_deps_analyzer.py -v`
Expected: FAIL - module not found

- [ ] **Step 3: Write minimal implementation**

```python
"""Proposal-level dependency and feature metadata analyzer."""
import re
from typing import Dict, List, Optional

def parse_proposal_metadata(content: str) -> Dict[str, any]:
    """Parse **依赖**: and **特性**: metadata from proposal content."""
    result = {
        "deps": [],
        "feature": None,
        "auto_detected": []
    }
    
    # Parse explicit **依赖**: [name1, name2]
    deps_match = re.search(r'\*\*依赖\*\*:\s*\[([^\]]+)\]', content)
    if deps_match:
        deps_str = deps_match.group(1)
        result["deps"] = [d.strip() for d in deps_str.split(',')]
    
    # Parse explicit **特性**: feature-name
    feature_match = re.search(r'\*\*特性\*\*:\s*(\S+)', content)
    if feature_match:
        result["feature"] = feature_match.group(1)
    
    # Auto-detect references to other improvements
    auto_refs = re.findall(r'improvements/([a-z0-9-]+)\.md', content)
    result["auto_detected"] = list(set(auto_refs))
    
    return result

def topological_sort(proposals: List[Dict]) -> List[str]:
    """Sort proposals by dependency order."""
    # Simple topological sort implementation
    sorted_names = []
    visited = set()
    
    def visit(name: str, deps_map: Dict[str, List[str]]):
        if name in visited:
            return
        visited.add(name)
        for dep in deps_map.get(name, []):
            visit(dep, deps_map)
        sorted_names.append(name)
    
    deps_map = {p["name"]: p.get("deps", []) for p in proposals}
    for p in proposals:
        visit(p["name"], deps_map)
    
    return sorted_names
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_proposal_deps_analyzer.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add skills/propose/scripts/proposal_deps_analyzer.py tests/unit/test_proposal_deps_analyzer.py
git commit -m "feat: add proposal deps analyzer for metadata parsing"
```
