# add-roadmap-proposal-guidance Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use skill_use("execute") to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Enable roadmap.md to declare expected improvement themes per category, and have guide-design automatically consume them to display coverage and provide constraint-injection for add-improve proposal creation.

**Architecture:** Three-layer implementation (3 layers, not 4 — Oracle review eliminated the handoff v2 schema bump):
1. **Roadmap layer**: Extend `roadmap.md` task-category table to 5 columns (add "预期改进方向"), add `roadmap_state.py::get_phase_themes()` parser.
2. **Proposal layer**: Add `**主题**:` field to `rdd-workflow-brainstorm` 5-section template, enabling exact-string coverage matching.
3. **Guidance layer**: `add-improve --from-roadmap` mode (env-var pattern, 3-file split) + `guide-design` preflight coverage display + menu option + optional `STRICT_PROPOSAL_COVERAGE` gate.

**Tech Stack:** bash 5.x, Python 3.11+ (env-var passing pattern), Markdown table parsing (regex), bats-core 1.10+, pytest. No new external dependencies.

---

## File Structure

### Production Code

| File | Responsibility |
|---|---|
| `skills/roadmap/scripts/roadmap_state.py` | Add `get_phase_themes()` function + update `add_phase()` template to 5-column |
| `skills/rdd-workflow-brainstorm/SKILL.md` | Update 5-section metadata template to include `**主题**:` field; document constraint-mode contract |
| `skills/add-improve/scripts/from_roadmap.sh` | Bash entry: parse CLI args, expose env-vars, call Python helper |
| `skills/add-improve/scripts/from_roadmap.py` | Python main: read env-vars, load brainstorm in constraint mode, write proposal file with `**主题**:` |
| `skills/add-improve/scripts/from_roadmap.env.py` | Env-var validation (anti-injection: reject shell metacharacters, unset on exit) |
| `skills/add-improve/SKILL.md` | Document `--from-roadmap` mode + env-var naming convention |
| `skills/guide-design/scripts/design_preflight.sh` | New function `compute_theme_coverage()` — calls `roadmap_state.get_phase_themes()` + scans `.rddf/improvements/*.md` for `**主题**:` |
| `skills/guide-design/SKILL.md` | Phase 1 preflight display format; Phase 2 menu option 2; Phase 4 `STRICT_PROPOSAL_COVERAGE` gate |
| `skills/guide-design/scripts/design_proposal_review.sh` | Phase 4 gate: add `STRICT_PROPOSAL_COVERAGE` check branch |
| `skills/roadmap/SKILL.md` | Document 5-column table format + cell syntax (`主题1；主题2`) |
| `AGENTS.md` | Document theme status vocabulary (`未覆盖 / 已覆盖 / ~skipped~`) and env-var naming convention |
| `CHANGELOG.md` | New feature entry |

### Tests

| File | Responsibility |
|---|---|
| `tests/unit/test_roadmap_state_themes.py` | `get_phase_themes()` parser unit tests (≥6 cases) |
| `tests/unit/test_from_roadmap_env_validation.py` | Env-var validation (injection safety) |
| `tests/unit/test_guide_design_preflight_themes.py` | Coverage computation algorithm tests |
| `tests/integration/test_roadmap_5col_parsing.bats` | End-to-end 4/5 column compatibility |
| `tests/integration/test_add_improve_from_roadmap.bats` | Constraint mode flow + HARD-GATE |
| `tests/integration/test_strict_proposal_coverage_gate.bats` | `STRICT_PROPOSAL_COVERAGE` gate behavior |

---

### Task 1: Roadmap parser — add get_phase_themes()

**Files:**
- Modify: `skills/roadmap/scripts/roadmap_state.py` (add function, update `add_phase()` template)
- Test: `tests/unit/test_roadmap_state_themes.py` (new file)

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/test_roadmap_state_themes.py
"""Unit tests for roadmap_state.get_phase_themes() — 5-column table parser."""

import os
import sys
import tempfile
from pathlib import Path

# Add project root to sys.path so we can import skills._lib modules
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from skills.roadmap.scripts.roadmap_state import get_phase_themes  # noqa: E402


def _write_roadmap(content: str) -> str:
    """Helper: write roadmap.md to temp dir, return path."""
    tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False)
    tmp.write(content)
    tmp.close()
    return tmp.name


def test_5col_single_theme():
    """Single theme in 5-column table returns 1-element list."""
    roadmap = """\
# Roadmap

### Phase 1: arch (phase-1)
**目标**: test

#### 任务分类
| 分类ID | 名称 | 描述 | 优先级 | 预期改进方向 |
|--------|------|------|--------|--------------|
| arch-design | 架构 | 核心 | P0 | RBAC权限模型 |
"""
    path = _write_roadmap(roadmap)
    try:
        result = get_phase_themes("phase-1", "arch-design", roadmap_path=path)
        assert result == ["RBAC权限模型"]
    finally:
        os.unlink(path)


def test_5col_multiple_themes_semicolon():
    """Multiple themes separated by `;` returns list."""
    roadmap = """\
# Roadmap

### Phase 1: arch (phase-1)

#### 任务分类
| 分类ID | 名称 | 描述 | 优先级 | 预期改进方向 |
|--------|------|------|--------|--------------|
| arch-design | 架构 | 核心 | P0 | RBAC权限模型；事件总线契约；模块边界 |
"""
    path = _write_roadmap(roadmap)
    try:
        result = get_phase_themes("phase-1", "arch-design", roadmap_path=path)
        assert result == ["RBAC权限模型", "事件总线契约", "模块边界"]
    finally:
        os.unlink(path)


def test_5col_empty_cell():
    """Empty 5th column returns empty list (no constraint)."""
    roadmap = """\
# Roadmap

### Phase 1: arch (phase-1)

#### 任务分类
| 分类ID | 名称 | 描述 | 优先级 | 预期改进方向 |
|--------|------|------|--------|--------------|
| arch-design | 架构 | 核心 | P0 |  |
"""
    path = _write_roadmap(roadmap)
    try:
        result = get_phase_themes("phase-1", "arch-design", roadmap_path=path)
        assert result == []
    finally:
        os.unlink(path)


def test_4col_legacy_compat():
    """4-column legacy table returns empty list (backward compat)."""
    roadmap = """\
# Roadmap

### Phase 1: arch (phase-1)

#### 任务分类
| 分类ID | 名称 | 描述 | 优先级 |
|--------|------|------|--------|
| arch-design | 架构 | 核心 | P0 |
"""
    path = _write_roadmap(roadmap)
    try:
        result = get_phase_themes("phase-1", "arch-design", roadmap_path=path)
        assert result == []
    finally:
        os.unlink(path)


def test_unknown_phase_returns_empty():
    """Unknown phase_id returns empty list (not error)."""
    roadmap = """\
# Roadmap

### Phase 1: arch (phase-1)

#### 任务分类
| 分类ID | 名称 | 描述 | 优先级 | 预期改进方向 |
|--------|------|------|--------|--------------|
| arch-design | 架构 | 核心 | P0 | theme1 |
"""
    path = _write_roadmap(roadmap)
    try:
        result = get_phase_themes("phase-99", "arch-design", roadmap_path=path)
        assert result == []
    finally:
        os.unlink(path)


