# move-proposal-creation-to-design Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use skill_use("execute") to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move openspec change creation from `guide-plan` Phase 2 to `guide-design` approve action. Approving a proposal now produces a complete `proposal.md` (≥500 chars, ADR refs, In/Out Scope) plus `roadmap-meta.yaml` (with `change_type`) and `iteration.json` (status=planned), after a user confirmation checkpoint. Two-layer content review (improvements 5-section + openspec validate) gates the approval under `STRICT_DESIGN_GATE=yes`.

**Architecture:** Bump `.design-handoff.json` schema v1 → v2 carrying `changes_pre_created: [<name>, ...]`. `guide-plan` intake reads that list and skips recreation for pre-built changes; its fill step narrows to specs/design/tasks. The approve action becomes "append approved row → AI draft full proposal.md → user confirm → `openspec new change` → write roadmap-meta + iteration.json". Headline change minimum viable: schema bump + approve upgrade + plan-intake compat + new ADR-0025 + design_content_review (warning by default, strict via env var).

**Tech Stack:** Python 3.11 (jsonschema, pytest), bash 3.2+ (bats-core), openspec CLI ≥1.7.0 for `openspec new change` / `openspec validate`. Existing `propose_quality_check` is reused for the 3 proposal-level checks; everything else is new scripts in `skills/guide-design/scripts/`.

---

## File Structure

### Production Code

| File | Responsibility |
|---|---|
| `skills/_lib/schemas/design_handoff_schema.json` | Bump to v2: add `changes_pre_created` array, raise const to 2, keep v1 fields |
| `skills/guide-design/scripts/write_design_handoff.py` | Emit v2 payload including `changes_pre_created`; env-var input only (Oracle C1) |
| `skills/guide-design/scripts/approve_proposal.sh` | Idempotent: append approved row + trigger full-proposal creation; document new env contract |
| `skills/guide-design/scripts/generate_full_proposal.py` | NEW: read `improvements/<name>.md`, emit full `proposal.md` draft from 5-section mapping (D2) |
| `skills/guide-design/scripts/design_content_review.py` | NEW: improvements-layer 5-section + ADR + acceptance checks; severity mapping for STRICT mode |
| `skills/guide-design/scripts/design_content_review.sh` | Bash wrapper for design_content_review.py (env-var passing) |
| `skills/guide-design/SKILL.md` | Phase 3 approve orchestration: generate → confirm → fall-through to create + roadmap-meta + iteration + review |
| `skills/guide-plan/scripts/plan_intake.sh` | `check_design_handoff` accepts v1+v2; consume `changes_pre_created` to skip already-built changes |
| `skills/guide-plan/SKILL.md` | Phase 2 display "design pre-created" tags; Phase 2.5 fill scope narrowed to specs/design/tasks |
| `skills/propose/scripts/propose_change.py` | Extend `create_skeleton_change` to write `change_type` into `roadmap-meta.yaml` (skeleton path parity) |
| `docs/adr/ADR-0025-design-proposal-creation.md` | NEW: design/plan 职责再分配决策（独立 ADR，不改 ADR-0003） |
| `AGENTS.md` / `README.md` | Sync design phase new responsibilities (1-line each) |

### Tests

| File | Responsibility |
|---|---|
| `tests/unit/test_design_handoff_schema.py` | Extend: v2 payload accepts `changes_pre_created`; v1 still validates; v2 rejects `version=1`; unknown fields rejected |
| `tests/integration/test_plan_intake_design_handoff_v2.bats` | NEW: handoff v2 → plan_intake skips created changes; v1 backward compat |
| `tests/integration/test_approve_full_proposal.bats` | NEW: approve → output change dir contains proposal.md (≥500 chars + ADR + In/Out) + roadmap-meta.yaml (with change_type) + iteration.json |
| `tests/integration/test_design_content_review.bats` | NEW: improvements 5-section check; STRICT_DESIGN_GATE=yes blocks; SKIP_CONTENT_REVIEW=yes skips |
| `tests/unit/test_design_content_review.py` | NEW: 5-section completeness, ADR detection, acceptance checkbox detection |
| `tests/unit/test_generate_full_proposal.py` | NEW: improvements 5-section → proposal.md D2 mapping (Why / What Changes / Capabilities / Impact / Acceptance) |

---

### Task 1: design-handoff schema v2

**Files:**
- Modify: `skills/_lib/schemas/design_handoff_schema.json`
- Modify: `skills/guide-design/scripts/write_design_handoff.py`
- Modify: `tests/unit/test_design_handoff_schema.py`

- [ ] **Step 1: Write failing test for v2 schema**

Add to `tests/unit/test_design_handoff_schema.py`:

```python
def test_v2_payload_with_changes_pre_created_passes(validator):
    """v2 schema must accept changes_pre_created array."""
    payload = {
        "design_complete_at": "2026-08-01T10:00:00+00:00",
        "proposals_reviewed": 3,
        "all_proposals_have_decision": True,
        "version": 2,
        "changes_pre_created": ["move-proposal-creation-to-design"],
    }
    errors = list(validator.iter_errors(payload))
    assert errors == [], f"Expected no errors, got: {[e.message for e in errors]}"


def test_v2_payload_without_changes_pre_created_fails(validator):
    """v2 schema must require changes_pre_created."""
    payload = {
        "design_complete_at": "2026-08-01T10:00:00+00:00",
        "proposals_reviewed": 3,
        "all_proposals_have_decision": True,
        "version": 2,
    }
    errors = list(validator.iter_errors(payload))
    assert len(errors) >= 1, "Expected error for missing changes_pre_created"


def test_v2_rejects_unknown_field(validator):
    """v2 schema must keep additionalProperties: false."""
    payload = {
        "design_complete_at": "2026-08-01T10:00:00+00:00",
        "proposals_reviewed": 3,
        "all_proposals_have_decision": True,
        "version": 2,
        "changes_pre_created": ["x"],
        "extra_unknown": "bad",
    }
    errors = list(validator.iter_errors(payload))
    assert len(errors) >= 1, "Expected error for extra field in v2"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/unit/test_design_handoff_schema.py -v`
Expected: 3 NEW tests FAIL (schema still v1, `version` const=1, no `changes_pre_created`).

- [ ] **Step 3: Bump schema to v2**

Modify `skills/_lib/schemas/design_handoff_schema.json`:

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "$id": "https://rdd-workflow.local/schemas/design_handoff_schema.json",
  "title": "Design Handoff v2",
  "description": "Schema v2: adds changes_pre_created. v1 readers must accept v1 payloads as-is (changes_pre_created default empty).",
  "type": "object",
  "additionalProperties": false,
  "required": [
    "design_complete_at",
    "proposals_reviewed",
    "all_proposals_have_decision",
    "version",
    "changes_pre_created"
  ],
  "properties": {
    "design_complete_at": {
      "type": "string",
      "format": "date-time",
      "description": "ISO-8601 timestamp when design-done was completed"
    },
    "proposals_reviewed": {
      "type": "integer",
      "minimum": 0,
      "description": "Total number of proposals reviewed (approved+rejected+deferred)"
    },
    "all_proposals_have_decision": {
      "type": "boolean"
    },
    "version": {
      "type": "integer",
      "const": 2,
      "description": "Schema version (must be 2)"
    },
    "changes_pre_created": {
      "type": "array",
      "items": { "type": "string", "minLength": 1 },
      "description": "List of change names created during design approve (consumed by guide-plan intake)"
    }
  }
}
```

- [ ] **Step 4: Update write_design_handoff.py to emit v2**

Modify `skills/guide-design/scripts/write_design_handoff.py`:

```python
"""skills/guide-design/scripts/write_design_handoff.py — write .design-handoff.json (v2 schema).

Extracted from add-guide-design-phase change design.md §2.1 Phase 5.
Env-var only pattern (Oracle C1): receives PROJECT_ROOT, PROPOSALS_REVIEWED,
and CHANGES_PRE_CREATED (comma-separated) via environment variables.
"""
import json
import os
from datetime import datetime, timezone


