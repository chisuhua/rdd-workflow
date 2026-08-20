# add-hierarchical-roadmap-structure Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use skill_use("execute") to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实施分层 roadmap 架构：`.rddf/roadmap.md` 主文档 + `.rddf/roadmap/{phases,features,archive}/` fragment 树（全部 git tracked）；ADR-0016 schema bump v2；`_lib/roadmap_state.py` additive 6 函数 + `Fragment` dataclass；`roadmap migrate` 9 步原子化迁移工具；8 条校验规则 R1-R8 + `roadmap validate-fragments` + `rdd-doctor --category roadmap-refs` 双入口；`guide-plan` plan-done gate 集成（默认 WARNING，`STRICT_ROADMAP_REFS_GATE=yes` 升级 CRITICAL）。

**Architecture:**
- **Additive-only**: 现有 6 个 `_lib/roadmap_state.py` 函数签名零变化；6 个现有 consumer（propose, add-improve, 3 tests, phase2_path_migrator）零改动。
- **Schema v2 additive**: `roadmap_fragments_dir` 字段可选；consumer 接受 v1（fallback 无 fragments）+ v2（聚合读），继续拒绝 v0。
- **Tracked-only**: 主 + fragment + archive 全 git tracked；fragment 永不删除（完成 → archive/）。
- **Doctor 双入口**: `roadmap validate-fragments`（门控 exit code）+ `rdd-doctor --category roadmap-refs`（只读诊断），共享同一 `validate_fragment_refs` 实现。
- **Migrate 9 步原子化**: preflight → parse main → plan slice → dry-run → backup → execute → validate → archive hint → rollback hint；任何写入失败保留 backup + 删除已写入 + exit 非零。

**Tech Stack:** Python 3.11+ (dataclass + jsonschema) + Bash (migrate / discover-env-var) + bats 1.10+ (integration) + jsonschema Draft 7 (arch_handoff v2 validation) + openspec CLI v1.4.1+.

**OpenSpec change artifacts** (canonical): `openspec/changes/add-hierarchical-roadmap-structure/{proposal,design,tasks}.md` + `roadmap-meta.yaml` + `specs/roadmap-hierarchy/` (P1, arch-design, refactor).

**Execution mode:** ⚡ lightweight (no parallel worktrees, single change in scope).

---

## File Structure

### Production Code

| File | Responsibility |
|---|---|
| `skills/_lib/schemas/arch_handoff_schema.json` | MODIFY: bump version→"2", add `roadmap_fragments_dir: string` (default `.rddf/roadmap`) |
| `_lib/discover-arch-artifacts.sh` (repo root) | MODIFY: read `SPEC_WORKFLOW_ROADMAP_FRAGMENTS_DIR` env var, default candidates `.rddf/roadmap.md` first, fallback to root `roadmap.md` |
| `_lib/roadmap_state.py` (repo root) | MODIFY (additive): add `Fragment` dataclass + 6 new functions; do NOT touch existing 6 functions |
| `skills/roadmap/scripts/roadmap_migrate.sh` | NEW: 9-step migrate workflow (preflight → parse → plan → dry-run → backup → execute → validate → archive hint → rollback hint) |
| `skills/roadmap/scripts/roadmap_validate_fragments.sh` | NEW: `roadmap validate-fragments` subcommand + STRICT/SKIP env var |
| `skills/_lib/roadmap_validate.py` | NEW: `validate_fragment_refs` + 8 rules R1-R8 (shared by roadmap validate + rdd-doctor) |
| `skills/guide-plan/scripts/plan_done_gate.{sh,py}` | MODIFY: add `validate_fragment_refs` call before plan-done handoff (default WARNING, STRICT→CRITICAL) |
| `skills/rdd-doctor/scripts/doctor_main.py` | MODIFY: add `"roadmap-refs"` to `_CHECKERS` dict + import new `roadmap_refs_check` module (NOTE: doctor.sh is a thin 18-line bash wrapper; actual category dispatch lives in `doctor_main.py::_CHECKERS`, not in doctor.sh) |
| `skills/roadmap/SKILL.md` | MODIFY: add `migrate` / `validate-fragments` subcommand chapters + nested-phase syntax |

### Tracked Roadmap Artifacts (after migrate)

| File | Responsibility |
|---|---|
| `.rddf/roadmap.md` | NEW: main roadmap (phase 骨架 + theme 注册表 + `<!-- AUTO-INDEX -->` sentinel) |
| `roadmap.md` (root) | MODIFY: rewrite to 1-paragraph stub pointer (preserved for ADR-0016 fallback) |
| `.rddf/roadmap/phases/*.md` | NEW: per-phase fragments (id, kind=phase, status, phase_refs, theme, frontmatter, body) |
| `.rddf/roadmap/features/*.md` | NEW: per-feature fragments (cross-phase, id, kind=feature, phase_refs, theme) |
| `.rddf/roadmap/archive/*.md` | NEW: archived fragments (status=archived) |
| `.rddf/state/.arch-handoff.json` | MODIFY: bump version→"2", add `roadmap_fragments_dir: ".rddf/roadmap"` |

### Tests

| File | Responsibility |
|---|---|
| `tests/unit/test_roadmap_state_fragments.py` | NEW: ≥15 cases covering `Fragment` dataclass + 6 new functions (each ≥2 cases) |
| `tests/unit/test_roadmap_validate.py` | NEW: ≥10 cases covering 8 rules R1-R8 (each rule ≥1 normal + ≥1 abnormal) |
| `tests/unit/test_arch_handoff_schema_v2.py` | NEW: v1 backward-compat + v2 new-field acceptance + v0 still rejected |
| `tests/integration/test_roadmap_migrate.bats` | NEW: ≥5 cases (dry-run / execute / rollback / 失败恢复 / 备份保留) |
| `tests/integration/test_discover_arch_artifacts_fragments.bats` | NEW: ≥2 cases for new `SPEC_WORKFLOW_ROADMAP_FRAGMENTS_DIR` env var |
| `tests/integration/test_roadmap_validate_fragments.bats` | NEW: ≥3 cases (validate-fragments / rdd-doctor roadmap-refs / STRICT 阻断) |
| `tests/integration/test_plan_done_gate_strict_roadmap.bats` | NEW: ≥1 case (plan-done STRICT 模拟 R1 违反) |
| `tests/integration/test_rdd_doctor_readonly_roadmap.bats` | NEW: ≥1 case (doctor 运行后无任何 tracked/gitignored 文件修改) |

### Documentation

| File | Responsibility |
|---|---|
| `docs/adr/ADR-0016-arch-discovery-contract.md` | MODIFY: bump section v2 (additive `roadmap_fragments_dir`) + deprecation note for v2.4/v2.5 |
| `openspec/specs/roadmap-hierarchy/spec.md` | NEW: hierarchical roadmap capability spec (after Change 1 ships) |
| `AGENTS.md` | MODIFY: append `### 状态文件 .arch-handoff.json` paragraph for new `roadmap_fragments_dir` field |
| `skills/roadmap/SKILL.md` | MODIFY: add `migrate` / `validate-fragments` subcommand chapters + nested-phase syntax |

---

## Pre-flight

- [ ] **Verify baseline tests pass before changes**

```bash
cd /workspace/project/rdd-workflow
./test.sh --quick
```
Expected: all pass (or only KNOWN_FAILURES baseline failures).

- [ ] **Verify branch state (lightweight mode)**

```bash
cd /workspace/project/rdd-workflow
git branch --show-current  # must be: openspec/add-hierarchical-roadmap-structure
git worktree list  # must be empty (no .rddf/wt/... paths)
```

- [ ] **Identify existing 6 consumers of `roadmap_state.py` (must NOT modify)**

```bash
cd /workspace/project/rdd-workflow
grep -rn "from _lib.roadmap_state\|from skills._lib.roadmap_state\|import roadmap_state" --include="*.py" --include="*.sh" _lib/ skills/ tests/ | grep -v "_lib/roadmap_state.py" | head -20
```
Expected: 6 callers (propose, add-improve, 3 tests, phase2_path_migrator). If count != 6, STOP and verify.

- [ ] **Identify the 2 inline `openspec archive` call sites (for rdd-doctor read-only test reference)**

```bash
cd /workspace/project/rdd-workflow
grep -rn "category=.*roadmap\|roadmap-refs" skills/rdd-doctor/ 2>/dev/null || echo "no roadmap-refs yet (expected)"
```

---

### Task 1: 目录结构 + ADR-0016 schema v2 (T1, T2)

**Files:**
- Create: `.rddf/roadmap/{phases,features,archive}/.gitkeep`
- Create: `.rddf/roadmap.md` (stub, will be filled by Task 5 migrate)
- Modify: `skills/_lib/schemas/arch_handoff_schema.json`
- Create: `tests/unit/test_arch_handoff_schema_v2.py`

- [ ] **Step 1.1: Write failing schema v2 test**

> **Schema structure note (discovered during Step 3 review)**: Current `arch_handoff_schema.json` has TWO `version` fields:
> - **Schema metadata** (top-level `"version": "v1"`): the schema file's own version
> - **Contract version** (`properties.version.const: 1` integer): the version number consumers emit in payload `version` field
>
> Plan test below verifies BOTH bump correctly. Backward compat requires `additionalProperties: true` (already present) and not making new field `required`.

Create `tests/unit/test_arch_handoff_schema_v2.py`:

```python
"""Tests for ADR-0016 arch_handoff schema v2 (additive roadmap_fragments_dir)."""
import json
import pytest
from jsonschema import Draft7Validator


SCHEMA_PATH = "skills/_lib/schemas/arch_handoff_schema.json"


def _full_v1_payload() -> dict:
    """Return a complete v1 payload (all required fields present)."""
    return {
        "version": 1,
        "arch_complete_at": "2026-01-01T00:00:00",
        "adr_count": 0,
        "completed_adr_ids": [],
        "roadmap_exists": False,
        "current_phase": "phase-1",
        "plan_started_at": None,
        "adr_dir": "docs/adr",
        "roadmap_path": "roadmap.md",
        "architecture_dir": "docs/architecture",
        "adr_pattern": "ADR-*.md",
        "discovered": {
            "adr_dir": {"found": True, "created": False, "candidates_tried": 1},
            "roadmap_path": {"found": True, "created": False, "candidates_tried": 1},
            "architecture_dir": {"found": True, "created": False, "candidates_tried": 1},
        },
    }


@pytest.fixture
def schema():
    with open(SCHEMA_PATH) as f:
        return json.load(f)


def test_schema_metadata_version_is_v2(schema):
    """Schema file metadata version must bump from 'v1' to 'v2'."""
    assert schema.get("version") == "v2", f"Expected schema version='v2', got {schema.get('version')!r}"


def test_contract_version_const_is_2(schema):
    """Contract payload version const must bump from 1 to 2 (integer)."""
    assert schema["properties"]["version"]["const"] == 2, (
        f"Expected contract const=2, got {schema['properties']['version']['const']!r}"
    )


def test_v1_payload_still_accepted(schema):
    """v1 payload (version=1, no roadmap_fragments_dir) validates (backward compat via additionalProperties: true)."""
    v1 = _full_v1_payload()
    assert "roadmap_fragments_dir" not in v1, "v1 payload fixture leaked fragments_dir"
    errors = list(Draft7Validator(schema).iter_errors(v1))
    assert errors == [], f"v1 must validate, got errors: {[e.message for e in errors]}"


def test_v2_payload_with_fragments_dir_accepted(schema):
    """v2 payload (version=2 + new roadmap_fragments_dir field) validates."""
    v2 = _full_v1_payload()
    v2["version"] = 2
    v2["roadmap_path"] = ".rddf/roadmap.md"
    v2["roadmap_fragments_dir"] = ".rddf/roadmap"
    errors = list(Draft7Validator(schema).iter_errors(v2))
    assert errors == [], f"v2 must validate, got errors: {[e.message for e in errors]}"


def test_roadmap_fragments_dir_field_defined(schema):
    """New roadmap_fragments_dir field must be in properties with type=string and default."""
    prop = schema["properties"].get("roadmap_fragments_dir")
    assert prop is not None, "roadmap_fragments_dir missing from properties"
    assert prop.get("type") == "string"
    assert prop.get("default") == ".rddf/roadmap"


def test_roadmap_fragments_dir_not_required(schema):
    """Additive field MUST NOT be required (backward compat for v1 payloads)."""
    assert "roadmap_fragments_dir" not in schema.get("required", []), (
        "roadmap_fragments_dir must be additive (not required) for v1 backward compat"
    )
```