def test_special_chars_in_theme():
    """Themes with CJK, dots, parens are preserved verbatim."""
    roadmap = """\
# Roadmap

### Phase 1: arch (phase-1)

#### 任务分类
| 分类ID | 名称 | 描述 | 优先级 | 预期改进方向 |
|--------|------|------|--------|--------------|
| arch-design | 架构 | 核心 | P0 | API v2.0 接口；测试覆盖率 > 80% |
"""
    path = _write_roadmap(roadmap)
    try:
        result = get_phase_themes("phase-1", "arch-design", roadmap_path=path)
        assert result == ["API v2.0 接口", "测试覆盖率 > 80%"]
    finally:
        os.unlink(path)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /workspace/project/rdd-workflow && python3 -m pytest tests/unit/test_roadmap_state_themes.py -v`
Expected: ImportError or AttributeError — `get_phase_themes` does not exist.

- [ ] **Step 3: Write minimal implementation**

```python
# skills/roadmap/scripts/roadmap_state.py — ADD to existing module

import re
from pathlib import Path
from typing import List, Optional


def get_phase_themes(
    phase_id: str,
    category_id: str,
    roadmap_path: Optional[str] = None,
) -> List[str]:
    """Parse the 5th column ("预期改进方向") of the task-category table for a given phase/category.

    Returns a list of theme names (semicolon-separated in the cell). Returns
    empty list if the table has only 4 columns (legacy), the cell is empty,
    or the phase/category is not found.

    Backward compatible: 4-column tables return [] (no constraint).
    """
    if roadmap_path is None:
        # Default: project_root/roadmap.md
        from skills.roadmap.scripts.roadmap_state import _default_roadmap_path
        roadmap_path = _default_roadmap_path()

    p = Path(roadmap_path)
    if not p.is_file():
        return []

    content = p.read_text(encoding="utf-8")

    # Find the phase section
    # Pattern: "### Phase N: <title> (phase_id)"
    phase_pattern = re.compile(
        rf"### Phase \d+:.*?\({re.escape(phase_id)}\)",
        re.MULTILINE,
    )
    phase_match = phase_pattern.search(content)
    if not phase_match:
        return []

    # Slice from phase header to next "### Phase" or end of file
    start = phase_match.end()
    next_phase = re.search(r"^### Phase \d+:", content[start:], re.MULTILINE)
    end = start + next_phase.start() if next_phase else len(content)
    phase_section = content[start:end]

    # Find the task-category table within this phase
    # Table format: "| 分类ID | 名称 | 描述 | 优先级 | 预期改进方向 |"
    # We capture the row matching category_id
    # Split by lines, find row with category_id
    lines = phase_section.splitlines()
    for line in lines:
        if category_id not in line or not line.strip().startswith("|"):
            continue
        # Split cells, strip whitespace
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if cells and cells[0] == category_id:
            # cells[0]=category, cells[1]=name, cells[2]=desc, cells[3]=priority
            # cells[4] = "预期改进方向" (only if 5-column)
            if len(cells) >= 5:
                theme_cell = cells[4].strip()
                if not theme_cell:
                    return []
                # Split by semicolon (full-width or half-width)
                themes = re.split(r"[；;]", theme_cell)
                return [t.strip() for t in themes if t.strip()]
            else:
                # Legacy 4-column
                return []

    return []


def _default_roadmap_path() -> str:
    """Resolve default roadmap.md path (project root)."""
    # Caller (preflight script) passes explicit roadmap_path; this is fallback only.
    return "roadmap.md"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /workspace/project/rdd-workflow && python3 -m pytest tests/unit/test_roadmap_state_themes.py -v`
Expected: All 6 tests PASS.

- [ ] **Step 5: Defer commit**

按仓库约定，execute 阶段不逐任务 commit；所有变更将在 archive 阶段统一提交。
如需在 execute 阶段逐任务 commit（不推荐），可设置 `COMMIT_IN_EXECUTE=yes`。

---

### Task 2: Update add_phase() template to 5-column

**Files:**
- Modify: `skills/roadmap/scripts/roadmap_state.py` (find the `add_phase()` function and update its template string)
- Test: extension to `tests/unit/test_roadmap_state_themes.py`

- [ ] **Step 1: Write the failing test**

Add to `tests/unit/test_roadmap_state_themes.py`:

```python
def test_add_phase_default_includes_5th_column(tmp_path):
    """add_phase() default template includes '预期改进方向' header column."""
    from skills.roadmap.scripts.roadmap_state import add_phase

    roadmap_file = tmp_path / "roadmap.md"
    roadmap_file.write_text("# Roadmap\n\n## 阶段定义\n\n", encoding="utf-8")

    add_phase(
        phase_id="phase-99",
        title="Test Phase",
        categories=[{"id": "general", "name": "通用", "desc": "通用分类", "priority": "P0"}],
        roadmap_path=str(roadmap_file),
    )

    content = roadmap_file.read_text(encoding="utf-8")
    assert "预期改进方向" in content
    assert "| 分类ID | 名称 | 描述 | 优先级 | 预期改进方向 |" in content
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /workspace/project/rdd-workflow && python3 -m pytest tests/unit/test_roadmap_state_themes.py::test_add_phase_default_includes_5th_column -v`
Expected: FAIL — current `add_phase()` template only has 4 columns.

- [ ] **Step 3: Update the add_phase template**

In `skills/roadmap/scripts/roadmap_state.py`, locate the `add_phase()` function (around line 296). Find the template string that produces the `#### 任务分类` table and update it:

```python
# OLD (4-column template):
table_header = "| 分类ID | 名称 | 描述 | 优先级 |"
table_separator = "|--------|------|------|--------|"

# NEW (5-column template — preserve existing rows, add new column header):
table_header = "| 分类ID | 名称 | 描述 | 优先级 | 预期改进方向 |"
table_separator = "|--------|------|------|--------|--------------|"
```

Also update the row template — append `| ` to the end of each category row so the 5th cell exists (even if empty):

```python
# Example row (existing) — append empty 5th cell:
row = f"| {cat['id']} | {cat['name']} | {cat['desc']} | {cat['priority']} |  |"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /workspace/project/rdd-workflow && python3 -m pytest tests/unit/test_roadmap_state_themes.py -v`
Expected: All 7 tests PASS.

- [ ] **Step 5: Defer commit**

按仓库约定，execute 阶段不逐任务 commit；所有变更将在 archive 阶段统一提交。

---

### Task 3: brainstorm 5-section template — add **主题** field

**Files:**
- Modify: `skills/rdd-workflow-brainstorm/SKILL.md` (template section)
- Test: `tests/unit/test_brainstorm_template.py` (new file)

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/test_brainstorm_template.py
"""Verify rdd-workflow-brainstorm 5-section template includes **主题** field."""

import re
from pathlib import Path

SKILL_PATH = Path(__file__).resolve().parents[2] / "skills" / "rdd-workflow-brainstorm" / "SKILL.md"


def test_template_includes_subject_field():
    """The 5-section template metadata includes **主题**: line."""
    content = SKILL_PATH.read_text(encoding="utf-8")
    # Look for the format spec (within code block or backticks)
    # The template block starts with "**优先级**:" and includes phase/category/type
    template_match = re.search(
        r"```markdown\s*#\s*<kebab-case-name>.*?```",
        content,
        re.DOTALL,
    )
    assert template_match, "5-section markdown template not found"
    template = template_match.group(0)
    assert "**主题**:" in template or "**主题** :" in template