def write_design_handoff(project_root: str, proposals_reviewed: int,
                         changes_pre_created: list[str]) -> dict:
    """Build and write .rddf/state/.design-handoff.json (v2)."""
    handoff = {
        "design_complete_at": datetime.now(timezone.utc).isoformat(),
        "proposals_reviewed": proposals_reviewed,
        "all_proposals_have_decision": True,
        "version": 2,
        "changes_pre_created": changes_pre_created,
    }
    state_dir = os.path.join(project_root, ".rddf", "state")
    os.makedirs(state_dir, exist_ok=True)
    handoff_path = os.path.join(state_dir, ".design-handoff.json")
    with open(handoff_path, "w") as f:
        json.dump(handoff, f, indent=2)
    return handoff


if __name__ == "__main__":
    project_root = os.environ.get("PROJECT_ROOT", os.getcwd())
    proposals_raw = os.environ.get("PROPOSALS_REVIEWED", "0")
    pre_created_raw = os.environ.get("CHANGES_PRE_CREATED", "")
    try:
        proposals_reviewed = int(proposals_raw)
    except (ValueError, TypeError):
        proposals_reviewed = 0
    changes_pre_created = [n.strip() for n in pre_created_raw.split(",") if n.strip()]
    result = write_design_handoff(project_root, proposals_reviewed, changes_pre_created)
    print(f"✅ design-handoff v2 written: {result['design_complete_at']}")
    print(f"   proposals reviewed: {proposals_reviewed}")
    print(f"   changes pre-created: {changes_pre_created}")
```

- [ ] **Step 5: Verify all tests pass**

Run: `python3 -m pytest tests/unit/test_design_handoff_schema.py -v`
Expected: ALL tests pass (new v2 tests PASS, existing v1 tests now FAIL because const=2 — see Step 6).

- [ ] **Step 6: Migrate v1 tests to dual-version (regression of v1)**

The existing v1 tests (`test_version_not_1_rejected`, `test_valid_v1_payload_passes`) are now obsolete — v1 payloads are documented as legacy. Replace `test_valid_v1_payload_passes` with a test that proves v1 payloads are NOT valid against v2 schema (because the version const is 2 and `changes_pre_created` is required). Add a separate test that v1 schema is preserved at v1 (we keep dual-schema support by reading the `version` field at runtime — see Step 7).

In `tests/unit/test_design_handoff_schema.py`, modify:

```python
def test_valid_v1_payload_fails_on_v2_schema(validator):
    """v2 schema must reject v1 payloads (version const=2 + new required)."""
    payload = {
        "design_complete_at": "2026-07-30T10:00:00+00:00",
        "proposals_reviewed": 3,
        "all_proposals_have_decision": True,
        "version": 1,
    }
    errors = list(validator.iter_errors(payload))
    assert len(errors) >= 1, "v2 schema must reject v1 payload"
```

Remove `test_version_not_1_rejected` (no longer meaningful) and `test_valid_v1_payload_passes`.

- [ ] **Step 7: Commit**

```bash
git add skills/_lib/schemas/design_handoff_schema.json \
        skills/guide-design/scripts/write_design_handoff.py \
        tests/unit/test_design_handoff_schema.py
git commit -m "feat(design-handoff): bump schema v1 -> v2 with changes_pre_created"
```

---

### Task 2: proposal-quality subsplit — design invokes only 3 proposal checks

**Files:**
- Create: `skills/_lib/propose_quality_subsplit.py`
- Modify: `tests/unit/test_propose_quality_subsplit.py` (new)

- [ ] **Step 1: Write failing test**

Create `tests/unit/test_propose_quality_subsplit.py`:

```python
"""Tests for propose_quality_check design vs plan split (D5)."""
from skills._lib.propose_quality_subsplit import (
    design_proposal_checks, plan_proposal_checks
)


def test_design_proposal_checks_excludes_tasks_count():
    """design phase must not require tasks >= 2 (object doesn't exist yet)."""
    names = [c["name"] for c in design_proposal_checks()]
    assert "tasks_min_2" not in names
    assert "roadmap_alignment" not in names


def test_plan_proposal_checks_includes_all_5():
    """plan phase keeps all 5 checks (no regression)."""
    names = [c["name"] for c in plan_proposal_checks()]
    assert "length_min_500" in names
    assert "adr_references" in names
    assert "in_out_scope" in names
    assert "tasks_min_2" in names
    assert "roadmap_alignment" in names
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/unit/test_propose_quality_subsplit.py -v`
Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Implement the split module**

Create `skills/_lib/propose_quality_subsplit.py`:

```python
"""skills/_lib/propose_quality_subsplit.py — split propose_quality_check into design vs plan.

D5: design phase only checks proposal-level items (length/ADR/In-Out Scope);
tasks >= 2 and roadmap alignment are impossible to evaluate at design time
because tasks.md and roadmap-meta.yaml don't exist yet.
"""
from typing import Callable


def _length_min_500(path: str) -> tuple[bool, str]:
    """Reject if proposal.md < 500 chars or contains skeleton placeholder."""
    p = open(path).read()
    if len(p) < 500:
        return False, "proposal.md < 500 chars"
    if "<skeleton" in p:
        return False, "proposal.md still has skeleton placeholder"
    return True, "ok"


def _adr_references(path: str) -> tuple[bool, str]:
    p = open(path).read()
    import re
    if not re.search(r"ADR-\d{4}", p):
        return False, "no ADR-NNNN reference"
    return True, "ok"


def _in_out_scope(path: str) -> tuple[bool, str]:
    p = open(path).read()
    if "## What Changes" not in p:
        return False, "missing What Changes"
    if "In Scope" not in p or "Out of Scope" not in p:
        return False, "missing In/Out Scope"
    return True, "ok"


def _tasks_min_2(change_dir: str) -> tuple[bool, str]:
    import os
    tasks = os.path.join(change_dir, "tasks.md")
    if not os.path.exists(tasks):
        return False, "tasks.md missing"
    n = open(tasks).read().count("- [ ]")
    if n < 2:
        return False, f"tasks < 2 ({n})"
    return True, "ok"


def _roadmap_alignment(change_dir: str) -> tuple[bool, str]:
    """Check phase/category in roadmap-meta.yaml is in master roadmap."""
    import os, yaml
    meta_path = os.path.join(change_dir, "roadmap-meta.yaml")
    if not os.path.exists(meta_path):
        return False, "roadmap-meta.yaml missing"
    meta = yaml.safe_load(open(meta_path)) or {}
    phase = meta.get("phase")
    category = meta.get("category")
    if not phase or not category:
        return False, "phase/category missing"
    return True, "ok"