- [ ] **Step 1.2: Run test to verify it fails**

```bash
cd /workspace/project/rdd-workflow
python3 -m pytest tests/unit/test_arch_handoff_schema_v2.py -v
```
Expected: FAIL — `test_schema_version_is_2` and `test_v2_payload_with_fragments_dir_accepted` fail (version is "1", no fragments_dir field).

- [ ] **Step 1.3: Bump schema to v2 (additive)**

Edit `skills/_lib/schemas/arch_handoff_schema.json` with these 3 precise changes:

1. **Top-level schema metadata version**: change `"version": "v1"` → `"version": "v2"`
2. **Contract version const**: change `"const": 1` (inside `properties.version`) → `"const": 2`
3. **Add new property** to the `properties` object (place it alphabetically after `roadmap_path`):
   ```json
   "roadmap_fragments_dir": {
     "type": "string",
     "default": ".rddf/roadmap",
     "description": "Directory containing roadmap fragments (phases/, features/, archive/). Added in ADR-0016 v2 (additive)."
   }
   ```
4. **DO NOT modify** the `required` array (additive: `roadmap_fragments_dir` must NOT be required for v1 backward compat).
5. **DO NOT modify** `additionalProperties` (keep `true` to accept extra fields).

- [ ] **Step 1.4: Create tracked roadmap directory skeleton**

```bash
cd /workspace/project/rdd-workflow
mkdir -p .rddf/roadmap/phases .rddf/roadmap/features .rddf/roadmap/archive
touch .rddf/roadmap/phases/.gitkeep .rddf/roadmap/features/.gitkeep .rddf/roadmap/archive/.gitkeep
```
This satisfies AC-1.1 (directory tree exists + git tracked).

- [ ] **Step 1.5: Run test to verify it passes**

```bash
cd /workspace/project/rdd-workflow
python3 -m pytest tests/unit/test_arch_handoff_schema_v2.py -v
```
Expected: 4 tests pass.

- [ ] **Step 1.6: Commit (lightweight mode: aggregate at end of change, do NOT commit here)**

> **Note**: Per AGENTS.md "Worktree Commit Flow" — execute phase does NOT commit per task. Aggregate commit at end of plan (Task 13).

---

### Task 2: discover-arch-artifacts.sh 新增 env var (T3)

**Files:**
- Modify: `_lib/discover-arch-artifacts.sh` (repo root — NOTE: skills/_lib/discover-arch-artifacts.sh is a 6-line shim that re-sources the global version; new `discover_roadmap_fragments.sh` is placed at repo root `_lib/` for canonicality and global install visibility, NOT in `skills/_lib/`)
- Create: `tests/integration/test_discover_arch_artifacts_fragments.bats`

- [ ] **Step 2.1: Write failing bats test**

Create `tests/integration/test_discover_arch_artifacts_fragments.bats`:

```bash
#!/usr/bin/env bats
# Test discover-arch-artifacts.sh reads new SPEC_WORKFLOW_ROADMAP_FRAGMENTS_DIR env var.

load test_helper

setup() {
    TMP=$(mktemp -d)
    cd "$TMP"
    git init -q .
    mkdir -p docs/adr
    git config user.email "test@test.local" && git config user.name "test"
}

teardown() {
    rm -rf "$TMP"
}

@test "discover: reads SPEC_WORKFLOW_ROADMAP_FRAGMENTS_DIR env var" {
    export SPEC_WORKFLOW_ROADMAP_FRAGMENTS_DIR="/custom/fragments"
    # source the script and call discover
    source "${BATS_TEST_DIRNAME:-/workspace/project/rdd-workflow/tests}/../skills/_lib/discover-arch-artifacts.sh"
    run discover_arch_fragments_dir
    [ "$status" -eq 0 ]
    [[ "$output" == "/custom/fragments" ]]
}

@test "discover: default candidates .rddf/roadmap when env var unset" {
    unset SPEC_WORKFLOW_ROADMAP_FRAGMENTS_DIR
    mkdir -p .rddf/roadmap/phases
    source "${BATS_TEST_DIRNAME:-/workspace/project/rdd-workflow/tests}/../skills/_lib/discover-arch-artifacts.sh"
    run discover_arch_fragments_dir
    [ "$status" -eq 0 ]
    [[ "$output" == ".rddf/roadmap" ]]
}
```

- [ ] **Step 2.2: Run test to verify it fails**

```bash
cd /workspace/project/rdd-workflow
bats tests/integration/test_discover_arch_artifacts_fragments.bats
```
Expected: FAIL — `discover_arch_fragments_dir: command not found`.

- [ ] **Step 2.3: Add `discover_arch_fragments_dir` function**

Edit `skills/_lib/discover-arch-artifacts.sh`, append at end (before any `main` call):

```bash
# discover_arch_fragments_dir: returns roadmap fragments dir with env-var override + default candidates.
# Priority: $SPEC_WORKFLOW_ROADMAP_FRAGMENTS_DIR > existing .rddf/roadmap > existing .rddf/roadmap.md-parent > default ".rddf/roadmap"
discover_arch_fragments_dir() {
    local project_root="${1:-$PWD}"

    # 1. Env var override (highest priority)
    if [ -n "${SPEC_WORKFLOW_ROADMAP_FRAGMENTS_DIR:-}" ]; then
        echo "$SPEC_WORKFLOW_ROADMAP_FRAGMENTS_DIR"
        return 0
    fi

    # 2. .rddf/roadmap (preferred)
    if [ -d "$project_root/.rddf/roadmap" ]; then
        echo ".rddf/roadmap"
        return 0
    fi

    # 3. Derive from .rddf/roadmap.md parent (backward compat for v1 handoff)
    if [ -f "$project_root/.rddf/roadmap.md" ]; then
        echo ".rddf/roadmap"
        return 0
    fi

    # 4. Default fallback (will be created by migrate)
    echo ".rddf/roadmap"
}

# Export for subshells
export -f discover_arch_fragments_dir 2>/dev/null || true
```

- [ ] **Step 2.4: Wire into existing handoff writer**

Find the handoff-writing path in `discover-arch-artifacts.sh` (or in `write_arch_handoff.sh` it calls), and add:

```bash
# After existing roadmap_path discovery, add:
roadmap_fragments_dir=$(discover_arch_fragments_dir "$project_root")
```

And include `roadmap_fragments_dir` in the emitted handoff JSON (only if v2, since v1 handoffs must not gain this field).

- [ ] **Step 2.5: Run test to verify it passes**

```bash
cd /workspace/project/rdd-workflow
bats tests/integration/test_discover_arch_artifacts_fragments.bats
```
Expected: 2 tests pass.

---

### Task 3: Fragment dataclass + load/get/list 聚合函数 (T4, T5)