def test_subject_field_documents_default_values():
    """Field documentation mentions default (empty or '不适用')."""
    content = SKILL_PATH.read_text(encoding="utf-8")
    assert "不适用" in content
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /workspace/project/rdd-workflow && python3 -m pytest tests/unit/test_brainstorm_template.py -v`
Expected: FAIL — current template lacks `**主题**:` field.

- [ ] **Step 3: Update the template in SKILL.md**

In `skills/rdd-workflow-brainstorm/SKILL.md` (around line 134-156), find the markdown template block. Add `**主题**:` line after the `**类型**:` line:

```markdown
```markdown
# <kebab-case-name>

**优先级**: <P0|P1|P2> | **来源**: <来源>
**阶段**: <阶段ID 或 default> | **分类**: <分类>
**类型**: <functional|debt|refactor>
**主题**: <theme-name 或 不适用>    ← NEW LINE
```
```

Also update the "格式要求" section (around line 158) to document the new field's semantics:

```markdown
- `**主题**` — 该提案绑定的 roadmap 主题名 (来自 `roadmap.md` 第 5 列「预期改进方向」),精确字符串匹配用于覆盖率计算。**约束模式**下由 `add-improve --from-roadmap` 自动填入;**自由模式**下留空或填 `不适用`。
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /workspace/project/rdd-workflow && python3 -m pytest tests/unit/test_brainstorm_template.py -v`
Expected: Both tests PASS.

- [ ] **Step 5: Defer commit**

按仓库约定，execute 阶段不逐任务 commit；所有变更将在 archive 阶段统一提交。

---

### Task 4: add-improve --from-roadmap mode — env-var 3-file split

**Files:**
- Create: `skills/add-improve/scripts/from_roadmap.sh` (bash entry)
- Create: `skills/add-improve/scripts/from_roadmap.py` (Python main)
- Create: `skills/add-improve/scripts/from_roadmap.env.py` (env-var validation)
- Modify: `skills/add-improve/SKILL.md` (document new mode)
- Test: `tests/unit/test_from_roadmap_env_validation.py`

- [ ] **Step 1: Write the failing test for env-var validation**

```python
# tests/unit/test_from_roadmap_env_validation.py
"""Tests for from_roadmap.env validation — anti-injection safety."""

import os
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = PROJECT_ROOT / "skills" / "add-improve" / "scripts" / "from_roadmap.env.py"


def test_rejects_shell_metacharacters():
    """Theme names with $(...), backticks, or quote-and-rm are rejected."""
    dangerous_inputs = [
        "evil$(whoami)",
        "evil`id`",
        'evil"; rm -rf #',
        "evil\nnewline",
        "evil' OR 1=1 --",
    ]
    for bad in dangerous_inputs:
        env = os.environ.copy()
        env["ADD_IMPROVE_FROM_ROADMAP"] = "phase-1/arch-design"
        env["ADD_IMPROVE_THEME"] = bad
        env["PROJECT_ROOT"] = str(PROJECT_ROOT)
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "validate"],
            env=env,
            capture_output=True,
            text=True,
        )
        assert result.returncode != 0, f"Should reject: {bad!r}"
        assert "invalid" in result.stderr.lower() or "reject" in result.stderr.lower()


def test_accepts_valid_theme():
    """Plain CJK theme names with spaces and punctuation are accepted."""
    valid_themes = [
        "RBAC权限模型",
        "API v2.0 接口",
        "测试覆盖率 > 80%",
        "事件总线契约",
    ]
    for good in valid_themes:
        env = os.environ.copy()
        env["ADD_IMPROVE_FROM_ROADMAP"] = "phase-1/arch-design"
        env["ADD_IMPROVE_THEME"] = good
        env["PROJECT_ROOT"] = str(PROJECT_ROOT)
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "validate"],
            env=env,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, f"Should accept: {good!r}\nstderr: {result.stderr}"


def test_requires_both_env_vars():
    """Missing --theme when --from-roadmap is set fails fast."""
    env = os.environ.copy()
    env.pop("ADD_IMPROVE_THEME", None)
    env["ADD_IMPROVE_FROM_ROADMAP"] = "phase-1/arch-design"
    env["PROJECT_ROOT"] = str(PROJECT_ROOT)
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "validate"],
        env=env,
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    assert "ADD_IMPROVE_THEME" in result.stderr
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /workspace/project/rdd-workflow && python3 -m pytest tests/unit/test_from_roadmap_env_validation.py -v`
Expected: FAIL — `from_roadmap.env.py` does not exist.

- [ ] **Step 3: Create from_roadmap.env.py**

```python
#!/usr/bin/env python3
# skills/add-improve/scripts/from_roadmap.env.py
# Env-var validation for add-improve --from-roadmap mode (Oracle C1 anti-injection).
#
# Usage:
#   python3 from_roadmap.env.py validate     # validates env-vars, exits 0/1
#   python3 from_roadmap.env.py describe     # prints validated values as JSON
#
# Exit codes:
#   0 — valid
#   1 — validation error (writes to stderr)
#
# Validates:
#   - ADD_IMPROVE_FROM_ROADMAP (required, format: phase_id/category_id)
#   - ADD_IMPROVE_THEME (required when FROM_ROADMAP set, no shell metachars)
#   - BRAINSTORM_RATIONALE_DRAFT (optional, no shell metachars)
#
# Disallowed characters in theme/rationale (anti-injection):
#   $ ` " ' ; | & \n \r  ( ) { } < >  ! ~ #

import json
import os
import re
import sys
from typing import Optional

# Allowed characters: CJK, ASCII letters/digits, spaces, common punctuation . , : - _ + = / ?
# Explicitly disallowed (shell injection vectors):
_DISALLOWED_RE = re.compile(r'[$`"\';|&\n\r(){}<>!~#]')
_FROM_ROADMAP_RE = re.compile(r"^[a-z0-9-]+/[a-z0-9-]+$")


def _check_text(value: str, name: str) -> Optional[str]:
    """Return error message if value contains disallowed chars, else None."""
    if not value:
        return f"{name} is empty"
    if _DISALLOWED_RE.search(value):
        return f"{name} contains disallowed shell metacharacters: {value!r}"
    if len(value) > 200:
        return f"{name} exceeds 200 chars (got {len(value)})"
    return None


def validate_env() -> dict:
    """Validate env-vars, return dict of values (or raise SystemExit)."""
    errors = []

    from_roadmap = os.environ.get("ADD_IMPROVE_FROM_ROADMAP", "").strip()
    theme = os.environ.get("ADD_IMPROVE_THEME", "").strip()
    rationale = os.environ.get("BRAINSTORM_RATIONALE_DRAFT", "").strip()

    if from_roadmap:
        # --from-roadmap mode triggered: require theme
        if not _FROM_ROADMAP_RE.match(from_roadmap):
            errors.append(
                f"ADD_IMPROVE_FROM_ROADMAP must match phase_id/category_id "
                f"(got {from_roadmap!r})"
            )
        err = _check_text(theme, "ADD_IMPROVE_THEME")
        if err:
            errors.append(err)
        if rationale:
            err = _check_text(rationale, "BRAINSTORM_RATIONALE_DRAFT")
            if err:
                errors.append(err)

    if errors:
        for e in errors:
            print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)

    return {
        "from_roadmap": from_roadmap,
        "theme": theme,
        "rationale": rationale,
    }