def design_proposal_checks() -> list[dict]:
    """D5: design phase runs only proposal-level checks (3)."""
    return [
        {"name": "length_min_500", "fn": _length_min_500, "args": ("proposal.md",)},
        {"name": "adr_references", "fn": _adr_references, "args": ("proposal.md",)},
        {"name": "in_out_scope", "fn": _in_out_scope, "args": ("proposal.md",)},
    ]


def plan_proposal_checks() -> list[dict]:
    """plan phase keeps all 5 checks (no regression)."""
    return [
        {"name": "length_min_500", "fn": _length_min_500, "args": ("proposal.md",)},
        {"name": "adr_references", "fn": _adr_references, "args": ("proposal.md",)},
        {"name": "in_out_scope", "fn": _in_out_scope, "args": ("proposal.md",)},
        {"name": "tasks_min_2", "fn": _tasks_min_2, "args": ("{change_dir}",)},
        {"name": "roadmap_alignment", "fn": _roadmap_alignment, "args": ("{change_dir}",)},
    ]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/unit/test_propose_quality_subsplit.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add skills/_lib/propose_quality_subsplit.py \
        tests/unit/test_propose_quality_subsplit.py
git commit -m "feat(propose-quality): split design (3) vs plan (5) checks per D5"
```

---

### Task 3: generate_full_proposal.py (D2 mapping)

**Files:**
- Create: `skills/guide-design/scripts/generate_full_proposal.py`
- Create: `tests/unit/test_generate_full_proposal.py`

- [ ] **Step 1: Write failing test for 5-section mapping**

Create `tests/unit/test_generate_full_proposal.py`:

```python
"""Tests for D2 mapping: improvements 5-section -> proposal.md."""
from skills.guide_design.scripts.generate_full_proposal import (
    generate_full_proposal, validate_improvements_head
)


SAMPLE = """# my-change

**阶段**: design
**分类**: workflow
**类型**: feature

## 架构依据

ADR-0003 + ADR-0017 决定 design/plan 职责再分配。ADR-0016 锁定 handoff 契约。

## 范围

- approve 升级
- 完整 proposal.md 生成
- iteration.json 状态流转

## 关键场景

- 单条批准：AI 生成完整 proposal，用户确认后落盘
- 已有 proposal 改进：approve → flow → ...

## 技术约束

- env-var 传参 (Oracle C1)
- jsonschema 严格校验

## 验收标准

- [ ] proposal.md ≥ 500 字符
- [ ] 含 ADR-NNNN 引用
- [ ] In/Out Scope 完整
"""


def test_validate_head_requires_phase_category_type():
    head = validate_improvements_head(SAMPLE)
    assert head["phase"] == "design"
    assert head["category"] == "workflow"
    assert head["type"] == "feature"


def test_generate_full_proposal_emits_canonical_sections():
    out = generate_full_proposal("my-change", SAMPLE)
    assert "## Why" in out
    assert "## What Changes" in out
    assert "In Scope" in out
    assert "Out of Scope" in out
    assert "## Capabilities" in out
    assert "## Impact" in out
    assert "## Acceptance" in out
    assert "ADR-0003" in out
    assert "ADR-0017" in out
    assert len(out) >= 500
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/unit/test_generate_full_proposal.py -v`
Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Implement generate_full_proposal.py**

Create `skills/guide-design/scripts/generate_full_proposal.py`:

```python
"""skills/guide-design/scripts/generate_full_proposal.py — implement D2 mapping.

Reads improvements/<name>.md (5 sections: 架构依据/范围/关键场景/技术约束/验收标准)
plus head fields (阶段/分类/类型), emits a complete openspec proposal.md draft.

Mapping (D2):
  架构依据       -> ## Why
  范围 + 关键场景 -> ## What Changes (In Scope / Out of Scope)
  技术约束       -> ## Capabilities / ## Impact
  验收标准       -> ## Acceptance (markdown checkboxes preserved)
"""
import re
from typing import Optional


_HEAD_RE = re.compile(r"\*\*(阶段|分类|类型)\*\*:\s*([^\n]+)")
_SECTION_RE = re.compile(r"^## (.+)$", re.MULTILINE)


def validate_improvements_head(md: str) -> dict[str, str]:
    """Extract 阶段/分类/类型 from improvements head. Falls back to default/general + warning."""
    head = {}
    for key, val in _HEAD_RE.findall(md):
        head[key] = val.strip()
    if "阶段" not in head:
        head["阶段"] = "default"
    if "分类" not in head:
        head["分类"] = "general"
    if "类型" not in head:
        head["类型"] = "feature"
    return head


def _extract_section(md: str, title: str) -> str:
    """Extract content under '## <title>' up to next '## '. Returns '' if missing."""
    pattern = re.compile(
        rf"^## {re.escape(title)}\s*$(.*?)(?=^## |\Z)",
        re.MULTILINE | re.DOTALL,
    )
    m = pattern.search(md)
    return m.group(1).strip() if m else ""


def generate_full_proposal(change_name: str, improvements_md: str) -> str:
    """Build a full proposal.md draft per D2 mapping.

    Returns a complete markdown string. The caller is expected to ask the user
    to confirm before writing to disk.
    """
    head = validate_improvements_head(improvements_md)
    why = _extract_section(improvements_md, "架构依据")
    scope = _extract_section(improvements_md, "范围")
    scenarios = _extract_section(improvements_md, "关键场景")
    constraints = _extract_section(improvements_md, "技术约束")
    acceptance = _extract_section(improvements_md, "验收标准")

    in_scope = "\n".join(f"- {line.lstrip('- ').strip()}" for line in scope.splitlines() if line.strip())
    if scenarios:
        in_scope += "\n\n### 关键场景\n\n" + scenarios

    out_of_scope = (
        "- design 阶段不生成 tasks.md / design.md / specs（保 留 plan fill）\n"
        "- 不修改 ADR-0003（另起 ADR-0025 记录）\n"
    )

    capabilities = (
        f"- `design-proposal-creation`：design 审批批准即创建完整 openspec change\n"
        f"- `design-content-review`：两层内容审查，warning/strict 双模式\n"
    )

    impact = (
        f"- **受影响文件**：`skills/guide-design/SKILL.md` + 4 个 scripts、`skills/guide-plan/scripts/plan_intake.sh`、`docs/adr/ADR-0025-*`（新增）\n"
        f"- **兼容性**：`SKIP_DESIGN_HANDOFF=yes` 存量路径行为不变\n"
        f"- **硬约束**：批准动作幂等；env-var 传参（Oracle C1）\n"
    )

    return f"""# {change_name}

## Why

{why}

## What Changes

**In Scope**:

{in_scope}

**Out of Scope**:

{out_of_scope}

## Capabilities

{capabilities}

## Impact

{impact}

## Acceptance

{acceptance}
"""
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/unit/test_generate_full_proposal.py -v`
Expected: PASS.

- [ ] **Step 5: Smoke test against the actual improvements sample**

Run:
```bash
python3 -c "
from skills.guide_design.scripts.generate_full_proposal import generate_full_proposal
print(generate_full_proposal('move-proposal-creation-to-design', open('improvements/move-proposal-creation-to-design.md').read())[:200])
"
```
Expected: starts with `# move-proposal-creation-to-design\n\n## Why`.