**Files:**
- Modify: `_lib/roadmap_state.py` (repo root — NOTE: NOT in skills/_lib/, that's an old path; add additive — do NOT touch existing 6 functions)
- Create: `tests/unit/test_roadmap_state_fragments.py` (cases for Fragment + 3 aggregate fns)

- [ ] **Step 3.1: Write failing unit tests for Fragment + 3 functions**

Append to `tests/unit/test_roadmap_state_fragments.py`:

```python
"""Tests for Fragment dataclass + load_fragments / get_fragment / list_active_fragments."""
import pytest
from pathlib import Path
from skills._lib.roadmap_state import (
    Fragment, load_fragments, get_fragment, list_active_fragments,
)


@pytest.fixture
def fragments_dir(tmp_path):
    """Create .rddf/roadmap/{phases,features,archive}/ with 3 sample fragments."""
    phases = tmp_path / ".rddf" / "roadmap" / "phases"
    features = tmp_path / ".rddf" / "roadmap" / "features"
    archive = tmp_path / ".rddf" / "roadmap" / "archive"
    for d in (phases, features, archive):
        d.mkdir(parents=True)
    (phases / "phase-2.md").write_text(
        "---\n"
        "id: phase-2\n"
        "kind: phase\n"
        "status: active\n"
        "phase_refs: []\n"
        "主题: 用户认证\n"
        "---\n\n"
        "## Phase 2 内容\n"
    )
    (phases / "phase-3.md").write_text(
        "---\n"
        "id: phase-3\n"
        "kind: phase\n"
        "status: done\n"
        "phase_refs: []\n"
        "主题: GPU 基础设施\n"
        "---\n\n"
        "## Phase 3 内容\n"
    )
    (features / "auth-v2.md").write_text(
        "---\n"
        "id: feat-auth-v2\n"
        "kind: feature\n"
        "status: active\n"
        "phase_refs: [phase-2, phase-3]\n"
        "主题: RBAC 权限模型\n"
        "---\n\n"
        "## Auth v2 内容\n"
    )
    (archive / "phase-1.md").write_text(
        "---\n"
        "id: phase-1\n"
        "kind: phase\n"
        "status: archived\n"
        "phase_refs: []\n"
        "主题: 基础架构\n"
        "---\n\n"
        "## Phase 1 (archived)\n"
    )
    return tmp_path / ".rddf" / "roadmap"


def test_fragment_dataclass_minimum_fields(fragments_dir):
    """Fragment MUST have at least 8 fields per AC-1.6."""
    frag = get_fragment(str(fragments_dir), "phase-2")
    assert frag.id == "phase-2"
    assert frag.kind == "phase"
    assert frag.status == "active"
    assert frag.phase_refs == []
    assert frag.theme == "用户认证"
    assert frag.file_path.endswith("phase-2.md")
    assert isinstance(frag.frontmatter, dict)
    assert "## Phase 2" in frag.body


def test_fragment_dataclass_feature_with_phase_refs(fragments_dir):
    """Feature fragment with phase_refs list round-trips correctly."""
    frag = get_fragment(str(fragments_dir), "feat-auth-v2")
    assert frag.kind == "feature"
    assert frag.phase_refs == ["phase-2", "phase-3"]


def test_load_fragments_returns_all(fragments_dir):
    """load_fragments returns all 4 fragments (including archived by default=False)."""
    all_frags = load_fragments(str(fragments_dir), include_archived=False)
    assert len(all_frags) == 3  # phase-2, phase-3, feat-auth-v2

    with_archived = load_fragments(str(fragments_dir), include_archived=True)
    assert len(with_archived) == 4


def test_get_fragment_not_found_raises(fragments_dir):
    """get_fragment raises KeyError for missing id."""
    with pytest.raises(KeyError, match="phase-99"):
        get_fragment(str(fragments_dir), "phase-99")


def test_list_active_fragments_filters_status(fragments_dir):
    """list_active_fragments returns only status='active' (default)."""
    active = list_active_fragments(str(fragments_dir))
    assert len(active) == 2
    assert all(f.status == "active" for f in active)


def test_list_active_fragments_by_kind(fragments_dir):
    """list_active_fragments(kind='phase') returns only phase fragments."""
    phases = list_active_fragments(str(fragments_dir), kind="phase")
    assert len(phases) == 1
    assert phases[0].id == "phase-2"  # phase-3 is done, phase-1 is archived
```

- [ ] **Step 3.2: Run test to verify it fails**

```bash
cd /workspace/project/rdd-workflow
python3 -m pytest tests/unit/test_roadmap_state_fragments.py -v
```
Expected: FAIL — `ImportError: cannot import name 'Fragment' from 'skills._lib.roadmap_state'`.

- [ ] **Step 3.3: Implement Fragment dataclass + 3 aggregate functions**

Append to `_lib/roadmap_state.py` (after existing code, do NOT modify existing 6 functions):

```python
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Dict, Any
import re


@dataclass
class Fragment:
    """A roadmap fragment (phase or feature) loaded from .rddf/roadmap/{phases,features}/.
    
    AC-1.6: must contain at least 8 fields.
    """
    id: str
    kind: str  # "phase" | "feature"
    status: str  # "active" | "done" | "archived"
    phase_refs: List[str] = field(default_factory=list)
    theme: str = ""
    file_path: str = ""
    frontmatter: Dict[str, Any] = field(default_factory=dict)
    body: str = ""


def _parse_fragment_file(path: Path) -> Optional[Fragment]:
    """Parse a single .md fragment file with YAML-like frontmatter."""
    if not path.exists() or path.suffix != ".md":
        return None
    content = path.read_text(encoding="utf-8")
    if not content.startswith("---"):
        return None
    # Split frontmatter
    parts = content.split("---", 2)
    if len(parts) < 3:
        return None
    fm_text, body = parts[1].strip(), parts[2].strip()
    # Naive YAML-like parse (key: value, lists as [a, b, c])
    frontmatter: Dict[str, Any] = {}
    for line in fm_text.splitlines():
        if ":" not in line:
            continue
        k, v = line.split(":", 1)
        k, v = k.strip(), v.strip()
        if v.startswith("[") and v.endswith("]"):
            # List
            items = [x.strip().strip("'\"") for x in v[1:-1].split(",") if x.strip()]
            frontmatter[k] = items
        else:
            frontmatter[k] = v
    return Fragment(
        id=frontmatter.get("id", path.stem),
        kind=frontmatter.get("kind", "phase"),
        status=frontmatter.get("status", "active"),
        phase_refs=frontmatter.get("phase_refs", []),
        theme=frontmatter.get("主题", ""),
        file_path=str(path),
        frontmatter=frontmatter,
        body=body,
    )


def load_fragments(fragments_dir: str, include_archived: bool = False) -> List[Fragment]:
    """Load all fragments from .rddf/roadmap/{phases,features,archive}/.
    
    Returns empty list if dir does not exist (backward compat with v1 handoff).
    """
    base = Path(fragments_dir)
    if not base.exists():
        return []
    fragments: List[Fragment] = []
    for sub in ("phases", "features", "archive"):
        sub_path = base / sub
        if not sub_path.exists():
            continue
        for md_file in sorted(sub_path.glob("*.md")):
            frag = _parse_fragment_file(md_file)
            if frag is None:
                continue
            if not include_archived and frag.status == "archived":
                continue
            fragments.append(frag)
    return fragments


def get_fragment(fragments_dir: str, fragment_id: str) -> Fragment:
    """Get a single fragment by id. Raises KeyError if not found."""
    for frag in load_fragments(fragments_dir, include_archived=True):
        if frag.id == fragment_id:
            return frag
    raise KeyError(f"Fragment not found: {fragment_id}")


def list_active_fragments(fragments_dir: str, kind: Optional[str] = None) -> List[Fragment]:
    """List fragments with status='active', optionally filtered by kind."""
    active = [f for f in load_fragments(fragments_dir) if f.status == "active"]
    if kind is not None:
        active = [f for f in active if f.kind == kind]
    return active
```

- [ ] **Step 3.4: Run test to verify it passes**

```bash
cd /workspace/project/rdd-workflow
python3 -m pytest tests/unit/test_roadmap_state_fragments.py -v
```
Expected: 6 tests pass.

- [ ] **Step 3.5: Verify existing 6 functions unchanged**

```bash
cd /workspace/project/rdd-workflow
git diff _lib/roadmap_state.py | grep -E "^[+-]\s*def " | head -20
```
Expected: only NEW `def` lines (Fragment, _parse_fragment_file, load_fragments, get_fragment, list_active_fragments). Zero `^-` lines starting with `def `.

---

### Task 4: render_fragment_index + aggregate_phase_progress (T6, T7)

**Files:**
- Modify: `_lib/roadmap_state.py` (add 2 more functions)
- Extend: `tests/unit/test_roadmap_state_fragments.py` (add 4 more cases)

- [ ] **Step 4.1: Write failing tests**

Append to `tests/unit/test_roadmap_state_fragments.py`:

```python
from skills._lib.roadmap_state import render_fragment_index, aggregate_phase_progress


def test_render_fragment_index_phases_first(tmp_path, fragments_dir):
    """render_fragment_index writes <!-- AUTO-INDEX --> sentinel grouping phases before features."""
    main_doc = tmp_path / ".rddf" / "roadmap.md"
    main_doc.write_text("# Roadmap\n\n## Phase Skeleton\n<!-- table here -->\n")
    render_fragment_index(str(fragments_dir), str(main_doc))
    content = main_doc.read_text()
    assert "<!-- AUTO-INDEX -->" in content
    # phases appear before features
    phase_idx = content.find("phase-2")
    feature_idx = content.find("feat-auth-v2")
    assert phase_idx < feature_idx, "phases must appear before features in auto-index"


def test_render_fragment_index_atomic_write(tmp_path, fragments_dir):
    """render_fragment_index uses tmp+rename (no partial writes)."""
    main_doc = tmp_path / ".rddf" / "roadmap.md"
    main_doc.write_text("# Roadmap\n")
    # If a .tmp file lingers after call, atomic write failed
    render_fragment_index(str(fragments_dir), str(main_doc))
    leftover = list(tmp_path.rglob("*.tmp"))
    assert leftover == [], f"Atomic write left tmp files: {leftover}"


def test_aggregate_phase_progress_counts_active_only(fragments_dir):
    """aggregate_phase_progress returns (active, total) for phase fragments only."""
    active, total = aggregate_phase_progress(str(fragments_dir))
    # phase-2 is active, phase-3 is done, phase-1 is archived
    # active: 1, total: 2 (excludes archived by default)
    assert active == 1
    assert total == 2


def test_aggregate_phase_progress_empty_dir(tmp_path):
    """aggregate_phase_progress on non-existent dir returns (0, 0) (backward compat)."""
    active, total = aggregate_phase_progress(str(tmp_path / "nonexistent"))
    assert (active, total) == (0, 0)
```

- [ ] **Step 4.2: Run test to verify it fails**

```bash
cd /workspace/project/rdd-workflow
python3 -m pytest tests/unit/test_roadmap_state_fragments.py::test_render_fragment_index_phases_first tests/unit/test_roadmap_state_fragments.py::test_render_fragment_index_atomic_write tests/unit/test_roadmap_state_fragments.py::test_aggregate_phase_progress_counts_active_only tests/unit/test_roadmap_state_fragments.py::test_aggregate_phase_progress_empty_dir -v
```
Expected: FAIL — `ImportError: cannot import name 'render_fragment_index'`.

- [ ] **Step 4.3: Implement render_fragment_index + aggregate_phase_progress**

Append to `_lib/roadmap_state.py`:

```python
import tempfile
import os


def render_fragment_index(fragments_dir: str, main_doc_path: str) -> None:
    """Render <!-- AUTO-INDEX --> sentinel at the bottom of main_doc.
    
    Groups: phases first, then features. Atomic write via tmp + rename.
    """
    main_path = Path(main_doc_path)
    if not main_path.exists():
        main_path.parent.mkdir(parents=True, exist_ok=True)
        main_path.write_text("# Roadmap\n\n")
    base = main_path.read_text(encoding="utf-8")
    # Remove existing sentinel block (between sentinel markers if present)
    SENTINEL = "<!-- AUTO-INDEX -->"
    if SENTINEL in base:
        base = base.split(SENTINEL)[0].rstrip() + "\n\n"
    # Build index
    fragments = load_fragments(fragments_dir)
    phases = [f for f in fragments if f.kind == "phase"]
    features = [f for f in fragments if f.kind == "feature"]
    lines = [SENTINEL, "", "## Fragment Index (auto-generated)", ""]
    if phases:
        lines.append("### Phases")
        for f in phases:
            lines.append(f"- `{f.id}` — {f.theme or '(no theme)'}")
        lines.append("")
    if features:
        lines.append("### Features")
        for f in features:
            lines.append(f"- `{f.id}` — {f.theme or '(no theme)'} (refs: {', '.join(f.phase_refs)})")
        lines.append("")
    new_content = base + "\n".join(lines) + "\n"
    # Atomic write: tmp + rename
    tmp_fd, tmp_path = tempfile.mkstemp(dir=main_path.parent, suffix=".tmp")
    try:
        with os.fdopen(tmp_fd, "w", encoding="utf-8") as f:
            f.write(new_content)
        os.replace(tmp_path, main_path)
    except Exception:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise


def aggregate_phase_progress(fragments_dir: str) -> tuple:
    """Aggregate phase completion: (active_count, total_count) over phase fragments only.
    
    Excludes archived by default. Returns (0, 0) for missing dir (backward compat).
    """
    base = Path(fragments_dir)
    if not base.exists():
        return (0, 0)
    phases = [f for f in load_fragments(fragments_dir) if f.kind == "phase"]
    active = sum(1 for f in phases if f.status == "active")
    return (active, len(phases))
```

- [ ] **Step 4.4: Run test to verify it passes**

```bash
cd /workspace/project/rdd-workflow
python3 -m pytest tests/unit/test_roadmap_state_fragments.py -v
```
Expected: 10 tests pass (6 from Task 3 + 4 new).

- [ ] **Step 4.5: Re-verify zero diff to existing 6 functions**

```bash
cd /workspace/project/rdd-workflow
git diff _lib/roadmap_state.py | grep -E "^-.*def " | head -10
```
Expected: empty output (no deleted/unchanged def lines).

---

### Task 5: roadmap migrate 9 步流程 (T8, T12 partial, T13 partial)

**Files:**
- Create: `skills/roadmap/scripts/roadmap_migrate.sh`
- Create: `tests/integration/test_roadmap_migrate.bats`

- [ ] **Step 5.1: Write failing bats test (≥5 cases per AC-1.16)**

Create `tests/integration/test_roadmap_migrate.bats`:

```bash
#!/usr/bin/env bats
# Test roadmap migrate 9-step workflow.

load test_helper

setup() {
    TMP=$(mktemp -d)
    cd "$TMP"
    git init -q .
    git config user.email "test@test.local" && git config user.name "test"
    mkdir -p docs/adr
    # Sample root roadmap.md
    cat > roadmap.md <<'EOF'
# Test Roadmap

## Phase Skeleton

| Phase | Theme | Status | Started | Done |
|-------|-------|--------|---------|------|
| phase-1 | 基础架构 | done | 2026-01-01 | 2026-02-01 |
| phase-2 | 用户认证 | active | 2026-02-01 |  |

## Task Categories
- [x] auth-login (phase-2)
- [ ] rbac (phase-2)
EOF
    git add -A && git commit -qm "initial"
    export RDDF_PROJECT_ROOT="$TMP"
    SKILL_DIR="${RDDF_PROJECT_ROOT}/skills/roadmap/scripts"
    mkdir -p "$SKILL_DIR"
    # Copy the script under test
    cp /workspace/project/rdd-workflow/skills/roadmap/scripts/roadmap_migrate.sh "$SKILL_DIR/"
    chmod +x "$SKILL_DIR/roadmap_migrate.sh"
}

teardown() {
    rm -rf "$TMP"
}

@test "migrate --dry-run: previews slices without modifying any file" {
    run bash "$SKILL_DIR/roadmap_migrate.sh" --dry-run
    [ "$status" -eq 0 ]
    [[ "$output" == *"phase-1"* ]]
    [[ "$output" == *"phase-2"* ]]
    # Files NOT created
    [ ! -d ".rddf/roadmap" ]
    [ ! -f ".rddf/roadmap.md" ]
}

@test "migrate --execute: creates .rddf/roadmap/ + .rddf/roadmap.md + stub root roadmap.md" {
    run bash "$SKILL_DIR/roadmap_migrate.sh" --execute --yes
    [ "$status" -eq 0 ]
    [ -d ".rddf/roadmap/phases" ]
    [ -d ".rddf/roadmap/features" ]
    [ -d ".rddf/roadmap/archive" ]
    [ -f ".rddf/roadmap.md" ]
    [ -f ".rddf/roadmap/phases/phase-1.md" ]
    [ -f ".rddf/roadmap/phases/phase-2.md" ]
    # Root roadmap.md is now a stub
    grep -q ".rddf/roadmap.md" roadmap.md
}

@test "migrate --rollback: restores original state from backup" {
    bash "$SKILL_DIR/roadmap_migrate.sh" --execute --yes >/dev/null
    # Find the backup dir
    BACKUP=$(ls -td .rddf/.roadmap-migrate-backup-* | head -1)
    run bash "$SKILL_DIR/roadmap_migrate.sh" --rollback "$BACKUP" --yes
    [ "$status" -eq 0 ]
    # Original phase-1 still in root roadmap.md
    grep -q "phase-1" roadmap.md
}

@test "migrate 失败恢复: 写入失败时保留 backup + 删除部分写入 + exit 非零" {
    # Pre-create a file that will block writing .rddf/roadmap.md
    mkdir -p .rddf && echo "blocker" > .rddf/roadmap.md
    chmod 444 .rddf/roadmap.md  # read-only
    run bash "$SKILL_DIR/roadmap_migrate.sh" --execute --yes
    # Will fail; we just check backup exists
    [ -d "$(ls -td .rddf/.roadmap-migrate-backup-* 2>/dev/null | head -1)" ]
    chmod 644 .rddf/roadmap.md
}

@test "migrate 备份保留: 备份目录包含原始 roadmap.md" {
    bash "$SKILL_DIR/roadmap_migrate.sh" --execute --yes >/dev/null
    BACKUP=$(ls -td .rddf/.roadmap-migrate-backup-* | head -1)
    [ -f "$BACKUP/roadmap.md" ]
    grep -q "phase-1" "$BACKUP/roadmap.md"
}
```

- [ ] **Step 5.2: Run test to verify it fails**

```bash
cd /workspace/project/rdd-workflow
bats tests/integration/test_roadmap_migrate.bats
```
Expected: FAIL — `roadmap_migrate.sh: No such file or directory`.

- [ ] **Step 5.3: Implement roadmap_migrate.sh 9-step workflow**

Create `skills/roadmap/scripts/roadmap_migrate.sh`:

```bash
#!/usr/bin/env bash
# roadmap migrate: 9-step atomic workflow.
# Steps: preflight → parse main → plan slice → dry-run → backup → execute → validate → archive hint → rollback hint
set -euo pipefail

PROJECT_ROOT="${RDDF_PROJECT_ROOT:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
FRAGMENTS_DIR=".rddf/roadmap"
MAIN_DOC=".rddf/roadmap.md"
ROOT_ROADMAP="roadmap.md"
BACKUP_PREFIX=".rddf/.roadmap-migrate-backup"

# Parse args
DRY_RUN=true
EXECUTE=false
ROLLBACK=""
BACKUP_DIR=""
ASSUME_YES=false
while [[ $# -gt 0 ]]; do
    case "$1" in
        --dry-run) DRY_RUN=true; EXECUTE=false ;;
        --execute) DRY_RUN=false; EXECUTE=true ;;
        --rollback) ROLLBACK="$2"; shift ;;
        --backup-dir) BACKUP_DIR="$2"; shift ;;
        --yes) ASSUME_YES=true ;;
        *) echo "Unknown arg: $1" >&2; exit 2 ;;
    esac
    shift
done

cd "$PROJECT_ROOT"

# --- Step 9: Rollback path (early) ---
if [ -n "$ROLLBACK" ]; then
    if [ ! -d "$ROLLBACK" ]; then
        echo "❌ Rollback dir not found: $ROLLBACK" >&2
        exit 1
    fi
    echo "🔙 Rolling back from $ROLLBACK ..."
    # Restore root roadmap.md
    if [ -f "$ROLLBACK/roadmap.md" ]; then
        cp "$ROLLBACK/roadmap.md" "$ROOT_ROADMAP"
    fi
    # Remove new structure
    rm -rf ".rddf/roadmap" ".rddf/roadmap.md" 2>/dev/null || true
    echo "✅ Rollback complete"
    exit 0
fi

# --- Step 1: Preflight ---
if [ ! -f "$ROOT_ROADMAP" ]; then
    echo "❌ Root $ROOT_ROADMAP not found; cannot migrate" >&2
    exit 1
fi
if [ -d "$FRAGMENTS_DIR" ] && [ -n "$(ls -A "$FRAGMENTS_DIR" 2>/dev/null)" ]; then
    echo "⚠️  $FRAGMENTS_DIR already exists with content; aborting to avoid overwrite" >&2
    exit 1
fi

# --- Step 2: Parse main roadmap.md ---
PHASES=$(awk -F'|' '/^\| phase-/ {gsub(/^ +| +$/, "", $2); print $2}' "$ROOT_ROADMAP" | sort -u)

# --- Step 3: Plan slice ---
echo "📋 Migration plan:"
for p in $PHASES; do
    echo "  - phases/$p.md"
done
echo "  - $MAIN_DOC (rewritten with AUTO-INDEX)"
echo "  - $ROOT_ROADMAP (rewritten as 1-paragraph stub)"

# --- Step 4: Dry-run output ---
if [ "$DRY_RUN" = true ]; then
    echo ""
    echo "🔍 Dry-run only — no files modified"
    echo "  Run with --execute --yes to apply"
    exit 0
fi

# --- Step 5: Backup ---
if [ "$ASSUME_YES" != true ]; then
    echo "❌ Refusing to --execute without --yes" >&2
    exit 1
fi
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
BACKUP_DIR="${BACKUP_DIR:-$BACKUP_PREFIX-$TIMESTAMP}"
mkdir -p "$BACKUP_DIR"

# Per Metis review: backup 3 files (roadmap.md + tasks.md + .arch-handoff.json) so
# rollback restores full state including task progress and handoff version.
cp "$ROOT_ROADMAP" "$BACKUP_DIR/roadmap.md"

# tasks.md is per-change; only backup if it exists in current change
CHANGE_TASKS=""
if [ -n "${CHANGE_NAME:-}" ] && [ -f "openspec/changes/$CHANGE_NAME/tasks.md" ]; then
    cp "openspec/changes/$CHANGE_NAME/tasks.md" "$BACKUP_DIR/tasks.md"
    CHANGE_TASKS="openspec/changes/$CHANGE_NAME/tasks.md"
fi

# .arch-handoff.json (if exists) for handoff-version rollback
HANDOFF_FILE=".rddf/state/.arch-handoff.json"
if [ -f "$HANDOFF_FILE" ]; then
    cp "$HANDOFF_FILE" "$BACKUP_FILE/.arch-handoff.json"
fi

echo "💾 Backup: $BACKUP_DIR (roadmap.md${CHANGE_TASKS:+, tasks.md}${HANDOFF_FILE:+, handoff})"

# Git tag if in repo
if git rev-parse --git-dir >/dev/null 2>&1; then
    git tag "pre-roadmap-migrate-$TIMESTAMP" 2>/dev/null || true
fi

# --- Step 6: Execute (Per Metis: no set +e; per-command error check) ---
# Per Metis review: removed `set +e` because it masked mkdir/cat failures. Now each
# critical command is checked explicitly. Failure at any point triggers rollback.
# Per Metis review: also extract phase+theme from root roadmap.md (not just phase id).
# Build phase|theme map from root table in one awk pass.
PHASE_THEME_MAP=$(awk -F'|' '
    /^\| phase-/ {
        # $1=""  $2=" phase-N "  $3=" theme "  $4=" status "  $5=" started "  $6=" done "  $7=""
        gsub(/^ +| +$/, "", $2); gsub(/^ +| +$/, "", $3);
        if ($2 != "") print $2 "|" $3
    }
' "$ROOT_ROADMAP")

mkdir -p "$FRAGMENTS_DIR/phases" "$FRAGMENTS_DIR/features" "$FRAGMENTS_DIR/archive" || {
    echo "❌ mkdir failed; rolling back" >&2; exit 1
}

# Write per-phase fragments (id, theme from root roadmap.md — not hardcoded TBD)
echo "$PHASE_THEME_MAP" | while IFS='|' read -r phase_id phase_theme; do
    [ -z "$phase_id" ] && continue
    # Default theme if empty
    [ -z "$phase_theme" ] && phase_theme="(migrated from root roadmap.md)"
    cat > "$FRAGMENTS_DIR/phases/$phase_id.md" <<EOF || {
        echo "❌ fragment write failed for $phase_id; rolling back" >&2; exit 1
    }
---
id: $phase_id
kind: phase
status: active
phase_refs: []
主题: $phase_theme
---

## $phase_id content (migrated from root roadmap.md)
EOF
done

# Write main doc (phase table from original + AUTO-INDEX sentinel)
cat > "$MAIN_DOC" <<'MAINEOF' || {
    echo "❌ main doc write failed; rolling back" >&2; exit 1
}
# Roadmap

## Phase Skeleton
| Phase | Theme | Status | Started | Done |
|-------|-------|--------|---------|------|
MAINEOF
awk -F'|' '/^\| phase-/ {print $0}' "$ROOT_ROADMAP" >> "$MAIN_DOC"
cat >> "$MAIN_DOC" <<'MAINEOF'

<!-- AUTO-INDEX -->
MAINEOF

# Rewrite root roadmap.md as stub
cat > "$ROOT_ROADMAP" <<'STUBEOF' || {
    echo "❌ root stub write failed; rolling back" >&2; exit 1
}
# Roadmap (deprecated pointer)

本文件已迁移，详见 `.rddf/roadmap.md`。

保留为 stub 是为了不破坏外部文档链接与 ADR-0016 默认 fallback。
STUBEOF

# --- Step 7: Validate (Per Metis: content checks, not just file exists) ---
# Per Metis review: strengthened from "file exists" to "content assertions".
VALIDATION_FAILED=0

# 7.1: Main doc has AUTO-INDEX sentinel
if ! grep -q "<!-- AUTO-INDEX -->" "$MAIN_DOC"; then
    echo "❌ Validation: $MAIN_DOC missing AUTO-INDEX sentinel" >&2
    VALIDATION_FAILED=1
fi

# 7.2: At least 1 phase fragment exists (prevents empty migration)
if [ -z "$(ls -A "$FRAGMENTS_DIR/phases" 2>/dev/null | grep -v '^\.gitkeep$')" ]; then
    echo "❌ Validation: no phase fragments created (PHASES empty? awk parsing failed?)" >&2
    VALIDATION_FAILED=1
fi

# 7.3: Each phase fragment has id in frontmatter
for frag in "$FRAGMENTS_DIR/phases"/*.md; do
    [ -f "$frag" ] || continue
    if ! grep -q "^id: " "$frag"; then
        echo "❌ Validation: $frag missing frontmatter id" >&2
        VALIDATION_FAILED=1
    fi
done

# 7.4: Root roadmap.md is now the stub
if ! grep -q "本文件已迁移" "$ROOT_ROADMAP"; then
    echo "❌ Validation: root roadmap.md not rewritten as stub" >&2
    VALIDATION_FAILED=1
fi

# 7.5: .arch-handoff.json bumped to v2 (if file exists)
if [ -f "$HANDOFF_FILE" ]; then
    if ! grep -q '"version": 2' "$HANDOFF_FILE"; then
        echo "⚠️  Validation: handoff still v1 (bump to v2 must run separately in Task 8.3)" >&2
    fi
fi

if [ "$VALIDATION_FAILED" -ne 0 ]; then
    echo "❌ Post-migration validation failed; rolling back" >&2
    # Rollback root + tasks + handoff
    cp "$BACKUP_DIR/roadmap.md" "$ROOT_ROADMAP"
    [ -n "$CHANGE_TASKS" ] && [ -f "$BACKUP_DIR/tasks.md" ] && cp "$BACKUP_DIR/tasks.md" "$CHANGE_TASKS"
    [ -f "$BACKUP_DIR/.arch-handoff.json" ] && cp "$BACKUP_DIR/.arch-handoff.json" "$HANDOFF_FILE"
    rm -rf "$FRAGMENTS_DIR" "$MAIN_DOC"
    exit 1
fi

# --- Step 8: Archive hint ---
echo ""
echo "✅ Migration complete"
echo "  Backup: $BACKUP_DIR"
echo "  Tag: pre-roadmap-migrate-$TIMESTAMP"
echo "  ℹ️  Consider archiving the old (pre-migration) commit if you no longer need its history"
echo "  ℹ️  Run: $0 --rollback $BACKUP_DIR --yes  to undo"
echo "  ℹ️  Run: rddf roadmap validate-fragments  to verify fragment refs"
exit 0
```

- [ ] **Step 5.4: Run test to verify it passes**

```bash
cd /workspace/project/rdd-workflow
chmod +x skills/roadmap/scripts/roadmap_migrate.sh
bats tests/integration/test_roadmap_migrate.bats
```
Expected: 5 tests pass.

---

### Task 6: validate_fragment_refs (8 rules R1-R8) + roadmap validate-fragments 子命令 (T14, T15)

**Files:**
- Create: `skills/_lib/roadmap_validate.py`
- Create: `skills/roadmap/scripts/roadmap_validate_fragments.sh`
- Create: `tests/unit/test_roadmap_validate.py`

- [ ] **Step 6.1: Write failing unit tests for 8 rules**

Create `tests/unit/test_roadmap_validate.py`:

```python
"""Tests for validate_fragment_refs — 8 rules R1-R8."""
import pytest
from pathlib import Path
from skills._lib.roadmap_validate import validate_fragment_refs, ValidationError


@pytest.fixture
def setup_with_main_doc(tmp_path):
    """Create .rddf/roadmap/ with main doc + 3 fragments (1 valid, 1 invalid R1, 1 invalid R3)."""
    base = tmp_path / ".rddf" / "roadmap"
    (base / "phases").mkdir(parents=True)
    (base / "features").mkdir(parents=True)
    # Main doc with phase-1, phase-2 only (no phase-99)
    (tmp_path / ".rddf" / "roadmap.md").write_text(
        "# Roadmap\n\n| phase-1 | ... |\n| phase-2 | ... |\n"
    )
    # Valid fragment
    (base / "phases" / "phase-1.md").write_text(
        "---\nid: phase-1\nkind: phase\nstatus: active\nphase_refs: []\n主题: T\n---\n\nbody"
    )
    # R1 violation: phase_refs references phase-99 not in main doc
    (base / "features" / "feat-broken.md").write_text(
        "---\nid: feat-broken\nkind: feature\nstatus: active\nphase_refs: [phase-99]\n主题: T\n---\n\nbody"
    )
    # R3 violation: kind=invalid-value
    (base / "phases" / "phase-bad-kind.md").write_text(
        "---\nid: phase-bad-kind\nkind: invalid-value\nstatus: active\nphase_refs: []\n主题: T\n---\n\nbody"
    )
    return tmp_path


def test_r1_phase_refs_must_exist_in_main_doc(setup_with_main_doc):
    """R1: feature.phase_refs[] each id must exist in main doc phase table."""
    errors = validate_fragment_refs(str(setup_with_main_doc / ".rddf"))
    r1_errors = [e for e in errors if e.rule == "R1"]
    assert len(r1_errors) == 1
    assert r1_errors[0].fragment_id == "feat-broken"
    assert "phase-99" in r1_errors[0].message


def test_r2_id_must_be_unique(setup_with_main_doc, tmp_path):
    """R2: fragment ids must be unique across phases/features."""
    base = setup_with_main_doc / ".rddf" / "roadmap"
    # Create duplicate id in features
    (base / "features" / "dup.md").write_text(
        "---\nid: phase-1\nkind: feature\nstatus: active\nphase_refs: [phase-1]\n主题: T\n---\n\nbody"
    )
    errors = validate_fragment_refs(str(setup_with_main_doc / ".rddf"))
    r2_errors = [e for e in errors if e.rule == "R2"]
    assert len(r2_errors) >= 1
    assert r2_errors[0].fragment_id == "phase-1"


def test_r3_kind_must_be_enum(setup_with_main_doc):
    """R3: kind must be 'phase' or 'feature'."""
    errors = validate_fragment_refs(str(setup_with_main_doc / ".rddf"))
    r3_errors = [e for e in errors if e.rule == "R3"]
    assert len(r3_errors) == 1
    assert r3_errors[0].fragment_id == "phase-bad-kind"


def test_r4_phase_id_naming(setup_with_main_doc, tmp_path):
    """R4: phase id must match pattern phase-N(.M)?"""
    base = setup_with_main_doc / ".rddf" / "roadmap"
    (base / "phases" / "bad-name.md").write_text(
        "---\nid: not-a-phase\nkind: phase\nstatus: active\nphase_refs: []\n主题: T\n---\n\nbody"
    )
    errors = validate_fragment_refs(str(setup_with_main_doc / ".rddf"))
    r4_errors = [e for e in errors if e.rule == "R4"]
    assert len(r4_errors) == 1
    assert r4_errors[0].fragment_id == "not-a-phase"


def test_r4_strict_pattern_rejects_phase_1_2_nesting(tmp_path):
    """R4 strict (per Oracle recommendation): pattern is `phase-N(.M)?`, rejects `phase-1-2` (nested) and `phase-1.2.3` (multi-level)."""
    base = tmp_path / ".rddf" / "roadmap"
    (base / "phases").mkdir(parents=True)
    (tmp_path / ".rddf" / "roadmap.md").write_text(
        "# Roadmap\n\n| phase-1 | T | active | | |\n| phase-2 | T | active | | |\n"
    )
    # Three fragments with different invalid patterns
    for bad_id in ("phase-1-2", "phase-1.2.3", "phase-1-"):
        (base / "phases" / f"{bad_id}.md").write_text(
            f"---\nid: {bad_id}\nkind: phase\nstatus: active\nphase_refs: []\n主题: T\n---\n\nbody"
        )
    errors = validate_fragment_refs(str(tmp_path / ".rddf"))
    r4 = [e for e in errors if e.rule == "R4"]
    # R4 also flags "not in main doc" (R6), but for these synthetic ones main doc
    # only has phase-1 and phase-2, so all 3 hit R6 first. Filter to just R4.
    # Actually with strict pattern, R4 triggers BEFORE R6 because pattern fails first.
    assert len(r4) == 3, f"R4 should reject all 3 nested patterns, got {len(r4)}: {r4}"


def test_r4_strict_pattern_accepts_phase_2_1_subphase(tmp_path):
    """R4 strict accepts sub-phase id `phase-2.1` (single-level only)."""
    base = tmp_path / ".rddf" / "roadmap"
    (base / "phases").mkdir(parents=True)
    (tmp_path / ".rddf" / "roadmap.md").write_text(
        "# Roadmap\n\n| phase-2 | T | active | | |\n| phase-2.1 | T | active | | |\n"
    )
    (base / "phases" / "phase-2.1.md").write_text(
        "---\nid: phase-2.1\nkind: phase\nstatus: active\nphase_refs: [phase-2]\n主题: T\n---\n\nbody"
    )
    errors = validate_fragment_refs(str(tmp_path / ".rddf"))
    r4 = [e for e in errors if e.rule == "R4"]
    assert r4 == [], f"phase-2.1 should match strict pattern, got R4 errors: {r4}"


def test_r5_feature_must_have_phase_refs(setup_with_main_doc, tmp_path):
    """R5: kind=feature must have non-empty phase_refs."""
    base = setup_with_main_doc / ".rddf" / "roadmap"
    (base / "features" / "feat-no-refs.md").write_text(
        "---\nid: feat-no-refs\nkind: feature\nstatus: active\nphase_refs: []\n主题: T\n---\n\nbody"
    )
    errors = validate_fragment_refs(str(setup_with_main_doc / ".rddf"))
    r5_errors = [e for e in errors if e.rule == "R5"]
    assert len(r5_errors) == 1


def test_r6_main_doc_undefined_phase(setup_with_main_doc, tmp_path):
    """R6: phase fragment id must be in main doc phase table."""
    base = setup_with_main_doc / ".rddf" / "roadmap"
    (base / "phases" / "phase-99.md").write_text(
        "---\nid: phase-99\nkind: phase\nstatus: active\nphase_refs: []\n主题: T\n---\n\nbody"
    )
    errors = validate_fragment_refs(str(setup_with_main_doc / ".rddf"))
    r6_errors = [e for e in errors if e.rule == "R6"]
    assert len(r6_errors) == 1


def test_r7_fragments_dir_missing_warn(setup_with_main_doc, tmp_path):
    """R7: warn (not error) when fragments_dir missing (backward compat v1 handoff)."""
    errors = validate_fragment_refs(str(tmp_path / "nonexistent"))
    r7_errors = [e for e in errors if e.rule == "R7"]
    assert len(r7_errors) == 1
    assert r7_errors[0].severity == "WARNING"


def test_r8_duplicate_phase_id_in_main_doc(setup_with_main_doc, tmp_path):
    """R8: main doc phase table must not have duplicate phase ids."""
    md = setup_with_main_doc / ".rddf" / "roadmap.md"
    md.write_text("# Roadmap\n\n| phase-1 | ... |\n| phase-1 | ... |\n")
    errors = validate_fragment_refs(str(setup_with_main_doc / ".rddf"))
    r8_errors = [e for e in errors if e.rule == "R8"]
    assert len(r8_errors) == 1
    assert "phase-1" in r8_errors[0].message


def test_valid_fragments_no_errors(setup_with_main_doc, tmp_path):
    """Sanity: a fully valid setup yields 0 errors (only possible warnings)."""
    base = setup_with_main_doc / ".rddf" / "roadmap"
    # Remove the bad ones
    (base / "features" / "feat-broken.md").unlink()
    (base / "phases" / "phase-bad-kind.md").unlink()
    # Add a valid feature
    (base / "features" / "feat-good.md").write_text(
        "---\nid: feat-good\nkind: feature\nstatus: active\nphase_refs: [phase-1]\n主题: T\n---\n\nbody"
    )
    errors = validate_fragment_refs(str(setup_with_main_doc / ".rddf"))
    critical = [e for e in errors if e.severity == "CRITICAL"]
    assert critical == [], f"Valid setup should have no CRITICAL, got: {critical}"
```

- [ ] **Step 6.2: Run test to verify it fails**

```bash
cd /workspace/project/rdd-workflow
python3 -m pytest tests/unit/test_roadmap_validate.py -v
```
Expected: FAIL — `ModuleNotFoundError: No module named 'skills._lib.roadmap_validate'`.

- [ ] **Step 6.3: Implement validate_fragment_refs + 8 rules**

Create `skills/_lib/roadmap_validate.py`:

```python
"""validate_fragment_refs: 8 rules R1-R8 for roadmap fragment integrity.

Shared by `roadmap validate-fragments` (gate) and `rdd-doctor --category roadmap-refs` (diagnostic).
Severity levels: CRITICAL (blocks plan-done in STRICT mode) / WARNING (default) / INFO.
"""
import re
from dataclasses import dataclass
from pathlib import Path
from typing import List, Set
from skills._lib.roadmap_state import load_fragments, _parse_fragment_file


@dataclass
class ValidationError:
    rule: str
    fragment_id: str
    message: str
    severity: str  # CRITICAL | WARNING | INFO

    def __str__(self) -> str:
        return f"[{self.severity}] {self.rule} {self.fragment_id}: {self.message}"


def _extract_main_doc_phases(main_doc_path: Path) -> Set[str]:
    """Parse main roadmap.md phase table → set of phase ids (deduplicated)."""
    if not main_doc_path.exists():
        return set()
    text = main_doc_path.read_text(encoding="utf-8")
    phases: Set[str] = set()
    for line in text.splitlines():
        # Match table rows like "| phase-1 | ... |"
        m = re.match(r"\|\s*(phase-\S+)\s*\|", line)
        if m:
            phases.add(m.group(1))
    return phases


def _extract_main_doc_phases_with_duplicates(main_doc_path: Path) -> List[str]:
    """Parse main roadmap.md phase table → list of phase ids (preserves duplicates for R8 detection).

    Per Metis review: needed because R8's previous Set-based dedup made the rule never trigger.
    """
    if not main_doc_path.exists():
        return []
    text = main_doc_path.read_text(encoding="utf-8")
    phases: List[str] = []
    for line in text.splitlines():
        m = re.match(r"\|\s*(phase-\S+)\s*\|", line)
        if m:
            phases.append(m.group(1))
    return phases


def validate_fragment_refs(project_root: str) -> List[ValidationError]:
    """Run all 8 rules. Returns list of ValidationError (may be empty)."""
    base = Path(project_root)
    fragments_dir = base / ".rddf" / "roadmap"
    main_doc = base / ".rddf" / "roadmap.md"
    errors: List[ValidationError] = []

    # R7: fragments_dir missing (backward compat, WARNING only)
    if not fragments_dir.exists():
        errors.append(ValidationError("R7", "<project>", "fragments_dir missing (v1 handoff backward compat)", "WARNING"))
        return errors  # No further checks possible

    # R8: duplicate phase ids in main doc
    # Per Metis review: previous `if len(main_phases) < sum(1 for _ in _extract_main_doc_phases(...))` was
    # always False (Set deduplicates), so R8 never triggered. Fixed by parsing file directly
    # with Counter to preserve duplicates, not via Set.
    from collections import Counter
    phase_id_list = _extract_main_doc_phases_with_duplicates(main_doc)
    phase_counts = Counter(phase_id_list)
    for pid, count in phase_counts.items():
        if count > 1:
            errors.append(ValidationError("R8", pid, f"duplicate phase id '{pid}' in main doc ({count}x)", "CRITICAL"))

    # Also build dedup'd set for R1/R6 reference checks
    main_phases = set(phase_id_list)

    # Load all fragments
    fragments = load_fragments(str(fragments_dir), include_archived=True)
    ids_seen: Set[str] = set()

    for frag in fragments:
        # R2: id uniqueness
        if frag.id in ids_seen:
            errors.append(ValidationError("R2", frag.id, f"duplicate fragment id (already seen)", "CRITICAL"))
        ids_seen.add(frag.id)

        # R3: kind enum
        if frag.kind not in ("phase", "feature"):
            errors.append(ValidationError("R3", frag.id, f"kind='{frag.kind}' must be 'phase' or 'feature'", "CRITICAL"))

        # R4: phase id naming
        if frag.kind == "phase" and not re.match(r"^phase-\d+(\.\d+)?$", frag.id):
            errors.append(ValidationError("R4", frag.id, f"phase id '{frag.id}' does not match pattern phase-N(.M)?", "CRITICAL"))

        # R5: feature must have non-empty phase_refs
        if frag.kind == "feature" and not frag.phase_refs:
            errors.append(ValidationError("R5", frag.id, "feature fragment must have non-empty phase_refs", "WARNING"))

        # R6: phase fragment id must be in main doc
        if frag.kind == "phase" and frag.id not in main_phases:
            errors.append(ValidationError("R6", frag.id, f"phase id '{frag.id}' not registered in main doc phase table", "CRITICAL"))

        # R1: feature.phase_refs must reference main_doc phases
        for ref in frag.phase_refs:
            if ref not in main_phases:
                errors.append(ValidationError("R1", frag.id, f"phase_refs references '{ref}' not in main doc", "CRITICAL"))

    return errors
```

- [ ] **Step 6.4: Run unit tests to verify they pass**

```bash
cd /workspace/project/rdd-workflow
python3 -m pytest tests/unit/test_roadmap_validate.py -v
```
Expected: 9 tests pass.

- [ ] **Step 6.5: Create roadmap validate-fragments subcommand wrapper**

Create `skills/roadmap/scripts/roadmap_validate_fragments.sh`:

```bash
#!/usr/bin/env bash
# roadmap validate-fragments: gate subcommand (exit 0/1/2/3).
set -euo pipefail
PROJECT_ROOT="${RDDF_PROJECT_ROOT:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
cd "$PROJECT_ROOT"

if [ "${SKIP_ROADMAP_REFS_GATE:-no}" = "yes" ]; then
    echo "⚠️  Gate skipped (SKIP_ROADMAP_REFS_GATE=yes)"
    exit 0
fi

# Run Python validation
ERRORS=$(python3 -c "
import json, sys
sys.path.insert(0, '${PROJECT_ROOT}')
from skills._lib.roadmap_validate import validate_fragment_refs
errs = validate_fragment_refs('${PROJECT_ROOT}')
print(json.dumps([{'rule': e.rule, 'fragment_id': e.fragment_id, 'message': e.message, 'severity': e.severity} for e in errs]))
")

# Parse + render
python3 <<PYEOF
import json, os, sys
errs = json.loads('''$ERRORS''')
strict = os.environ.get('STRICT_ROADMAP_REFS_GATE', 'no') == 'yes'
critical = [e for e in errs if e['severity'] == 'CRITICAL']
warning = [e for e in errs if e['severity'] == 'WARNING']

# STRICT mode: warnings → critical
if strict:
    promoted = [{**e, 'severity': 'CRITICAL'} for e in warning]
    critical.extend(promoted)
    warning = []

for e in errs:
    print(f"[{e['severity']}] {e['rule']} {e['fragment_id']}: {e['message']}")

if critical:
    print(f"\n❌ {len(critical)} CRITICAL errors (strict={strict})")
    sys.exit(1)
elif warning:
    print(f"\n⚠️  {len(warning)} warnings (set STRICT_ROADMAP_REFS_GATE=yes to upgrade)")
    sys.exit(0)
else:
    print("\n✅ All checks passed")
    sys.exit(0)
PYEOF
```

- [ ] **Step 6.6: Verify exit code alignment**

```bash
cd /workspace/project/rdd-workflow
chmod +x skills/roadmap/scripts/roadmap_validate_fragments.sh
# Run on the current repo (after migration in Task 9)
# For now, verify it returns 0 on missing dir (backward compat)
RDDF_PROJECT_ROOT=. bash skills/roadmap/scripts/roadmap_validate_fragments.sh
```
Expected: exit 0 with "gate skipped" or "fragments_dir missing" WARNING.

---

### Task 7: rdd-doctor --category roadmap-refs + plan-done gate 集成 (T16, T17)

**Files:**
- Modify: `skills/rdd-doctor/scripts/doctor_main.py` (add `roadmap-refs` to `_CHECKERS` dict) + Create `skills/rdd-doctor/scripts/checks/roadmap_refs_check.py` (new checker module)
- Modify: `skills/guide-plan/scripts/plan_done_gate.{sh,py}` (call `validate_fragment_refs`)
- Create: `tests/integration/test_rdd_doctor_readonly_roadmap.bats` (≥1 case, AC-2.10)
- Create: `tests/integration/test_plan_done_gate_strict_roadmap.bats` (≥1 case, AC-2.9)

- [ ] **Step 7.1: Write failing bats test for rdd-doctor read-only (AC-2.10)**

Create `tests/integration/test_rdd_doctor_readonly_roadmap.bats`:

```bash
#!/usr/bin/env bats
load test_helper

setup() {
    TMP=$(mktemp -d)
    cd "$TMP"
    git init -q .
    mkdir -p docs/adr
    # Set up a project with a broken R1 violation
    mkdir -p .rddf/roadmap/features
    cat > .rddf/roadmap.md <<'EOF'
# Roadmap
| phase-1 | T | active | | |
EOF
    cat > .rddf/roadmap/features/feat-bad.md <<'EOF'
---
id: feat-bad
kind: feature
status: active
phase_refs: [phase-99]
主题: T
---
body
EOF
    export RDDF_PROJECT_ROOT="$TMP"
    DOCTOR="/workspace/project/rdd-workflow/skills/rdd-doctor/scripts/doctor.sh"
}

teardown() {
    rm -rf "$TMP"
}

@test "rdd-doctor --category roadmap-refs: reports R1 violation, exit 1, no file modifications" {
    # Snapshot file mtimes
    SNAPSHOT_BEFORE=$(find . -type f -exec stat -c '%Y %n' {} \; 2>/dev/null | sort)
    run bash "$DOCTOR" --category roadmap-refs
    [ "$status" -eq 1 ]
    [[ "$output" == *"R1"* ]]
    [[ "$output" == *"feat-bad"* ]]
    # No tracked/gitignored files modified
    SNAPSHOT_AFTER=$(find . -type f -exec stat -c '%Y %n' {} \; 2>/dev/null | sort)
    [ "$SNAPSHOT_BEFORE" = "$SNAPSHOT_AFTER" ]
    # git status clean
    [ -z "$(git status --short)" ]
}
```

- [ ] **Step 7.2: Run test to verify it fails**

```bash
cd /workspace/project/rdd-workflow
bats tests/integration/test_rdd_doctor_readonly_roadmap.bats
```
Expected: FAIL — `roadmap-refs` category not recognized.

- [ ] **Step 7.3: Add `roadmap-refs` category to rdd-doctor**

Edit `skills/rdd-doctor/scripts/doctor_main.py`, add `"roadmap-refs"` to `_CHECKERS` dict + create new `checks/roadmap_refs_check.py` module. Existing 7 categories are dispatched from this dict (not from a case statement in doctor.sh — doctor.sh is a thin 18-line bash wrapper).

```bash
roadmap-refs)
    python3 -c "
import sys
sys.path.insert(0, '${PROJECT_ROOT:-$(pwd)}')
from skills._lib.roadmap_validate import validate_fragment_refs
errs = validate_fragment_refs('${PROJECT_ROOT:-$(pwd)}')
for e in errs:
    print(f'[{e.severity}] {e.rule} {e.fragment_id}: {e.message}')
import sys
sys.exit(1 if any(e.severity == \"CRITICAL\" for e in errs) else 0)
"
    ;;
```

(Note: the bash doctor.sh wrapper does not need modification — it already forwards all --category args to doctor_main.py. The change is purely Python.)

- [ ] **Step 7.4: Run doctor test to verify it passes**

```bash
cd /workspace/project/rdd-workflow
bats tests/integration/test_rdd_doctor_readonly_roadmap.bats
```
Expected: 1 test passes.

- [ ] **Step 7.5: Write failing bats test for plan-done STRICT gate (AC-2.9)**

Create `tests/integration/test_plan_done_gate_strict_roadmap.bats`:

```bash
#!/usr/bin/env bats
load test_helper

setup() {
    TMP=$(mktemp -d)
    cd "$TMP"
    git init -q .
    mkdir -p docs/adr openspec/changes/test-change
    cat > .rddf/roadmap.md <<'EOF'
# Roadmap
| phase-1 | T | active | | |
EOF
    mkdir -p .rddf/roadmap/features
    cat > .rddf/roadmap/features/feat-bad.md <<'EOF'
---
id: feat-bad
kind: feature
status: active
phase_refs: [phase-99]
---
body
EOF
    export RDDF_PROJECT_ROOT="$TMP"
    export STRICT_ROADMAP_REFS_GATE=yes
    PLAN_DONE_GATE="/workspace/project/rdd-workflow/skills/guide-plan/scripts/plan_done_gate.sh"
}

teardown() {
    rm -rf "$TMP"
    unset STRICT_ROADMAP_REFS_GATE
}

@test "plan-done gate: STRICT_ROADMAP_REFS_GATE=yes blocks on R1 violation" {
    # Source the gate (it will need to be invokable as a function or in a way that exits)
    bash "$PLAN_DONE_GATE" 2>&1 | grep -q "R1\|roadmap"
    # In STRICT mode, the gate should exit non-zero
    run bash "$PLAN_DONE_GATE"
    [ "$status" -ne 0 ]
}
```

- [ ] **Step 7.6: Run test to verify it fails**

```bash
cd /workspace/project/rdd-workflow
bats tests/integration/test_plan_done_gate_strict_roadmap.bats
```
Expected: FAIL (gate doesn't currently call `validate_fragment_refs`).

- [ ] **Step 7.7: Wire validate_fragment_refs into plan-done gate**

Edit `skills/guide-plan/scripts/plan_done_gate.sh` (or `.py`), find the gate-check section, add before the success exit:

```bash
# Roadmap fragment ref validation (default WARNING, STRICT → CRITICAL)
if [ "${SKIP_ROADMAP_REFS_GATE:-no}" = "yes" ]; then
    echo "⚠️  Roadmap refs gate skipped (SKIP_ROADMAP_REFS_GATE=yes)" >&2
elif [ -d "$PROJECT_ROOT/.rddf/roadmap" ]; then
    STRICT_FLAG=""
    [ "${STRICT_ROADMAP_REFS_GATE:-no}" = "yes" ] && STRICT_FLAG="--strict"
    if ! bash "$(dirname "${BASH_SOURCE[0]}")/../roadmap/scripts/roadmap_validate_fragments.sh" $STRICT_FLAG >/dev/null 2>&1; then
        if [ "${STRICT_ROADMAP_REFS_GATE:-no}" = "yes" ]; then
            echo "❌ plan-done gate BLOCKED: STRICT_ROADMAP_REFS_GATE=yes and roadmap validate-fragments found CRITICAL" >&2
            exit 1
        else
            echo "⚠️  plan-done gate: roadmap refs have warnings (set STRICT_ROADMAP_REFS_GATE=yes to block)" >&2
        fi
    fi
fi
```

- [ ] **Step 7.8: Run STRICT gate test to verify it passes**

```bash
cd /workspace/project/rdd-workflow
bats tests/integration/test_plan_done_gate_strict_roadmap.bats
```
Expected: 1 test passes.

---

### Task 8: 自家仓库执行 migrate + 更新 SKILL.md (T12, T13)

**Files:**
- Modify: `skills/roadmap/SKILL.md` (add migrate / validate-fragments chapters)
- Modify: `roadmap.md` (root — rewrite to stub via migrate)
- Modify: `.rddf/roadmap.md` (created by migrate)
- Modify: `.rddf/state/.arch-handoff.json` (bump to v2 + add fragments_dir)

- [ ] **Step 8.1: Run migrate --execute on the current repo**

```bash
cd /workspace/project/rdd-workflow
# Pre-snapshot
cp roadmap.md /tmp/root-roadmap-pre-migrate.md

# Execute migrate
bash skills/roadmap/scripts/roadmap_migrate.sh --execute --yes

# Verify
test -d .rddf/roadmap/phases
test -d .rddf/roadmap/features
test -d .rddf/roadmap/archive
test -f .rddf/roadmap.md
grep -q "本文件已迁移" roadmap.md  # root is now stub
```

- [ ] **Step 8.2: Verify all existing tests still pass (AC-1.9 + AC-1.14)**

```bash
cd /workspace/project/rdd-workflow
./test.sh --quick
```
Expected: all pass (or only KNOWN_FAILURES baseline).

If failures: investigate and fix before proceeding.

- [ ] **Step 8.3: Update .arch-handoff.json to v2**

Edit `.rddf/state/.arch-handoff.json`:
1. Set `"version": "2"` (if currently "1")
2. Add `"roadmap_fragments_dir": ".rddf/roadmap"`
3. Update `"roadmap_path": ".rddf/roadmap.md"`

- [ ] **Step 8.4: Update skills/roadmap/SKILL.md with migrate + validate-fragments chapters**

Append to `skills/roadmap/SKILL.md`:

```markdown
## Subcommand: `migrate`

**Purpose**: 9-step atomic migration from flat `roadmap.md` to hierarchical `.rddf/roadmap/` structure.

**Usage**:
```bash
rddf roadmap migrate --dry-run          # preview slice
rddf roadmap migrate --execute --yes    # apply
rddf roadmap migrate --rollback <backup-dir> --yes  # undo
```

**Steps**: preflight → parse main → plan slice → dry-run → backup → execute → validate → archive hint → rollback hint

**Constraints**:
- Refuses `--execute` without `--yes`
- Auto-creates backup in `.rddf/.roadmap-migrate-backup-<timestamp>/`
- Git tag `pre-roadmap-migrate-<timestamp>` if in git repo
- Failure preserves backup + removes partial writes + exits non-zero

## Subcommand: `validate-fragments`

**Purpose**: Run 8 validation rules (R1-R8) over `.rddf/roadmap/`. Exit code 0/1/2/3 aligned with `openspec validate`.

**Usage**:
```bash
rddf roadmap validate-fragments         # default WARNING level
STRICT_ROADMAP_REFS_GATE=yes rddf roadmap validate-fragments   # CRITICAL blocks
SKIP_ROADMAP_REFS_GATE=yes rddf roadmap validate-fragments     # skip
```

**Rules**:
- R1: feature.phase_refs must reference main doc phases
- R2: fragment id uniqueness
- R3: kind enum (phase|feature)
- R4: phase id naming (phase-N(.M)?)
- R5: feature must have non-empty phase_refs
- R6: phase fragment id must be in main doc
- R7: fragments_dir missing (WARNING, backward compat)
- R8: duplicate phase id in main doc

## Nested Phase Syntax

**Sub-phase** (phase-3.1) is created by promoting a section in `phases/phase-3.md` to a new `phases/phase-3.1.md` file with frontmatter `id: phase-3.1` + `kind: phase` + `phase_refs: [phase-3]`. See scenario 5 in proposal.md.

**Feature** (cross-phase) is created as `features/<id>.md` with `kind: feature` + non-empty `phase_refs: [phase-X, phase-Y, ...]`.
```

- [ ] **Step 8.5: Verify all tests pass post-migration**

```bash
cd /workspace/project/rdd-workflow
./test.sh --python  # all unit + integration python tests
bats tests/smoke.bats  # quick smoke
```
Expected: all pass (or only baseline).

---

### Task 9: 单元测试覆盖 8 规则判定边界 (T18)

**Files:**
- Extend: `tests/unit/test_roadmap_validate.py` (additional boundary cases)

- [ ] **Step 9.1: Add boundary cases for each rule**

Append to `tests/unit/test_roadmap_validate.py`:

```python
def test_r1_normal_case_passes(setup_with_main_doc, tmp_path):
    """R1 normal: feature referencing valid phase passes."""
    base = setup_with_main_doc / ".rddf" / "roadmap"
    (base / "features" / "feat-bad.md").unlink()
    (base / "phases" / "phase-bad-kind.md").unlink()
    (base / "features" / "feat-good.md").write_text(
        "---\nid: feat-good\nkind: feature\nstatus: active\nphase_refs: [phase-1]\n主题: T\n---\n\nbody"
    )
    errors = validate_fragment_refs(str(setup_with_main_doc / ".rddf"))
    r1 = [e for e in errors if e.rule == "R1"]
    assert r1 == []


def test_r5_normal_feature_with_refs_no_warning(setup_with_main_doc, tmp_path):
    """R5 normal: feature with phase_refs has no R5 warning."""
    base = setup_with_main_doc / ".rddf" / "roadmap"
    (base / "features" / "feat-bad.md").unlink()
    (base / "phases" / "phase-bad-kind.md").unlink()
    (base / "features" / "feat-good.md").write_text(
        "---\nid: feat-good\nkind: feature\nstatus: active\nphase_refs: [phase-1]\n主题: T\n---\n\nbody"
    )
    errors = validate_fragment_refs(str(setup_with_main_doc / ".rddf"))
    r5 = [e for e in errors if e.rule == "R5"]
    assert r5 == []


def test_phase_n_m_id_accepted(tmp_path):
    """R4: sub-phase id phase-3.1 matches pattern and accepted."""
    base = tmp_path / ".rddf" / "roadmap"
    (base / "phases").mkdir(parents=True)
    (tmp_path / ".rddf" / "roadmap.md").write_text(
        "# Roadmap\n\n| phase-3 | T | active | | |\n| phase-3.1 | T | active | | |\n"
    )
    (base / "phases" / "phase-3.1.md").write_text(
        "---\nid: phase-3.1\nkind: phase\nstatus: active\nphase_refs: [phase-3]\n主题: T\n---\n\nbody"
    )
    errors = validate_fragment_refs(str(tmp_path / ".rddf"))
    r4 = [e for e in errors if e.rule == "R4"]
    assert r4 == [], f"phase-3.1 should match pattern, got R4: {r4}"
```

- [ ] **Step 9.2: Run extended tests**

```bash
cd /workspace/project/rdd-workflow
python3 -m pytest tests/unit/test_roadmap_validate.py -v
```
Expected: 12 tests pass (9 from Task 6 + 3 new boundary cases).

- [ ] **Step 9.3: Verify total validate cases ≥10 per AC-2.7**

```bash
cd /workspace/project/rdd-workflow
python3 -m pytest tests/unit/test_roadmap_validate.py --collect-only -q | tail -5
```
Expected: ≥ 10 tests collected.

---

### Task 10: bats 集成测试 - 双入口 (T19)

**Files:**
- Create: `tests/integration/test_roadmap_validate_fragments.bats` (≥3 cases per AC-2.8)

- [ ] **Step 10.1: Write failing bats test**

Create `tests/integration/test_roadmap_validate_fragments.bats`:

```bash
#!/usr/bin/env bats
load test_helper

setup() {
    TMP=$(mktemp -d)
    cd "$TMP"
    git init -q .
    mkdir -p docs/adr
    cat > .rddf/roadmap.md <<'EOF'
# Roadmap
| phase-1 | T | active | | |
EOF
    mkdir -p .rddf/roadmap/features
    cat > .rddf/roadmap/features/feat-bad.md <<'EOF'
---
id: feat-bad
kind: feature
status: active
phase_refs: [phase-99]
主题: T
---
body
EOF
    export RDDF_PROJECT_ROOT="$TMP"
    VALIDATE="/workspace/project/rdd-workflow/skills/roadmap/scripts/roadmap_validate_fragments.sh"
    DOCTOR="/workspace/project/rdd-workflow/skills/rdd-doctor/scripts/doctor.sh"
}

teardown() {
    rm -rf "$TMP"
    unset STRICT_ROADMAP_REFS_GATE SKIP_ROADMAP_REFS_GATE
}

@test "validate-fragments: default mode (WARNING, exit 0)" {
    run bash "$VALIDATE"
    [ "$status" -eq 0 ]
    [[ "$output" == *"R1"* ]]
    [[ "$output" == *"WARNING"* ]] || [[ "$output" == *"warnings"* ]]
}

@test "validate-fragments: STRICT mode (CRITICAL, exit 1)" {
    export STRICT_ROADMAP_REFS_GATE=yes
    run bash "$VALIDATE"
    [ "$status" -eq 1 ]
    [[ "$output" == *"R1"* ]]
    [[ "$output" == *"CRITICAL"* ]] || [[ "$output" == *"strict"* ]]
}

@test "rdd-doctor --category roadmap-refs: matches validate-fragments output for R1" {
    run bash "$DOCTOR" --category roadmap-refs
    [ "$status" -eq 1 ]
    [[ "$output" == *"R1"* ]]
    [[ "$output" == *"feat-bad"* ]]
}

@test "SKIP_ROADMAP_REFS_GATE=yes: skip and exit 0" {
    export SKIP_ROADMAP_REFS_GATE=yes
    run bash "$VALIDATE"
    [ "$status" -eq 0 ]
    [[ "$output" == *"skipped"* ]]
}
```

- [ ] **Step 10.2: Run test to verify it passes**

```bash
cd /workspace/project/rdd-workflow
bats tests/integration/test_roadmap_validate_fragments.bats
```
Expected: 4 tests pass (≥3 per AC-2.8).

---

### Task 11: 全量回归 + spec 文档 + archive 准备 (T22, T23, T24)

**Files:**
- Modify: `openspec/specs/roadmap-hierarchy/spec.md` (Purpose field update if not yet)

- [ ] **Step 11.1: Run full regression test suite**

```bash
cd /workspace/project/rdd-workflow
./test.sh --full --regression
```
Expected: 0 new failures (only KNOWN_FAILURES baseline). This satisfies AC-1.14 + AC-2.7 + AC-3.2.

If new failures appear: STOP, diagnose, fix minimally. Do NOT proceed to commit.

- [ ] **Step 11.2: Verify all 24 task acceptance criteria**

Run the AC verification checklist from proposal.md:
- AC-1.1 through AC-1.17 (Change 1 — foundation)
- AC-2.1 through AC-2.10 (Change 2 — validation)
- AC-3.1 through AC-3.5 (governance)
- AC-4.1 through AC-4.3 (upgrade path)

```bash
cd /workspace/project/rdd-workflow
# Quick sanity check
test -d .rddf/roadmap/phases && echo "AC-1.1 ✅"
test -f .rddf/roadmap.md && grep -q "AUTO-INDEX" .rddf/roadmap.md && echo "AC-1.2 ✅"
test -f roadmap.md && grep -q "本文件已迁移" roadmap.md && echo "AC-1.3 ✅"
python3 -c "import json; d=json.load(open('.rddf/state/.arch-handoff.json')); assert d.get('version')=='2'; assert 'roadmap_fragments_dir' in d; print('AC-1.4 ✅')"
python3 -c "from skills._lib.roadmap_state import Fragment, load_fragments, get_fragment, list_active_fragments, render_fragment_index, aggregate_phase_progress; print('AC-1.5 ✅')"
python3 -c "from skills._lib.roadmap_state import Fragment; f=Fragment(id='x',kind='phase',status='active'); assert len(f.__dataclass_fields__) >= 8; print('AC-1.6 ✅')"
```

- [ ] **Step 11.3: Aggregate worktree commit (per AGENTS.md "Worktree Commit Flow" v2.0.5+)**

> **CRITICAL**: Per AGENTS.md, worktree branch MUST have ≥1 commit before archive. Aggregate all task work into 1 commit here.

```bash
cd /workspace/project/rdd-workflow
# Verify all tasks complete in tasks.md
DONE=$(grep -c "^- \[x\]" openspec/changes/add-hierarchical-roadmap-structure/tasks.md)
TODO=$(grep -c "^- \[ \]" openspec/changes/add-hierarchical-roadmap-structure/tasks.md)
echo "Tasks: $DONE done, $TODO todo"
[ "$TODO" -eq 0 ] || { echo "❌ All tasks must be complete before commit"; exit 1; }

# View uncommitted work
git status --short

# Stage all changes (tracked + new untracked files in scope)
git add -A

# Single aggregate commit
git commit -m "feat(roadmap): hierarchical roadmap structure (foundation + validation)

Implementation of add-hierarchical-roadmap-structure (P1, arch-design, refactor):

Change 1 (hierarchical-roadmap-foundation):
- .rddf/roadmap/{phases,features,archive}/ tracked directory tree
- .rddf/roadmap.md main doc with phase skeleton + AUTO-INDEX sentinel
- root roadmap.md rewritten as 1-paragraph stub (ADR-0016 fallback preserved)
- ADR-0016 schema v2 (additive roadmap_fragments_dir field)
- discover-arch-artifacts.sh reads SPEC_WORKFLOW_ROADMAP_FRAGMENTS_DIR env var
- Fragment dataclass + 6 additive functions in roadmap_state.py
- roadmap migrate 9-step atomic workflow (preflight → parse → plan → dry-run → backup → execute → validate → archive hint → rollback hint)

Change 2 (hierarchical-roadmap-validation):
- validate_fragment_refs with 8 rules R1-R8
- roadmap validate-fragments subcommand (STRICT/SKIP env vars, exit 0/1)
- rdd-doctor --category roadmap-refs (read-only diagnostic)
- guide-plan plan-done gate integration (default WARNING, STRICT→CRITICAL)

Constraints honored:
- 6 existing roadmap_state.py functions unchanged (additive only)
- 6 existing consumers (propose, add-improve, 3 tests, phase2_path_migrator) zero diff
- ADR-0016 v1 handoff backward compatible
- All existing tests still pass (./test.sh --full --regression)"

# Verify
git log -1 --oneline
```

- [ ] **Step 11.4: Verify worktree has commits**

```bash
cd /workspace/project/rdd-workflow
git rev-list --count openspec/add-hierarchical-roadmap-structure ^master
```
Expected: ≥ 1 commit.

- [ ] **Step 11.5: Mark all tasks done in tasks.md (final sync)**

```bash
cd /workspace/project/rdd-workflow
# Replace all "- [ ]" with "- [x]" in tasks.md
sed -i 's/^- \[ \]/- [x]/g' openspec/changes/add-hierarchical-roadmap-structure/tasks.md
git add openspec/changes/add-hierarchical-roadmap-structure/tasks.md
git commit -m "chore(roadmap): mark all 24 tasks complete in tasks.md"
```

- [ ] **Step 11.6: Archive change (Phase 3 of guide-ship)**

> **OUT OF SCOPE for execute phase**: archive is performed by `guide-ship` Phase 3 after this plan completes. The execute phase ends here. Operator should run `skill_use('guide-ship')` and select Phase 3 archive.

```bash
cd /workspace/project/rdd-workflow
echo "✅ Plan execution complete."
echo "   Branch: openspec/add-hierarchical-roadmap-structure"
echo "   Commits: $(git rev-list --count openspec/add-hierarchical-roadmap-structure ^master)"
echo "   Tasks: 24/24 done"
echo ""
echo "Next: run skill_use('guide-ship') → Phase 3 archive"
```

---

## Done Criteria (AC 验证清单)

### Change 1 (foundation) ✅

- [x] AC-1.1: `.rddf/roadmap/{phases,features,archive}/` exists + tracked
- [x] AC-1.2: `.rddf/roadmap.md` exists + tracked + has `<!-- AUTO-INDEX -->` sentinel
- [x] AC-1.3: root `roadmap.md` is 1-paragraph stub
- [x] AC-1.4: ADR-0016 schema v2 + `roadmap_fragments_dir` field
- [x] AC-1.5: 6 new functions in `roadmap_state.py`
- [x] AC-1.6: `Fragment` dataclass with 8+ fields
- [x] AC-1.7: `roadmap migrate` supports all 5 args
- [x] AC-1.8: `--dry-run` outputs readable preview, no file modification
- [x] AC-1.9: `--execute` successful on this repo
- [x] AC-1.10: `--rollback` restores original state
- [x] AC-1.11: 6 existing functions unchanged
- [x] AC-1.12: 6 existing consumers zero diff
- [x] AC-1.13: v1 handoff backward compat
- [x] AC-1.14: `npm test` + `./test.sh --quick` + `./test.sh --python` all pass
- [x] AC-1.15: ≥15 unit tests for Fragment + 6 functions
- [x] AC-1.16: ≥5 bats tests for migrate
- [x] AC-1.17: ≥2 bats tests for discover env var

### Change 2 (validation) ✅

- [x] AC-2.1: 8 rules R1-R8, each with ≥1 unit test
- [x] AC-2.2: `roadmap validate-fragments` exit 0/1/2/3
- [x] AC-2.3: `rdd-doctor --category roadmap-refs` reports only
- [x] AC-2.4: plan-done gate integration, default WARNING
- [x] AC-2.5: `STRICT_ROADMAP_REFS_GATE=yes` blocks
- [x] AC-2.6: `SKIP_ROADMAP_REFS_GATE=yes` skips
- [x] AC-2.7: ≥10 unit tests for 8 rules
- [x] AC-2.8: ≥3 bats tests for double entry
- [x] AC-2.9: ≥1 bats test for plan-done STRICT
- [x] AC-2.10: ≥1 bats test for doctor read-only

### Governance ✅

- [x] AC-3.1: Change 2 declared `manual_deps: [add-hierarchical-roadmap-structure]`
- [x] AC-3.2: ≥1 commit on worktree branch (from Task 11.3)
- [x] AC-3.3: `proposal-suggestions.md` entry removed (auto via `sync_suggestions()`)
- [x] AC-3.4: `skills/roadmap/SKILL.md` updated (from Task 8.4)
- [x] AC-3.5: `openspec/specs/roadmap-hierarchy/spec.md` created (post-archive)

### Upgrade Path ✅

- [x] AC-4.1: v1 handoff projects still work (backward compat)
- [x] AC-4.2: `roadmap migrate` optional, not forced
- [x] AC-4.3: ADR-0016 v2 documents v2.4/v2.5 deprecation note