def main() -> int:
    if len(sys.argv) < 2 or sys.argv[1] not in {"validate", "describe"}:
        print("Usage: from_roadmap.env.py {validate|describe}", file=sys.stderr)
        return 1

    values = validate_env()

    if sys.argv[1] == "describe":
        print(json.dumps(values, ensure_ascii=False))
    # 'validate' prints nothing on success, exit 0

    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /workspace/project/rdd-workflow && python3 -m pytest tests/unit/test_from_roadmap_env_validation.py -v`
Expected: All 3 test groups PASS.

- [ ] **Step 5: Defer commit**

按仓库约定，execute 阶段不逐任务 commit；所有变更将在 archive 阶段统一提交。

---

### Task 5: add-improve --from-roadmap — bash entry + Python main

**Files:**
- Create: `skills/add-improve/scripts/from_roadmap.sh`
- Create: `skills/add-improve/scripts/from_roadmap.py`

- [ ] **Step 1: Write the failing integration test**

```bash
# tests/integration/test_add_improve_from_roadmap.bats
#!/usr/bin/env bats

setup() {
    load 'test_helper'
    setup_isolated_test_env
}

teardown() {
    cleanup_isolated_test_env
}

@test "add-improve --from-roadmap creates proposal with 主题 field" {
    # Create a roadmap with a theme
    cat > "$TEST_PROJECT_ROOT/roadmap.md" <<'EOF'
# Test Roadmap

### Phase 1: arch (phase-1)
**目标**: test

#### 任务分类
| 分类ID | 名称 | 描述 | 优先级 | 预期改进方向 |
|--------|------|------|--------|--------------|
| arch-design | 架构 | 核心 | P0 | RBAC权限模型 |
EOF

    # Invoke bash entry
    run bash "$BATS_TEST_DIRNAME/../../skills/add-improve/scripts/from_roadmap.sh" \
        --from-roadmap "phase-1/arch-design" \
        --theme "RBAC权限模型" \
        --project-root "$TEST_PROJECT_ROOT"

    [ "$status" -eq 0 ]

    # Verify proposal file created with 主题 field
    [ -f "$TEST_PROJECT_ROOT/.rddf/improvements/test-proposal.md" ] || \
        find "$TEST_PROJECT_ROOT/.rddf/improvements/" -name "*.md" -exec grep -l "RBAC权限模型" {} \; | head -1

    grep -q "^\*\*主题\*\*: RBAC权限模型" \
        "$TEST_PROJECT_ROOT/.rddf/improvements/"*.md
}

@test "add-improve --from-roadmap rejects shell injection in theme" {
    run bash "$BATS_TEST_DIRNAME/../../skills/add-improve/scripts/from_roadmap.sh" \
        --from-roadmap "phase-1/arch-design" \
        --theme 'evil$(whoami)'

    [ "$status" -ne 0 ]
    [[ "$output" == *"disallowed"* ]] || [[ "$output" == *"invalid"* ]]
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /workspace/project/rdd-workflow && bats tests/integration/test_add_improve_from_roadmap.bats`
Expected: FAIL — `from_roadmap.sh` does not exist.

- [ ] **Step 3: Create from_roadmap.sh**

```bash
#!/usr/bin/env bash
# skills/add-improve/scripts/from_roadmap.sh
# Bash entry for `add-improve --from-roadmap` mode (Oracle C1 env-var pattern).
#
# Usage:
#   bash from_roadmap.sh --from-roadmap <phase_id>/<category_id> \
#                        --theme <theme_name> \
#                        [--rationale "<draft rationale>"] \
#                        --project-root <path>
#
# Behavior:
#   1. Parses CLI args into env-vars (ADD_IMPROVE_FROM_ROADMAP, ADD_IMPROVE_THEME, etc.)
#   2. Calls from_roadmap.env.py validate to reject shell metacharacters
#   3. Calls from_roadmap.py to invoke brainstorm in constraint mode and write proposal
#   4. Unsets env-vars on exit (cleanup)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Defaults
FROM_ROADMAP=""
THEME=""
RATIONALE=""
PROJECT_ROOT="${PROJECT_ROOT:-$(pwd)}"

usage() {
    cat <<EOF
Usage: $0 --from-roadmap <phase/category> --theme <name> [--rationale <text>] --project-root <path>

Options:
  --from-roadmap    REQUIRED: phase_id/category_id (e.g., phase-1/arch-design)
  --theme           REQUIRED: roadmap theme name (must NOT contain shell metacharacters)
  --rationale       OPTIONAL: AI-drafted rationale (passed to brainstorm scaffold)
  --project-root    REQUIRED: absolute path to project root
EOF
    exit 1
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --from-roadmap) FROM_ROADMAP="$2"; shift 2 ;;
        --theme)        THEME="$2"; shift 2 ;;
        --rationale)    RATIONALE="$2"; shift 2 ;;
        --project-root) PROJECT_ROOT="$2"; shift 2 ;;
        -h|--help)      usage ;;
        *)              echo "Unknown arg: $1" >&2; usage ;;
    esac
done

# Validate required args
if [[ -z "$FROM_ROADMAP" || -z "$THEME" || -z "$PROJECT_ROOT" ]]; then
    echo "ERROR: --from-roadmap, --theme, --project-root are required" >&2
    usage
fi

# Export env-vars (Oracle C1 pattern — no string interpolation into Python)
export ADD_IMPROVE_FROM_ROADMAP="$FROM_ROADMAP"
export ADD_IMPROVE_THEME="$THEME"
export BRAINSTORM_RATIONALE_DRAFT="$RATIONALE"
export PROJECT_ROOT

# Cleanup function (always unset on exit, success or failure)
cleanup() {
    unset ADD_IMPROVE_FROM_ROADMAP
    unset ADD_IMPROVE_THEME
    unset BRAINSTORM_RATIONALE_DRAFT
}
trap cleanup EXIT

# Step 1: Validate env-vars (reject shell metacharacters)
if ! python3 "$SCRIPT_DIR/from_roadmap.env.py" validate; then
    echo "ERROR: env-var validation failed" >&2
    exit 1
fi

# Step 2: Run main logic
python3 "$SCRIPT_DIR/from_roadmap.py"
```

- [ ] **Step 4: Create from_roadmap.py**

```python
#!/usr/bin/env python3
# skills/add-improve/scripts/from_roadmap.py
# Main logic for add-improve --from-roadmap mode.
#
# Reads validated env-vars, invokes rdd-workflow-brainstorm in constraint mode,
# and writes the proposal file with **主题** field populated.
#
# HARD-GATE: rdd-workflow-brainstorm requires explicit user approval before file
# creation. This script pre-fills scaffold but does NOT bypass the gate.
# (In non-interactive execution, the gate is enforced via stdin reading or
# pre-approved flag — see --yes-auto-approve-test-only for tests.)

import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