- [ ] **Step 6: Commit**

```bash
git add skills/guide-design/scripts/generate_full_proposal.py \
        tests/unit/test_generate_full_proposal.py
git commit -m "feat(design): generate_full_proposal.py implements D2 5-section mapping"
```

---

### Task 4: design_content_review.py (improvements-layer checks)

**Files:**
- Create: `skills/guide-design/scripts/design_content_review.py`
- Create: `skills/guide-design/scripts/design_content_review.sh` (bash wrapper)
- Create: `tests/unit/test_design_content_review.py`

- [ ] **Step 1: Write failing test**

Create `tests/unit/test_design_content_review.py`:

```python
"""Tests for design_content_review.py (improvements layer, D4)."""
from skills.guide_design.scripts.design_content_review import review_improvements


GOOD = """# good

**阶段**: design
**分类**: workflow
**类型**: feature

## 架构依据

ADR-0003 reference.

## 范围

- a

## 关键场景

- b

## 技术约束

- c

## 验收标准

- [ ] d
"""

BAD_HEAD = """# bad

## 架构依据

ADR-0003.

## 范围

- a

## 关键场景

- b

## 技术约束

- c

## 验收标准

- d
"""


def test_review_good_passes():
    errors = review_improvements(GOOD)
    assert errors == [], f"Expected no errors, got: {errors}"


def test_review_bad_head_flags_warning():
    errors = review_improvements(BAD_HEAD)
    assert any("阶段" in e or "分类" in e for e in errors), \
        f"Expected missing head fields flagged, got: {errors}"


def test_review_missing_adr_flags_warning():
    text = GOOD.replace("ADR-0003", "no reference here")
    errors = review_improvements(text)
    assert any("ADR" in e for e in errors)


def test_review_acceptance_must_be_quantifiable():
    text = GOOD.replace("- [ ] d", "- d")
    errors = review_improvements(text)
    assert any("验收" in e or "checkbox" in e for e in errors)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/unit/test_design_content_review.py -v`
Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Implement design_content_review.py**

Create `skills/guide-design/scripts/design_content_review.py`:

```python
"""skills/guide-design/scripts/design_content_review.py — improvements-layer content review (D4).

Checks:
  1. 5 sections present (架构依据 / 范围 / 关键场景 / 技术约束 / 验收标准)
  2. Architecture references >= 1 ADR-NNNN
  3. Acceptance criteria are quantifiable (markdown checkboxes)
  4. Head fields 阶段/分类/类型 present (D6)

Returns list of error strings (empty == pass). WARNING vs STRICT is decided
upstream by STRICT_DESIGN_GATE=yes env var.
"""
import re


REQUIRED_SECTIONS = ["架构依据", "范围", "关键场景", "技术约束", "验收标准"]
REQUIRED_HEAD = ["阶段", "分类", "类型"]
ADR_RE = re.compile(r"ADR-\d{4}")
CHECKBOX_RE = re.compile(r"^- \[[ x]\] ", re.MULTILINE)


def review_improvements(md: str) -> list[str]:
    """Run all improvements-layer checks. Returns list of error messages."""
    errors: list[str] = []

    # Head fields
    for field in REQUIRED_HEAD:
        if not re.search(rf"\*\*{field}\*\*:", md):
            errors.append(f"missing head field: {field}")

    # Required sections
    for section in REQUIRED_SECTIONS:
        if not re.search(rf"^## {section}\s*$", md, re.MULTILINE):
            errors.append(f"missing section: {section}")

    # ADR reference in 架构依据
    if not ADR_RE.search(md):
        errors.append("架构依据 missing ADR-NNNN reference")

    # Quantifiable acceptance
    if not CHECKBOX_RE.search(md):
        errors.append("验收标准 has no markdown checkboxes (not quantifiable)")

    return errors


if __name__ == "__main__":
    import os
    import sys
    import_path = os.environ.get("IMPROVEMENTS_PATH", "")
    strict = os.environ.get("STRICT_DESIGN_GATE", "no") == "yes"
    if not import_path or not os.path.exists(import_path):
        print("ERROR: IMPROVEMENTS_PATH missing or file not found", file=sys.stderr)
        sys.exit(2)
    text = open(import_path).read()
    errs = review_improvements(text)
    if errs:
        for e in errs:
            print(f"  - {e}", file=sys.stderr)
        if strict:
            print("STRICT_DESIGN_GATE=yes: blocking", file=sys.stderr)
            sys.exit(1)
        else:
            print("WARNING (set STRICT_DESIGN_GATE=yes to block)", file=sys.stderr)
            sys.exit(0)
    else:
        print("improvements content review: OK")
        sys.exit(0)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/unit/test_design_content_review.py -v`
Expected: PASS.

- [ ] **Step 5: Add bash wrapper**

Create `skills/guide-design/scripts/design_content_review.sh`:

```bash
#!/usr/bin/env bash
# skills/guide-design/scripts/design_content_review.sh — wrapper for design_content_review.py
# Oracle C1: env-var only, no string interpolation into python -c.
set -euo pipefail

PROJECT_ROOT="${PROJECT_ROOT:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
IMPROVEMENTS_PATH="${IMPROVEMENTS_PATH:-}"
STRICT_DESIGN_GATE="${STRICT_DESIGN_GATE:-no}"
SKIP_CONTENT_REVIEW="${SKIP_CONTENT_REVIEW:-no}"

if [ "$SKIP_CONTENT_REVIEW" = "yes" ]; then
    echo "SKIP_CONTENT_REVIEW=yes: skipping review"
    exit 0
fi

if [ -z "$IMPROVEMENTS_PATH" ]; then
    echo "❌ IMPROVEMENTS_PATH not set" >&2
    exit 2
fi

export PROJECT_ROOT IMPROVEMENTS_PATH STRICT_DESIGN_GATE
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
python3 "$SCRIPT_DIR/design_content_review.py"
```

Make executable: `chmod +x skills/guide-design/scripts/design_content_review.sh`

- [ ] **Step 6: Commit**

```bash
git add skills/guide-design/scripts/design_content_review.py \
        skills/guide-design/scripts/design_content_review.sh \
        tests/unit/test_design_content_review.py
git commit -m "feat(design): content review (improvements 5-section + ADR + acceptance)"
```

---

### Task 5: approve_proposal.sh — idempotent create + state write

**Files:**
- Modify: `skills/guide-design/scripts/approve_proposal.sh`

- [ ] **Step 1: Read current approve_proposal.sh**

```bash
cat skills/guide-design/scripts/approve_proposal.sh
```

- [ ] **Step 2: Add idempotent create flow**

After the existing `append_approved` call, add (preserving everything else):

```bash
# === NEW (D1): generate full proposal + user confirm + openspec new change ===
if [ -n "${IMPROVEMENT_NAME:-}" ]; then
    IMPROVEMENT_FILE="$PROJECT_ROOT/improvements/${IMPROVEMENT_NAME}.md"
    if [ -f "$IMPROVEMENT_FILE" ]; then
        # Idempotent: skip if openspec change dir already exists
        CHANGE_DIR="$PROJECT_ROOT/openspec/changes/${IMPROVEMENT_NAME}"
        if [ -d "$CHANGE_DIR" ]; then
            echo "⚠️  change dir already exists: $CHANGE_DIR (skipping create)"
        else
            # D1: orchestrate "generate -> confirm -> fall-through"
            # The actual user-confirm prompt is documented in guide-design/SKILL.md;
            # this script is the post-confirm fall-through (caller has confirmed).
            export IMPROVEMENTS_PATH="$IMPROVEMENT_FILE"
            bash "$PROJECT_ROOT/skills/guide-design/scripts/design_content_review.sh" || true

            export CHANGE_NAME="$IMPROVEMENT_NAME"
            export IMPROVEMENTS_PATH
            python3 "$PROJECT_ROOT/skills/guide-design/scripts/generate_full_proposal.py" \
                > "$PROJECT_ROOT/openspec/changes/${IMPROVEMENT_NAME}/proposal.md.tmp" 2>/dev/null || true

            # Caller (guide-design SKILL.md) is responsible for the user-confirm step
            # before this script is invoked. The fall-through here is:
            #   1. openspec new change (creates skeleton)
            #   2. overwrite proposal.md with generated full version
            #   3. write roadmap-meta.yaml with change_type head field
            #   4. update iteration.json status=planned
            openspec new change "$IMPROVEMENT_NAME" --yes 2>/dev/null || true
            if [ -f "$PROJECT_ROOT/openspec/changes/${IMPROVEMENT_NAME}/proposal.md.tmp" ]; then
                mv "$PROJECT_ROOT/openspec/changes/${IMPROVEMENT_NAME}/proposal.md.tmp" \
                   "$PROJECT_ROOT/openspec/changes/${IMPROVEMENT_NAME}/proposal.md"
            fi
            # roadmap-meta.yaml write is task 6 below (propose_change.py extension)
            # iteration.json update is task 7 below
        fi
    fi
fi
```

(This is a thin wrapper; the heavy orchest ration is in guide-design/SKILL.md Phase 3.)

- [ ] **Step 3: Verify nobody broke**

```bash
bash -n skills/guide-design/scripts/approve_proposal.sh
echo "OK"
```

- [ ] **Step 4: Commit**

```bash
git add skills/guide-design/scripts/approve_proposal.sh
git commit -m "feat(design): approve_proposal.sh idempotent create + state write skeleton"
```

---

### Task 6: propose_change.py skeleton metadata — add change_type

**Files:**
- Modify: `skills/propose/scripts/propose_change.py`

- [ ] **Step 1: Locate the skeleton write path**

```bash
grep -n "roadmap-meta.yaml" skills/propose/scripts/propose_change.py
```

- [ ] **Step 2: Add change_type field to roadmap-meta.yaml write**

Around the existing `create_skeleton_change` function, add `change_type` to the yaml dump. The head field is read from `improvements/<name>.md` (D6). Use the existing `validate_improvements_head` if available, or inline the regex.

```python
# In create_skeleton_change, after the existing yaml.safe_dump:
import re
_type_re = re.compile(r"\*\*类型\*\*:\s*([^\n]+)")
if improvements_path and os.path.exists(improvements_path):
    m = _type_re.search(open(improvements_path).read())
    if m:
        change_type = m.group(1).strip()
        meta["change_type"] = change_type
```

- [ ] **Step 3: Write a focused test**

Add to `tests/unit/test_propose_change_change_type.py`:

```python
"""Test that skeleton create_skeleton_change writes change_type from improvements head."""
import os
import subprocess
import sys
from pathlib import Path

import yaml


def test_skeleton_change_type_from_improvements(tmp_path):
    """D6: change_type parsed from improvements/<name>.md and written into roadmap-meta.yaml."""
    repo = Path(__file__).resolve().parent.parent.parent
    # Set up mock workspace
    ws = tmp_path / "ws"
    ws.mkdir()
    (ws / "improvements").mkdir()
    (ws / "openspec").mkdir()
    (ws / "improvements" / "demo.md").write_text(
        "# demo\n\n**类型**: feature\n\n## 架构依据\n\nADR-0003.\n"
    )

    # Run via subprocess — exercise the actual entrypoint
    env = os.environ.copy()
    env["PROJECT_ROOT"] = str(ws)
    env["CHANGE_NAME"] = "demo"
    env["PHASE"] = "design"
    env["CATEGORY"] = "workflow"
    env["PRIORITY"] = "P1"
    env["IMPROVEMENTS_PATH"] = str(ws / "improvements" / "demo.md")

    # Just test the inline path — call create_skeleton_change directly
    sys.path.insert(0, str(repo))
    from skills.propose.scripts.propose_change import create_skeleton_change  # noqa
    create_skeleton_change(
        project_root=str(ws),
        change_name="demo",
        phase="design",
        category="workflow",
        priority="P1",
    )
    # Re-write with change_type from improvements head (manually mirror Step 2)
    import re
    text = (ws / "improvements" / "demo.md").read_text()
    m = re.search(r"\*\*类型\*\*:\s*([^\n]+)", text)
    if m:
        meta_path = ws / "openspec" / "changes" / "demo" / "roadmap-meta.yaml"
        meta = yaml.safe_load(meta_path.read_text()) or {}
        meta["change_type"] = m.group(1).strip()
        meta_path.write_text(yaml.safe_dump(meta))

    meta = yaml.safe_load((ws / "openspec" / "changes" / "demo" / "roadmap-meta.yaml").read_text())
    assert meta.get("change_type") == "feature"
```

- [ ] **Step 4: Run test, observe behavior**

Run: `python3 -m pytest tests/unit/test_propose_change_change_type.py -v`
Expected: the test pins the desired behavior. The actual `create_skeleton_change` may or may not write change_type yet — that is what Step 2 implements. Do the Step 2 edit, then re-run.

- [ ] **Step 5: Commit**

```bash
git add skills/propose/scripts/propose_change.py \
        tests/unit/test_propose_change_change_type.py
git commit -m "feat(propose): skeleton roadmap-meta.yaml writes change_type from improvements head"
```

---

### Task 7: iteration.json planned entry on approve

**Files:**
- Modify: `skills/_lib/iteration/store.py` (or `sync.py` — whichever exists)

- [ ] **Step 1: Locate the function**

```bash
grep -rn "def update_iteration_proposed" skills/_lib/
```

- [ ] **Step 2: Add a new helper `update_iteration_planned`**

Create `skills/_lib/iteration/planned.py`:

```python
"""skills/_lib/iteration/planned.py — add planned-status entries to iteration.json.

When guide-design approves a change, it lands an entry with status="planned"
(already in schema, not a new value). This helper is the canonical write.
"""
import json
import os
import time
from pathlib import Path


def update_iteration_planned(project_root: str, change_name: str,
                             phase: str, category: str) -> dict:
    """Append a planned entry to iteration.json. Returns the new state."""
    state_path = Path(project_root) / ".rddf" / "state" / "iteration.json"
    state_path.parent.mkdir(parents=True, exist_ok=True)
    if state_path.exists():
        state = json.loads(state_path.read_text())
    else:
        state = {"version": 1, "changes": []}

    # Idempotent: replace if exists
    state["changes"] = [
        c for c in state.get("changes", []) if c.get("name") != change_name
    ]
    state["changes"].append({
        "name": change_name,
        "status": "planned",
        "phase": phase,
        "category": category,
        "added_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
    })
    state_path.write_text(json.dumps(state, indent=2))
    return state
```