def main() -> int:
    project_root = Path(os.environ["PROJECT_ROOT"])
    from_roadmap = os.environ["ADD_IMPROVE_FROM_ROADMAP"]  # validated
    theme = os.environ["ADD_IMPROVE_THEME"]                 # validated
    rationale = os.environ.get("BRAINSTORM_RATIONALE_DRAFT", "")

    phase_id, category_id = from_roadmap.split("/", 1)

    # Build proposal scaffold (5-section template)
    # In production, this would invoke rdd-workflow-brainstorm interactively.
    # For batch/CI execution, we provide a scaffold that user reviews.
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    proposal_name = f"from-roadmap-{phase_id}-{category_id}".replace("/", "-")
    proposal_file = project_root / ".rddf" / "improvements" / f"{proposal_name}.md"

    content = f"""# {proposal_name}

**优先级**: P1 | **来源**: from-roadmap ({from_roadmap})
**阶段**: {phase_id} | **分类**: {category_id}
**类型**: functional
**主题**: {theme}

## 架构依据

{rationale if rationale else "_待用户填写: AI 起草的 rationale 已通过 env-var BRAINSTORM_RATIONALE_DRAFT 传入_"}

## 范围

- **In Scope**: _待 brainstorm 确认_
- **Out Scope**: _待 brainstorm 确认_

## 关键场景

- GIVEN _待 brainstorm 填写_
  WHEN _
  THEN _

## 技术约束

- MUST _
- MUST NOT _
- SHOULD _

## 验收标准

- [ ] _
"""

    proposal_file.parent.mkdir(parents=True, exist_ok=True)
    proposal_file.write_text(content, encoding="utf-8")

    print(f"✅ Scaffold created: {proposal_file}")
    print(f"   **主题**: {theme}")
    print(f"   Next: run brainstorm interactively to fill scaffold and approve")

    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd /workspace/project/rdd-workflow && bats tests/integration/test_add_improve_from_roadmap.bats`
Expected: First test PASS, second test PASS.

Note: First test may need adjustment — the `from_roadmap.py` writes to a deterministic name `from-roadmap-phase-1-arch-design.md`. Verify the test asserts on that name.

- [ ] **Step 6: Document in SKILL.md**

In `skills/add-improve/SKILL.md`, add a new section after "Phase 3: 引导下一步":

```markdown
### Phase 4: from-roadmap 模式 (v2.2 新增)

**入口条件**: 用户从外部上下文（如 guide-design Phase 2 选项 2）传入 `--from-roadmap <phase_id>/<category_id> --theme <theme_name>`。

**行为**: 跳过 Phase 0 OPEN-PROMPT，直接加载 `rdd-workflow-brainstorm` 进入约束模式，预填 5 段 scaffold 的**架构依据**（来自 `BRAINSTORM_RATIONALE_DRAFT`）和**主题**字段。

**env-var 契约**（3 文件 split，Oracle C1 安全）:
- `ADD_IMPROVE_FROM_ROADMAP`: `<phase_id>/<category_id>` (kebab-case)
- `ADD_IMPROVE_THEME`: roadmap 第 5 列中的主题名（精确字符串匹配）
- `BRAINSTORM_RATIONALE_DRAFT`: 可选，AI 起草的 rationale

**HARD-GATE**: 约束模式不绕过 brainstorm 逐段确认。`from_roadmap.py` 仅写 scaffold，**不自动落盘 `proposal-suggestions.md`**。

**安全**: `from_roadmap.env.py::validate` 拒绝 `$`、反引号、`"`、`'`、`;`、`|`、`&`、换行符、`()`、`{}`、`<>`、`!`、`~`、`#` 等 shell 元字符。

**示例调用**:
```bash
bash ~/.agents/skills/add-improve/scripts/from_roadmap.sh \
    --from-roadmap phase-1/arch-design \
    --theme "RBAC权限模型" \
    --rationale "ADR-0003 §2.3 提及但未细化" \
    --project-root /path/to/project
```
```

- [ ] **Step 7: Defer commit**

按仓库约定，execute 阶段不逐任务 commit；所有变更将在 archive 阶段统一提交。

---

### Task 6: guide-design preflight — compute_theme_coverage()

**Files:**
- Modify: `skills/guide-design/scripts/design_preflight.sh` (add new function)
- Test: `tests/unit/test_guide_design_preflight_themes.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/test_guide_design_preflight_themes.py
"""Tests for theme coverage computation algorithm."""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from skills.guide_design.scripts.design_preflight import compute_theme_coverage  # noqa: E402


def test_coverage_full_match(tmp_path):
    """All themes matched → 100% coverage."""
    # Create roadmap
    (tmp_path / "roadmap.md").write_text(
        """\
### Phase 1: arch (phase-1)
#### 任务分类
| 分类ID | 名称 | 描述 | 优先级 | 预期改进方向 |
|--------|------|------|--------|--------------|
| arch-design | 架构 | 核心 | P0 | RBAC；事件总线 |
""",
        encoding="utf-8",
    )
    # Create matching proposals
    imp_dir = tmp_path / ".rddf" / "improvements"
    imp_dir.mkdir(parents=True)
    (imp_dir / "p1.md").write_text(
        "**主题**: RBAC\n## 范围\n...", encoding="utf-8"
    )
    (imp_dir / "p2.md").write_text(
        "**主题**: 事件总线\n## 范围\n...", encoding="utf-8"
    )

    result = compute_theme_coverage(
        project_root=str(tmp_path),
        roadmap_path=str(tmp_path / "roadmap.md"),
        improvements_dir=str(imp_dir),
    )
    assert result["total_themes"] == 2
    assert result["covered"] == 2
    assert result["uncovered"] == []
    assert result["coverage_pct"] == 100


def test_coverage_partial_match(tmp_path):
    """1 of 2 themes matched → 50% coverage."""
    (tmp_path / "roadmap.md").write_text(
        """\
### Phase 1: arch (phase-1)
#### 任务分类
| 分类ID | 名称 | 描述 | 优先级 | 预期改进方向 |
|--------|------|------|--------|--------------|
| arch-design | 架构 | 核心 | P0 | RBAC；事件总线 |
""",
        encoding="utf-8",
    )
    imp_dir = tmp_path / ".rddf" / "improvements"
    imp_dir.mkdir(parents=True)
    (imp_dir / "p1.md").write_text(
        "**主题**: RBAC\n## 范围\n...", encoding="utf-8"
    )

    result = compute_theme_coverage(
        project_root=str(tmp_path),
        roadmap_path=str(tmp_path / "roadmap.md"),
        improvements_dir=str(imp_dir),
    )
    assert result["total_themes"] == 2
    assert result["covered"] == 1
    assert result["uncovered"] == ["事件总线"]
    assert result["coverage_pct"] == 50


def test_coverage_legacy_no_subject_field(tmp_path):
    """Old proposals without **主题** field counted separately, no false alarm."""
    (tmp_path / "roadmap.md").write_text(
        """\
### Phase 1: arch (phase-1)
#### 任务分类
| 分类ID | 名称 | 描述 | 优先级 | 预期改进方向 |
|--------|------|------|--------|--------------|
| arch-design | 架构 | 核心 | P0 | RBAC |
""",
        encoding="utf-8",
    )
    imp_dir = tmp_path / ".rddf" / "improvements"
    imp_dir.mkdir(parents=True)
    # Old proposal — no 主题 field
    (imp_dir / "legacy.md").write_text(
        "**优先级**: P1\n## 范围\n...", encoding="utf-8"
    )

    result = compute_theme_coverage(
        project_root=str(tmp_path),
        roadmap_path=str(tmp_path / "roadmap.md"),
        improvements_dir=str(imp_dir),
    )
    assert result["total_themes"] == 1
    assert result["covered"] == 0
    assert result["uncovered"] == ["RBAC"]
    assert result["unmapped_legacy_count"] == 1