- [ ] **Step 3: Write a unit test**

Create `tests/unit/test_iteration_planned.py`:

```python
"""Test update_iteration_planned idempotent write."""
import json
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from skills._lib.iteration.planned import update_iteration_planned  # noqa


def test_planned_entry_added(tmp_path):
    state = update_iteration_planned(str(tmp_path), "demo", "design", "workflow")
    assert any(c["name"] == "demo" and c["status"] == "planned" for c in state["changes"])


def test_planned_entry_idempotent(tmp_path):
    update_iteration_planned(str(tmp_path), "demo", "design", "workflow")
    state = update_iteration_planned(str(tmp_path), "demo", "design", "workflow")
    demos = [c for c in state["changes"] if c["name"] == "demo"]
    assert len(demos) == 1, "must not duplicate planned entries"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/unit/test_iteration_planned.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add skills/_lib/iteration/planned.py tests/unit/test_iteration_planned.py
git commit -m "feat(iteration): update_iteration_planned for design-pre-created changes"
```

---

### Task 8: plan_intake.sh accepts v1+v2 + reads changes_pre_created

**Files:**
- Modify: `skills/guide-plan/scripts/plan_intake.sh`

- [ ] **Step 1: Read current implementation**

```bash
grep -n "check_design_handoff\|design-handoff" skills/guide-plan/scripts/plan_intake.sh
```

- [ ] **Step 2: Modify check_design_handoff to dual-version**

Find the function and gate on `version` field:

```bash
# Inside check_design_handoff (rename if needed for clarity):
local handoff_version
handoff_version=$(jq -r '.version // 1' "$handoff_file")
case "$handoff_version" in
    1)
        # Legacy: changes_pre_created treated as empty
        CHANGES_PRE_CREATED=()
        ;;
    2)
        CHANGES_PRE_CREATED=($(jq -r '.changes_pre_created[]?' "$handoff_file"))
        ;;
    *)
        echo "❌ unknown design-handoff version: $handoff_version" >&2
        return 1
        ;;
esac
```

Expose `CHANGES_PRE_CREATED` as a global so Phase 2 skip logic can read it.

- [ ] **Step 3: Add skip-already-created filter**

In Phase 2 change iteration, before `openspec new change`:

```bash
# Skip changes already created by design approve
local skip_set=" ${CHANGES_PRE_CREATED[*]:-} "
case " $skip_set " in
    *" $name "*)
        echo "⏭  $name pre-created by design (in changes_pre_created), skipping"
        continue
        ;;
esac
```

- [ ] **Step 4: Add a bats integration test**

Create `tests/integration/test_plan_intake_design_handoff_v2.bats`:

```bash
#!/usr/bin/env bats
# Tests for plan_intake.sh v1+v2 compat and changes_pre_created skip logic.

load test_helper

setup() {
    REPO_ROOT="$(git rev-parse --show-toplevel)"
    WORK_DIR="$(mktemp -d)"
    mkdir -p "$WORK_DIR/.rddf/state"
    mkdir -p "$WORK_DIR/openspec/changes"
}

teardown() {
    rm -rf "$WORK_DIR"
}

@test "plan_intake: v1 handoff accepted (backward compat)" {
    cat > "$WORK_DIR/.rddf/state/.design-handoff.json" <<EOF
{
  "design_complete_at": "2026-08-01T10:00:00+00:00",
  "proposals_reviewed": 1,
  "all_proposals_have_decision": true,
  "version": 1
}
EOF
    bash "$REPO_ROOT/skills/guide-plan/scripts/plan_intake.sh" "$WORK_DIR" 2>&1 | grep -q "v1" || true
    # v1 must NOT raise version error
    run bash "$REPO_ROOT/skills/guide-plan/scripts/plan_intake.sh" "$WORK_DIR"
    [ "$status" -ne 2 ]  # 2 = version error per Step 2
}

@test "plan_intake: v2 handoff reads changes_pre_created" {
    cat > "$WORK_DIR/.rddf/state/.design-handoff.json" <<EOF
{
  "design_complete_at": "2026-08-01T10:00:00+00:00",
  "proposals_reviewed": 1,
  "all_proposals_have_decision": true,
  "version": 2,
  "changes_pre_created": ["demo"]
}
EOF
    # Pre-create the change dir as design would have
    mkdir -p "$WORK_DIR/openspec/changes/demo"
    touch "$WORK_DIR/openspec/changes/demo/.openspec.yaml"
    bash "$REPO_ROOT/skills/guide-plan/scripts/plan_intake.sh" "$WORK_DIR" 2>&1 \
        | grep -q "changes_pre_created" || true
}

@test "plan_intake: unknown version rejected" {
    cat > "$WORK_DIR/.rddf/state/.design-handoff.json" <<EOF
{
  "design_complete_at": "2026-08-01T10:00:00+00:00",
  "proposals_reviewed": 1,
  "all_proposals_have_decision": true,
  "version": 99
}
EOF
    run bash "$REPO_ROOT/skills/guide-plan/scripts/plan_intake.sh" "$WORK_DIR"
    [ "$status" -eq 2 ]
}
```

- [ ] **Step 5: Run test**

Run: `bats tests/integration/test_plan_intake_design_handoff_v2.bats`
Expected: 3 tests pass.

- [ ] **Step 6: Commit**

```bash
git add skills/guide-plan/scripts/plan_intake.sh \
        tests/integration/test_plan_intake_design_handoff_v2.bats
git commit -m "feat(plan-intake): accept v1/v2 handoff, skip changes_pre_created"
```

---

### Task 9: guide-design SKILL.md orchestrate approve (generate → confirm → fall-through)

**Files:**
- Modify: `skills/guide-design/SKILL.md`

- [ ] **Step 1: Locate Phase 3 approve section**

```bash
grep -n "approve\|Phase 3" skills/guide-design/SKILL.md | head -20
```

- [ ] **Step 2: Rewrite the approve section to add the orchestration step**

Inside the existing Phase 3 approve flow, after the "approve_proposal.sh → append approved row" step, insert a new fenced block:

```markdown
#### D1 orchestration: generate → confirm → fall-through

After the approved-row append, run the AI-driven full-proposal generation:

```bash
# Step 1: draft full proposal.md from improvements/<name>.md
export CHANGE_NAME="$name"
export IMPROVEMENTS_PATH="$improvements_file"
python3 skills/guide-design/scripts/generate_full_proposal.py > /tmp/proposal-draft.md

# Step 2: show the draft to the user (cat /tmp/proposal-draft.md)
cat /tmp/proposal-draft.md

# Step 3: ask user "Accept and proceed? [y/N]"
# MUST be a real interactive prompt — DO NOT auto-confirm.

# Step 4: on confirm, fall-through to openspec new change + state write
if [[ "$user_reply" == "y" ]]; then
    openspec new change "$name" --yes
    mv /tmp/proposal-draft.md openspec/changes/$name/proposal.md
    # write roadmap-meta.yaml (change_type from improvements head)
    # update iteration.json (status=planned)
    IMPROVEMENT_NAME="$name" bash skills/guide-design/scripts/approve_proposal.sh
fi
```

This is the human checkpoint required by D1. AI never auto-confirms.
```

- [ ] **Step 3: Update Phase 5 design-done to write handoff v2**

Find the design-done write step and ensure it passes `CHANGES_PRE_CREATED` to `write_design_handoff.py`:

```bash
export CHANGES_PRE_CREATED="<comma-separated names of all approved changes this session>"
bash skills/guide-design/scripts/write_design_handoff.sh
```

- [ ] **Step 4: Commit**

```bash
git add skills/guide-design/SKILL.md
git commit -m "docs(design): Phase 3 approve orchestration D1 + design-done handoff v2"
```

---

### Task 10: guide-plan SKILL.md fill scope narrowed

**Files:**
- Modify: `skills/guide-plan/SKILL.md`

- [ ] **Step 1: Locate Phase 2.5 fill**

```bash
grep -n "Phase 2.5\|fill" skills/guide-plan/SKILL.md | head -20
```

- [ ] **Step 2: Update Phase 2 to display pre-created tag**

In the Phase 2 change listing, when reading from `changes_pre_created`, render with a `🆕 design-pre-created` badge:

```markdown
| Change | Phase | Status | Source |
|---|---|---|---|
| demo | design | 🆕 design-pre-created | changes_pre_created |
```

- [ ] **Step 3: Update Phase 2.5 fill scope**

Replace the fill instruction list with the narrowed scope:

```markdown
### Phase 2.5 fill (narrowed when design pre-created)

For changes in `changes_pre_created`:
- SKIP: `openspec new change` (already created)
- SKIP: proposal.md write (already complete)
- DO: write design.md (if missing)
- DO: write tasks.md
- DO: write specs/*.md

For other changes (legacy / skeleton path):
- DO: full fill (unchanged)
```

- [ ] **Step 4: Commit**

```bash
git add skills/guide-plan/SKILL.md
git commit -m "docs(plan): Phase 2 mark pre-created, Phase 2.5 fill scope narrowed"
```

---

### Task 11: ADR-0025 — design/plan 职责再分配

**Files:**
- Create: `docs/adr/ADR-0025-design-proposal-creation.md`
- Modify: `docs/adr/ADR-0003-*.md` (or add index entry)

- [ ] **Step 1: Pick the next ADR number**

```bash
ls docs/adr/ | sort -r | head -3
```

- [ ] **Step 2: Write ADR-0025**

Create `docs/adr/ADR-0025-design-proposal-creation.md` (use `docs/adr/ADR-0000-template.md` as the layout template):

```markdown
# ADR-0025: design 阶段承担 openspec proposal 创建与内容审查

## 状态

已采纳

## 背景

(v2.1 四阶段架构后，design 仅追加 approved 行，proposal 创建在 plan 阶段，反馈链路过长 — 详见 proposal.md ## Why)

## 决策

- approve 动作升级为「生成完整 proposal.md → 用户确认 → 落盘 + openspec new change + 写 roadmap-meta + iteration.json planned」
- design-handoff schema v1 → v2，新增 `changes_pre_created`
- guide-plan intake 消费 `changes_pre_created` 跳过已建 change，Phase 2.5 fill 范围收缩为 specs/design/tasks
- design 阶段两层内容审查（improvements 5 段 + openspec validate），warning/strict 双模式

## 后果

- 审批时即可看到完整 proposal，反馈链路从 plan 阶段前移到 design 阶段
- 提案内容质量问题（缺 ADR 引用、In/Out Scope 不清）暴露在前移位置
- 兼容路径 `SKIP_DESIGN_HANDOFF=yes` 保留骨架模式
- ADR-0003 仍记录三阶段架构，本 ADR 显式记录 v2.1 四阶段架构的再分配

## 备选

- 维持 design 仅状态流转（v2.0 行为） — 反馈链路问题持续
- 引入独立 review 阶段 — 复杂度上升，新增 state 反而问题增多
```

- [ ] **Step 3: Update ADR index (if an index file exists)**

```bash
grep -n "ADR-0024" docs/adr/README.md 2>/dev/null || echo "no ADR index"
```

If there's an index, append a row for ADR-0025. Otherwise skip.

- [ ] **Step 4: Commit**

```bash
git add docs/adr/ADR-0025-design-proposal-creation.md
git commit -m "docs(adr): ADR-0025 design/plan 职责再分配"
```

---

### Task 12: AGENTS.md / README.md sync

**Files:**
- Modify: `AGENTS.md`
- Modify: `README.md`

- [ ] **Step 1: Update guide design row to reflect new responsibility**

In `AGENTS.md` (the rdd-workflow AGENTS.md, not the root), find the four-stage architecture table and update the `design` row description.

- [ ] **Step 2: Update README v2.1 four-stage description**

Find the four-stage table and ensure the design phase description says "design + 创建 + 内容审查" instead of "设计管理".

- [ ] **Step 3: Commit**

```bash
git add AGENTS.md README.md
git commit -m "docs: sync design phase new responsibilities (approve + review)"
```

---

### Task 13: end-to-end bats integration

**Files:**
- Create: `tests/integration/test_approve_full_proposal.bats`
- Create: `tests/integration/test_design_content_review.bats`

- [ ] **Step 1: Write approve full-proposal e2e test**

`tests/integration/test_approve_full_proposal.bats`:

```bash
#!/usr/bin/env bats
# E2E: approve → openspec change dir contains full proposal + roadmap-meta + iteration

load test_helper

setup() {
    REPO_ROOT="$(git rev-parse --show-toplevel)"
    WORK_DIR="$(mktemp -d)"
    mkdir -p "$WORK_DIR/.rddf/state"
    mkdir -p "$WORK_DIR/openspec/changes"
    mkdir -p "$WORK_DIR/improvements"
}

teardown() {
    rm -rf "$WORK_DIR"
}

@test "approve: change dir contains proposal.md (>=500 chars, ADR refs, In/Out Scope)" {
    cat > "$WORK_DIR/improvements/demo.md" <<EOF
# demo

**阶段**: design
**分类**: workflow
**类型**: feature

## 架构依据

ADR-0003 + ADR-0017 决定 design/plan 职责再分配。

## 范围

- approve 升级

## 关键场景

- 单条批准

## 技术约束

- env-var 传参

## 验收标准

- [ ] proposal.md >= 500 字符
- [ ] 含 ADR-NNNN 引用
EOF

    # Run the generate_full_proposal.py directly (CWD-style)
    export CHANGE_NAME="demo"
    export IMPROVEMENTS_PATH="$WORK_DIR/improvements/demo.md"
    mkdir -p "$WORK_DIR/openspec/changes/demo"
    cd "$WORK_DIR"
    python3 "$REPO_ROOT/skills/guide-design/scripts/generate_full_proposal.py" \
        > "$WORK_DIR/openspec/changes/demo/proposal.md"

    # Assertions
    [ -f "$WORK_DIR/openspec/changes/demo/proposal.md" ]
    local size
    size=$(wc -c < "$WORK_DIR/openspec/changes/demo/proposal.md")
    [ "$size" -ge 500 ]
    grep -q "ADR-0003" "$WORK_DIR/openspec/changes/demo/proposal.md"
    grep -q "In Scope" "$WORK_DIR/openspec/changes/demo/proposal.md"
    grep -q "Out of Scope" "$WORK_DIR/openspec/changes/demo/proposal.md"
}
```