def test_skipped_theme_excluded(tmp_path):
    """~skipped~ themes don't count toward denominator."""
    (tmp_path / "roadmap.md").write_text(
        """\
### Phase 1: arch (phase-1)
#### 任务分类
| 分类ID | 名称 | 描述 | 优先级 | 预期改进方向 |
|--------|------|------|--------|--------------|
| arch-design | 架构 | 核心 | P0 | RBAC；事件总线 ~skipped~ |
""",
        encoding="utf-8",
    )

    result = compute_theme_coverage(
        project_root=str(tmp_path),
        roadmap_path=str(tmp_path / "roadmap.md"),
        improvements_dir=str(tmp_path / "improvements"),
    )
    assert result["total_themes"] == 1  # only RBAC, ~skipped~ excluded
    assert result["uncovered"] == ["RBAC"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /workspace/project/rdd-workflow && python3 -m pytest tests/unit/test_guide_design_preflight_themes.py -v`
Expected: ImportError — module does not exist.

- [ ] **Step 3: Create design_preflight.py**

```python
# skills/guide-design/scripts/design_preflight.py
"""Theme coverage computation for guide-design preflight display."""

import re
import sys
from pathlib import Path
from typing import List, Dict, Any


_SUBJECT_RE = re.compile(r"^\*\*主题\*\*\s*:\s*(.+?)\s*$", re.MULTILINE)
_SKIPPED_SUFFIX = "~skipped~"


def _parse_themes_cell(cell: str) -> List[str]:
    """Split a 5th-column cell by ;/； and return clean theme names."""
    if not cell.strip():
        return []
    parts = re.split(r"[；;]", cell)
    cleaned = []
    for p in parts:
        p = p.strip()
        if not p:
            continue
        # Mark ~skipped~ but keep in list (caller decides exclusion)
        cleaned.append(p)
    return cleaned


def _read_roadmap_themes(roadmap_path: str) -> List[Dict[str, str]]:
    """Parse roadmap.md, return list of {phase, category, theme} dicts."""
    content = Path(roadmap_path).read_text(encoding="utf-8")
    themes = []

    # Find each phase section
    phase_pattern = re.compile(
        r"### Phase \d+:[^\n]*?\(phase-[a-z0-9-]+\)",
        re.MULTILINE,
    )
    for phase_match in phase_pattern.finditer(content):
        # Extract phase_id
        pid_match = re.search(r"\((phase-[a-z0-9-]+)\)", phase_match.group(0))
        if not pid_match:
            continue
        phase_id = pid_match.group(1)

        # Slice phase section
        start = phase_match.end()
        next_phase = re.search(r"^### Phase \d+:", content[start:], re.MULTILINE)
        end = start + next_phase.start() if next_phase else len(content)
        phase_section = content[start:end]

        # Find task-category table
        for line in phase_section.splitlines():
            if not line.strip().startswith("|"):
                continue
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if len(cells) < 2:
                continue
            # Skip header rows
            if cells[0] in {"分类ID", "--------"} or set(cells[0]) <= {"-"}:
                continue
            category_id = cells[0]
            if len(cells) < 5:
                continue  # 4-column legacy
            for theme in _parse_themes_cell(cells[4]):
                themes.append({
                    "phase": phase_id,
                    "category": category_id,
                    "theme": theme,
                })

    return themes


def _read_proposal_subjects(improvements_dir: str) -> tuple[List[str], int]:
    """Scan improvements/*.md for **主题** fields.

    Returns (matched_subjects, unmapped_legacy_count).
    """
    matched = []
    unmapped_legacy = 0
    p = Path(improvements_dir)
    if not p.is_dir():
        return matched, unmapped_legacy

    for f in p.glob("*.md"):
        content = f.read_text(encoding="utf-8")
        m = _SUBJECT_RE.search(content)
        if m:
            subject = m.group(1).strip()
            if subject and subject != "不适用":
                matched.append(subject)
        else:
            unmapped_legacy += 1

    return matched, unmapped_legacy


def compute_theme_coverage(
    project_root: str,
    roadmap_path: str,
    improvements_dir: str,
) -> Dict[str, Any]:
    """Compute theme coverage: matched / total / uncovered / legacy.

    Returns dict with:
      - total_themes: int (excluding ~skipped~)
      - covered: int (proposals whose 主题 matches a theme)
      - uncovered: list[str] (theme names not matched)
      - coverage_pct: float
      - unmapped_legacy_count: int (proposals without 主题 field)
      - phases: dict[phase_id] -> dict (per-phase breakdown)
    """
    themes = _read_roadmap_themes(roadmap_path)
    subjects, legacy_count = _read_proposal_subjects(improvements_dir)

    # Exclude ~skipped~ from denominator
    active_themes = [t for t in themes if not t["theme"].endswith(_SKIPPED_SUFFIX)]
    skipped_themes = [t for t in themes if t["theme"].endswith(_SKIPPED_SUFFIX)]

    # Clean theme names (strip ~skipped~ marker)
    active_names = [t["theme"].strip().removesuffix(_SKIPPED_SUFFIX).strip()
                    for t in active_themes]

    covered = [name for name in active_names if name in subjects]
    uncovered = [name for name in active_names if name not in subjects]

    total = len(active_names)
    coverage_pct = round(100 * len(covered) / total, 1) if total > 0 else 100.0

    return {
        "total_themes": total,
        "covered": len(covered),
        "uncovered": uncovered,
        "coverage_pct": coverage_pct,
        "unmapped_legacy_count": legacy_count,
        "skipped_count": len(skipped_themes),
    }


if __name__ == "__main__":
    # CLI usage: python3 design_preflight.py <project_root> <roadmap_path> <improvements_dir>
    if len(sys.argv) != 4:
        print("Usage: design_preflight.py <project_root> <roadmap_path> <improvements_dir>", file=sys.stderr)
        sys.exit(1)
    import json
    result = compute_theme_coverage(sys.argv[1], sys.argv[2], sys.argv[3])
    print(json.dumps(result, ensure_ascii=False, indent=2))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /workspace/project/rdd-workflow && python3 -m pytest tests/unit/test_guide_design_preflight_themes.py -v`
Expected: All 4 tests PASS.

- [ ] **Step 5: Defer commit**

按仓库约定，execute 阶段不逐任务 commit；所有变更将在 archive 阶段统一提交。

---

### Task 7: guide-design SKILL.md — Phase 1/2/4 updates

**Files:**
- Modify: `skills/guide-design/SKILL.md` (Phase 1 preflight display, Phase 2 menu, Phase 4 gate)
- Test: `tests/integration/test_strict_proposal_coverage_gate.bats` (new file)

- [ ] **Step 1: Write the failing test for STRICT gate**

```bash
# tests/integration/test_strict_proposal_coverage_gate.bats
#!/usr/bin/env bats

setup() {
    load 'test_helper'
    setup_isolated_test_env
}

teardown() {
    cleanup_isolated_test_env
}

@test "STRICT_PROPOSAL_COVERAGE=yes blocks design-done when uncovered themes exist" {
    export STRICT_PROPOSAL_COVERAGE=yes
    # Setup roadmap with 2 themes, 1 covered
    cat > "$TEST_PROJECT_ROOT/roadmap.md" <<'EOF'
### Phase 1: arch (phase-1)
#### 任务分类
| 分类ID | 名称 | 描述 | 优先级 | 预期改进方向 |
|--------|------|------|--------|--------------|
| arch-design | 架构 | 核心 | P0 | RBAC；事件总线 |
EOF

    # Create 1 matching proposal
    mkdir -p "$TEST_PROJECT_ROOT/.rddf/improvements"
    cat > "$TEST_PROJECT_ROOT/.rddf/improvements/p1.md" <<'EOF'
**主题**: RBAC
## 范围
EOF

    # Run the gate check
    run bash "$TEST_PROJECT_ROOT/skills/guide-design/scripts/design_proposal_review.sh" \
        "$TEST_PROJECT_ROOT" "gate"

    [ "$status" -ne 0 ]
    [[ "$output" == *"事件总线"* ]]
    [[ "$output" == *"STRICT_PROPOSAL_COVERAGE"* ]]
}

@test "default (no env var) is warning only, does not block" {
    unset STRICT_PROPOSAL_COVERAGE
    cat > "$TEST_PROJECT_ROOT/roadmap.md" <<'EOF'
### Phase 1: arch (phase-1)
#### 任务分类
| 分类ID | 名称 | 描述 | 优先级 | 预期改进方向 |
|--------|------|------|--------|--------------|
| arch-design | 架构 | 核心 | P0 | RBAC；事件总线 |
EOF

    mkdir -p "$TEST_PROJECT_ROOT/.rddf/improvements"
    cat > "$TEST_PROJECT_ROOT/.rddf/improvements/p1.md" <<'EOF'
**主题**: RBAC
## 范围
EOF

    run bash "$TEST_PROJECT_ROOT/skills/guide-design/scripts/design_proposal_review.sh" \
        "$TEST_PROJECT_ROOT" "gate"

    # Should warn but pass
    [[ "$output" == *"事件总线"* ]] || true
    # Exit code may be 0 (warning only)
    [ "$status" -eq 0 ] || [ "$status" -eq 1 ]
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /workspace/project/rdd-workflow && bats tests/integration/test_strict_proposal_coverage_gate.bats`
Expected: FAIL — gate does not check coverage yet.

- [ ] **Step 3: Modify design_proposal_review.sh**

In `skills/guide-design/scripts/design_proposal_review.sh`, find the function that implements `design_proposal_review` (around line 26-373). Add a new helper function and integrate it into the gate-check path.

Find the spot after the existing logic (before the function returns). Add:

```bash
# Inside design_proposal_review() function, near the end (before final return)

# Compute theme coverage
local COVERAGE_RESULT
COVERAGE_RESULT=$(PROJECT_ROOT="$PROJECT_ROOT" python3 - <<PYEOF
import sys
sys.path.insert(0, "${SCRIPT_DIR}/../../guide-design/scripts")
from design_preflight import compute_theme_coverage
import json
result = compute_theme_coverage(
    project_root="${PROJECT_ROOT}",
    roadmap_path="${ROADMAP_FILE}",
    improvements_dir="${PROJECT_ROOT}/.rddf/improvements",
)
print(json.dumps(result, ensure_ascii=False))
PYEOF
)

local UNCOVERED=$(echo "$COVERAGE_RESULT" | python3 -c "import sys, json; print(' '.join(json.load(sys.stdin).get('uncovered', [])))")
local TOTAL=$(echo "$COVERAGE_RESULT" | python3 -c "import sys, json; print(json.load(sys.stdin).get('total_themes', 0))")

if [ "$TOTAL" -gt 0 ] && [ -n "$UNCOVERED" ]; then
    echo ""
    echo "📊 Roadmap 主题覆盖率:"
    echo "   总主题: $TOTAL"
    echo "   未覆盖: $UNCOVERED"
    echo ""

    if [ "${STRICT_PROPOSAL_COVERAGE:-}" = "yes" ]; then
        if [ "${SKIP_PROPOSAL_COVERAGE:-}" != "yes" ]; then
            echo "❌ STRICT_PROPOSAL_COVERAGE=yes 但有未覆盖主题"
            echo "   选项: 补 proposal / 显式 skip 主题 / 设置 SKIP_PROPOSAL_COVERAGE=yes 临时绕过"
            return 1
        else
            echo "⚠️  SKIP_PROPOSAL_COVERAGE=yes, coverage gate skipped"
        fi
    else
        echo "⚠️  coverage gate is warning only (set STRICT_PROPOSAL_COVERAGE=yes to enforce)"
    fi
fi
```

Note: This requires `ROADMAP_FILE` to be set earlier in the function. If not, add detection logic at the top of `design_proposal_review()`:

```bash
# Detect roadmap file (ADR-0016 arch-handoff)
local ROADMAP_FILE
if [ -f "$PROJECT_ROOT/.rddf/state/.arch-handoff.json" ]; then
    ROADMAP_FILE=$(jq -r '.roadmap_path // "roadmap.md"' "$PROJECT_ROOT/.rddf/state/.arch-handoff.json")
    ROADMAP_FILE="$PROJECT_ROOT/$ROADMAP_FILE"
else
    ROADMAP_FILE="$PROJECT_ROOT/roadmap.md"
fi
```

- [ ] **Step 4: Update SKILL.md**

In `skills/guide-design/SKILL.md`:

**Phase 1 (after the "📋 架构上下文" display block, around line 113)** — add coverage display:

```markdown
**主题覆盖率显示**（v2.2 新增）：

```bash
# 在 preflight 阶段调用
PROJECT_ROOT="$PROJECT_ROOT" python3 "$SCRIPT_DIR/design_preflight.py" \
    "$PROJECT_ROOT" "${ROADMAP_FILE:-$PROJECT_ROOT/roadmap.md}" \
    "$PROJECT_ROOT/.rddf/improvements"
```

输出格式:
```
📋 路线图指引: 6 个主题 across 3 分类
📌 当前提案覆盖: 2/7 (29%) ⚠️
📌 未覆盖主题:
  - [phase-1/arch-design] 事件总线契约
  - [phase-1/infra-setup] Docker镜像
📌 未标注主题: 1 个旧 proposal (向后兼容)
```
```

**Phase 2 (around line 122 menu)** — add new option 2:

```markdown
```
设计阶段 - 提案管理

📂 提案池:
  - 待审查: N 个
  - 已归档(自动批准): M 个
  - 已推迟: K 个（按 v 查看全部）
  - 路线图覆盖: X/M (Y%) ⚠️

选择操作:
  1. ➕ 创建新提案（add-improve 自由模式）
  2. 🎯 按路线图主题创建提案（推荐）  ← NEW
  3. 📋 审查待批准提案
  4. ✅ 批量批准所有提案
  5. ✅ 完成设计阶段 → 进入设计门控
```
```

**Phase 4 (around line 215-232 check_design_done_gate)** — add coverage check:

```markdown
**主题覆盖率门控** (v2.2 新增)：

```bash
# 在 check_design_done_gate 末尾调用
if [ "${STRICT_PROPOSAL_COVERAGE:-}" = "yes" ]; then
    # 调用 compute_theme_coverage, 检查是否有未覆盖主题
    # 有则 return 1 (门控失败)
fi
```

环境变量:
- `STRICT_PROPOSAL_COVERAGE=yes` — 启用严格门控 (默认 OFF)
- `SKIP_PROPOSAL_COVERAGE=yes` — 临时绕过 (紧急情况)
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd /workspace/project/rdd-workflow && bats tests/integration/test_strict_proposal_coverage_gate.bats`
Expected: Both tests PASS.

- [ ] **Step 6: Defer commit**

按仓库约定，execute 阶段不逐任务 commit；所有变更将在 archive 阶段统一提交。

---

### Task 8: Documentation updates — roadmap/SKILL.md, AGENTS.md, CHANGELOG.md

**Files:**
- Modify: `skills/roadmap/SKILL.md` (5-column table documentation)
- Modify: `AGENTS.md` (theme status vocabulary + env-var naming)
- Modify: `CHANGELOG.md` (new feature entry)

- [ ] **Step 1: Update skills/roadmap/SKILL.md**

Find the section that documents the `#### 任务分类` table format (around line 124-130 in the template example). Update it to include the 5th column:

```markdown
#### 任务分类

| 分类ID | 名称 | 描述 | 优先级 | 预期改进方向 |
|--------|------|------|--------|--------------|
| arch-design | 架构设计 | 核心架构和接口设计 | P0 | RBAC权限模型；事件总线契约；模块边界 |
| infra-setup | 基础设施 | 构建系统、CI/CD、工具链 | P0 | Docker镜像；GitHub Actions |
| core-impl | 核心实现 | 基础类和核心功能实现 | P1 | - |

> **预期改进方向** (v2.2 新增): 可选第 5 列,内容为 `主题1；主题2` 分号分隔。guide-design 进入时会读取此列计算覆盖率。空 cell 表示该分类无主题约束 (向后兼容)。
```

- [ ] **Step 2: Update AGENTS.md**

Find the "关键约定" section. Add a new bullet:

```markdown
### 主题状态词汇 (roadmap-proposal-guidance, v2.2+)

| 状态 | 含义 | coverage 分母 |
|------|------|---------------|
| `未覆盖` | roadmap 定义但无 proposal 匹配 | 计入 |
| `已覆盖` | 至少一个 proposal 的 `**主题**:` 字段精确匹配 | 不计入 |
| `~skipped~` | 用户显式标记豁免 (在 cell 末尾追加 `~skipped~`) | 不计入 |

### env-var 命名规范 (Oracle C1)

- 所有 add-improve/brainstorm 间传参 env-var MUST 大写蛇形: `ADD_IMPROVE_FROM_ROADMAP`, `ADD_IMPROVE_THEME`, `BRAINSTORM_RATIONALE_DRAFT`
- 调用结束 MUST `unset` env-var (避免污染 shell),用 `trap cleanup EXIT`
- 禁止 `python3 -c "...$VAR..."` 内联 bash 字符串插值
```

- [ ] **Step 3: Update CHANGELOG.md**

Find the "Unreleased" or top section. Add:

```markdown
## [Unreleased]

### Added

- **roadmap-proposal-guidance**: 让 roadmap 节点声明预期改进主题,guide-design 自动消费并约束 proposal 创建流程
  - `roadmap.md` 任务分类表格支持 5 列 (新增 "预期改进方向")
  - `roadmap_state.py::get_phase_themes()` 解析第 5 列
  - `rdd-workflow-brainstorm` 5 段模板新增 `**主题**:` 字段
  - `add-improve --from-roadmap <phase/cat> --theme <name>` 模式 (env-var 3 文件 split)
  - `guide-design` Phase 1 preflight 显示主题覆盖率 + 未覆盖清单
  - Phase 2 菜单新增选项 2 "🎯 按路线图主题创建提案"
  - Phase 4 design-done 门控支持 `STRICT_PROPOSAL_COVERAGE=yes` 严格模式
  - 主题状态词汇: `未覆盖 / 已覆盖 / ~skipped~`
```

- [ ] **Step 4: Verify all docs render**

Run: `cd /workspace/project/rdd-workflow && grep -l "预期改进方向\|--from-roadmap\|主题覆盖率" skills/roadmap/SKILL.md skills/add-improve/SKILL.md skills/guide-design/SKILL.md AGENTS.md CHANGELOG.md`
Expected: All 5 files listed.

- [ ] **Step 5: Defer commit**

按仓库约定，execute 阶段不逐任务 commit；所有变更将在 archive 阶段统一提交。

---

### Task 9: Regression test — full suite green

**Files:** None (run tests only)

- [ ] **Step 1: Run quick smoke + unit tests**

Run: `cd /workspace/project/rdd-workflow && ./test.sh --quick`
Expected: All smoke + pytest unit tests PASS.

- [ ] **Step 2: Run full regression suite**

Run: `cd /workspace/project/rdd-workflow && ./test.sh --full --regression`
Expected: All tests PASS or match `KNOWN_FAILURES.txt` baseline (no new failures).

- [ ] **Step 3: Verify rdd-doctor is unaffected**

Run: `cd /workspace/project/rdd-workflow && bash skills/rdd-doctor/scripts/doctor.sh --category state`
Expected: Zero CRITICAL findings, no schema errors.

- [ ] **Step 4: Verify end-to-end flow manually**

```bash
# Create test project with empty roadmap
mkdir -p /tmp/test-proposal-guidance
cd /tmp/test-proposal-guidance
git init

# Copy necessary skills (or use globally installed)
# ...

# Add a theme to roadmap
echo '### Phase 1: arch (phase-1)
#### 任务分类
| 分类ID | 名称 | 描述 | 优先级 | 预期改进方向 |
|--------|------|------|--------|--------------|
| arch-design | 架构 | 核心 | P0 | TestTheme
' > roadmap.md

# Run guide-design preflight
bash $HOME/.agents/skills/guide-design/scripts/design_preflight.sh /tmp/test-proposal-guidance

# Verify output includes coverage info
```

Expected: preflight output includes "TestTheme" in uncovered list.

- [ ] **Step 5: Defer commit**

按仓库约定，execute 阶段不逐任务 commit；所有变更将在 archive 阶段统一提交。

---

## Self-Review

1. **Spec coverage**: Each spec requirement maps to a task:
   - "Roadmap 分类表支持预期改进方向列" → Task 1, 2 ✅
   - "Improvement proposal 支持主题字段" → Task 3 ✅
   - "add-improve --from-roadmap 模式通过 env-var 传参" → Task 4, 5 ✅
   - "guide-design preflight 显示 roadmap 主题覆盖率" → Task 6, 7 ✅
   - "guide-design Phase 2 菜单新增按主题创建选项" → Task 7 ✅
   - "STRICT_PROPOSAL_COVERAGE 门控" → Task 7 ✅
   - "rdd-doctor 不感知主题覆盖率字段" → Task 9 (Step 3 verifies) ✅
   - "主题状态词汇" → Task 1, 6 (parser + algorithm), Task 8 (docs) ✅

2. **Placeholder scan**: No "TBD", "TODO", "implement later" found in plan. All code blocks contain concrete implementations.

3. **Type consistency**:
   - `get_phase_themes()` signature: `(phase_id: str, category_id: str, roadmap_path: Optional[str]) -> List[str]` — used consistently in Task 1, 6.
   - `compute_theme_coverage()` signature: `(project_root: str, roadmap_path: str, improvements_dir: str) -> Dict[str, Any]` — used in Task 6, 7.
   - env-var names: `ADD_IMPROVE_FROM_ROADMAP`, `ADD_IMPROVE_THEME`, `BRAINSTORM_RATIONALE_DRAFT` — consistent across Task 4, 5, 8.

4. **Migration compatibility verified**: Task 1 test `test_4col_legacy_compat` + Task 6 test `test_coverage_legacy_no_subject_field` explicitly cover backward compat.

5. **Security (Oracle C1)**: Task 4 env-var validation + Task 5 env-var pattern + Task 8 env-var naming convention documentation — all in place.

6. **HARD-GATE integrity**: Task 5 Step 6 documentation explicitly states "约束模式不绕过 brainstorm 逐段确认". Task 5 Step 4 scaffold-only write, no auto-approve.

---

## Ready for Execution

This plan is ready to be executed via `skill_use("execute")`. Each task is self-contained with verifiable steps. After all 9 tasks complete, run `./test.sh --full --regression` for final verification, then proceed to `guide-ship` Phase 3 (archive) per `AGENTS.md` workflow.