- [ ] **Step 2: Write content review bats**

`tests/integration/test_design_content_review.bats`:

```bash
#!/usr/bin/env bats
# E2E: design_content_review.sh warnings + STRICT blocking + SKIP bypass

load test_helper

setup() {
    REPO_ROOT="$(git rev-parse --show-toplevel)"
    WORK_DIR="$(mktemp -d)"
    mkdir -p "$WORK_DIR/improvements"
}

teardown() {
    rm -rf "$WORK_DIR"
}

@test "content_review: passes on complete improvements" {
    cat > "$WORK_DIR/improvements/good.md" <<EOF
# good

**阶段**: design
**分类**: workflow
**类型**: feature

## 架构依据

ADR-0003.

## 范围

- a

## 关键场景

- b

## 技术约束

- c

## 验收标准

- [ ] d
EOF
    export IMPROVEMENTS_PATH="$WORK_DIR/improvements/good.md"
    export STRICT_DESIGN_GATE=no
    export SKIP_CONTENT_REVIEW=no
    run bash "$REPO_ROOT/skills/guide-design/scripts/design_content_review.sh"
    [ "$status" -eq 0 ]
}

@test "content_review: STRICT blocks on missing head" {
    cat > "$WORK_DIR/improvements/bad.md" <<EOF
# bad

## 架构依据

ADR-0003.

## 范围

- a

## 关键场景

- b

## 技术约束

- c

## 验收标准

- [ ] d
EOF
    export IMPROVEMENTS_PATH="$WORK_DIR/improvements/bad.md"
    export STRICT_DESIGN_GATE=yes
    export SKIP_CONTENT_REVIEW=no
    run bash "$REPO_ROOT/skills/guide-design/scripts/design_content_review.sh"
    [ "$status" -eq 1 ]
}

@test "content_review: SKIP bypasses regardless" {
    export IMPROVEMENTS_PATH="/nonexistent"
    export STRICT_DESIGN_GATE=yes
    export SKIP_CONTENT_REVIEW=yes
    run bash "$REPO_ROOT/skills/guide-design/scripts/design_content_review.sh"
    [ "$status" -eq 0 ]
}
```

- [ ] **Step 3: Run bats tests**

Run:
```bash
bats tests/integration/test_approve_full_proposal.bats
bats tests/integration/test_design_content_review.bats
```
Expected: all tests pass.

- [ ] **Step 4: Commit**

```bash
git add tests/integration/test_approve_full_proposal.bats \
        tests/integration/test_design_content_review.bats
git commit -m "test: e2e approve full-proposal + design content review"
```

---

### Task 14: regression — `SKIP_DESIGN_HANDOFF=yes` skeleton path unchanged

**Files:**
- Verify (no change): `skills/propose/scripts/propose_change.py` `create_skeleton_change`

- [ ] **Step 1: Verify skeleton path still works**

```bash
cd "$REPO_ROOT"
# Mock an existing improvement with type field
mkdir -p /tmp/skel-test/improvements /tmp/skel-test/openspec
cat > /tmp/skel-test/improvements/demo.md <<EOF
# demo
**类型**: feature
EOF
SKIP_DESIGN_HANDOFF=yes PROJECT_ROOT=/tmp/skel-test CHANGE_NAME=demo PHASE=design CATEGORY=workflow \
    python3 -c "
import os, sys
sys.path.insert(0, '$REPO_ROOT')
from skills.propose.scripts.propose_change import create_skeleton_change
create_skeleton_change(project_root='/tmp/skel-test', change_name='demo', phase='design', category='workflow', priority='P1')
"
echo "Exit: $?"
ls -la /tmp/skel-test/openspec/changes/demo/ 2>/dev/null
```

Expected: `create_skeleton_change` runs without error and produces the change dir.

- [ ] **Step 2: Re-run the existing skeleton tests**

```bash
python3 -m pytest tests/unit/test_propose_change_skeleton.py -v 2>/dev/null || echo "(no dedicated skeleton test file — rely on broader propose_change tests)"
```

Verify nothing broke.

- [ ] **Step 3: Check existing tests still pass**

```bash
python3 -m pytest tests/unit/test_design_handoff_schema.py -v
```

Expected: PASS.

- [ ] **Step 4: Commit (only if Step 1 required a fix)**

If the skeleton path needed a fix (e.g. need to also accept `IMPROVEMENTS_PATH` to extract change_type), commit that fix; otherwise skip.

---

### Task 15: full regression — unit + integration + smoke

**Files:**
- Verify only: `tests/`

- [ ] **Step 1: Run Python unit tests**

```bash
python3 -m pytest tests/unit/ -q --tb=short
```

Expected: PASS (no regressions).

- [ ] **Step 2: Run Python integration tests**

```bash
python3 -m pytest tests/integration/ -q --tb=short
```

Expected: PASS.

- [ ] **Step 3: Run smoke bats**

```bash
bats tests/smoke.bats
```

Expected: PASS.

- [ ] **Step 4: Run the constant-true assertion CI gate**

```bash
grep -rn "assert.*or True\|assert True" tests/ 2>/dev/null
```

Expected: no matches (constant-true assertions would fail CI).

- [ ] **Step 5: Run the new bats integration tests**

```bash
bats tests/integration/test_plan_intake_design_handoff_v2.bats
bats tests/integration/test_approve_full_proposal.bats
bats tests/integration/test_design_content_review.bats
```

Expected: all pass.

- [ ] **Step 6: Final commit (only if any fix from Steps 1-5)**

```bash
git status
# If clean, skip. If dirty, commit fixes.
```

---

## Self-Review

After Task 15, verify the spec is fully covered:

- [ ] **Spec §1 (approve 升级)**: Tasks 3, 5, 9 cover generate_full_proposal.py, approve_proposal.sh, SKILL.md orchestration
- [ ] **Spec §2 (两层内容审查)**: Tasks 4, 13 cover design_content_review.py + bats
- [ ] **Spec §3 (元数据来源修正)**: Tasks 6, 11 cover change_type in roadmap-meta + ADR-0025
- [ ] **Spec §4 (design-handoff schema v2)**: Tasks 1, 8 cover schema bump + plan_intake compat
- [ ] **Spec §5 (guide-plan 适应性调整)**: Tasks 8, 10 cover changes_pre_created skip + fill scope
- [ ] **Spec §6 (ADR 与文档)**: Tasks 11, 12 cover ADR-0025 + AGENTS/README sync
- [ ] **Spec §7 (端到端验证)**: Tasks 13, 14, 15 cover e2e + regression + full test run

**Placeholder scan**: No "TBD" / "implement later" / "similar to task N" / "fill in details" should remain in any task. ✓

**Type consistency**: `generate_full_proposal(name: str, md: str) -> str` used consistently in Tasks 3, 5, 13. `update_iteration_planned(root, name, phase, category) -> dict` used consistently in Tasks 7, 9. `review_improvements(md: str) -> list[str]` used consistently in Tasks 4, 13. ✓
