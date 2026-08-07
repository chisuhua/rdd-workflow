# add-rdd-doctor-skill Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use skill_use("execute") to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a `rdd-doctor` skill — a phase-independent, manual-triggered, read-only diagnostic tool that surfaces file content / schema drift across 5 categories of structured files in the rdd-workflow repo.

**Architecture:** Single bash entry (`doctor.sh`) dispatches to one Python process that imports 5 checker modules + 1 path resolver + 1 aggregator. Output is a graded report (CRITICAL/WARNING/INFO) or JSON. Exit codes follow `openspec validate` (0/1/2/3). Path resolver always reads from real `_lib/` (post-`c3a90fe` where `skills/_lib/` is a shim). cat-5 descoped from `openspec status` cross-check (vacuously satisfied; degraded path emits INFO).

**Tech Stack:** Bash 4+ (entry + fixtures), Python 3.11+ (render + 5 checkers + path resolver), `jsonschema` (cat-1), `pytest` + `bats-core` (tests).

---

## File Structure

### Production Code

| File | Responsibility |
|---|---|
| `skills/rdd-doctor/SKILL.md` | Skill frontmatter (name/description/license/compatibility + metadata.author/version/user-invocable). Documents invocation contract. |
| `skills/rdd-doctor/scripts/doctor.sh` | Bash entry. Parses flags (`--json`, `--category`, `--quiet`, `--help`, `--version`). Forwards to single Python process. |
| `skills/rdd-doctor/scripts/doctor_main.py` | Python main entry. Imports all checkers, calls path resolver, invokes checker functions, hands raw findings to `doctor_render`. |
| `skills/rdd-doctor/scripts/doctor_render.py` | Severity aggregation. Maps findings → exit code (0/1/2/3). Emits human-readable report OR JSON payload. |
| `skills/rdd-doctor/scripts/path_resolver.py` | Resolves real `_lib/` location (`PROJECT_ROOT/_lib/...`). NEVER uses `skills/_lib/` shim. |
| `skills/rdd-doctor/scripts/checks/state_schema_check.py` | Cat 1 — validates 4 `.rddf/state/*.json` files against `_lib/schemas/*.json` using `jsonschema`. |
| `skills/rdd-doctor/scripts/checks/plan_tdd_check.py` | Cat 2 — verifies `.rddf/plans/*.md` contains 5 TDD step markers (loose string match). WARNING only. |
| `skills/rdd-doctor/scripts/checks/roadmap_meta_check.py` | Cat 3 — validates `openspec/changes/*/roadmap-meta.yaml` field completeness + `manual_deps`/`manual_blocks` types. |
| `skills/rdd-doctor/scripts/checks/proposal_table_check.py` | Cat 4 — validates `proposal-suggestions.md` + `proposal-approved.md` Markdown table column counts + required columns. |
| `skills/rdd-doctor/scripts/checks/tasks_checkbox_check.py` | Cat 5 — counts `- [ ]` / `- [x]` in `openspec/changes/*/tasks.md`. Verifies file existence. Emits INFO if `openspec` not on PATH. |

### Tests

| File | Responsibility |
|---|---|
| `tests/unit/test_doctor_render.py` | ≥6 tests: severity→exit-code mapping, JSON payload schema validation, `--quiet` line count. |
| `tests/unit/test_path_resolver.py` | ≥3 tests: real path resolution, error on missing PROJECT_ROOT, never-resolves-via-shim property. |
| `tests/unit/test_state_schema_check.py` | ≥4 tests: each of 4 schema files validated; missing-field case; degraded path (no state files). |
| `tests/unit/test_proposal_table_check.py` | ≥3 tests: well-formed table passes; column count drift reports WARNING; missing link reports WARNING. |
| `tests/integration/test_rdd_doctor.bats` | ≥15 tests across 5 categories + 4 CLI modes + 2 edge cases (fresh project, empty `--category`). |
| `tests/integration/test_rdd_doctor_cli.bats` | ≥5 tests: `--help`, `--version`, `--quiet`, `--category state`, `--json` mode. |
| `tests/integration/test_rdd_doctor_readonly.bats` | ≥3 tests: AC4 — `git status --porcelain` unchanged before/after; checker does NOT invoke `git rm`/`rm -f`. |
| `tests/integration/test_rdd_doctor_cat5_degraded.bats` | ≥2 tests: cat-5 with `openspec` removed from PATH still produces valid report (INFO finding, not exit 3). |
| `tests/fixtures/diseased-repo/` | Fixture with all 5 category defects planted. |
| `tests/fixtures/healthy-repo/` | Empty fixture baseline. |
| `tests/fixtures/diseased-repo/plant_*.sh` | Named mutation helpers (`plant_manual_deps_string_drift`, `drop_plan_step3`, etc.). |

### Documentation

| File | Responsibility |
|---|---|
| `AGENTS.md` | New "rdd-doctor" section (~15 lines). Lists 3 example scenarios where doctor should be run. |
| `tests/README.md` | One-line entry pointing to `rdd-doctor` tests. |
| `tests/smoke.bats` | New test line referencing `rdd-doctor` skill. |

---

### Task 1: Path resolver — direct `_lib/` access (M1 enabler)

**Files:**
- Create: `skills/rdd-doctor/scripts/path_resolver.py`
- Test: `tests/unit/test_path_resolver.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/test_path_resolver.py
import os
import tempfile
from pathlib import Path
import pytest

from skills.rdd_doctor.scripts.path_resolver import resolve_real_lib_path, LibPathNotFoundError


def test_resolves_real_lib_dir_not_shim(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Verifies path resolver returns the real _lib/ dir, not the skills/_lib/ shim."""
    # Setup: real _lib/ + shim skills/_lib/ (shim has same file but wrong content)
    real_lib = tmp_path / "_lib"
    real_lib.mkdir()
    (real_lib / "schemas").mkdir()
    (real_lib / "schemas" / "iteration_schema.json").write_text('{"$id":"REAL"}')

    shim_lib = tmp_path / "skills" / "_lib"
    shim_lib.mkdir(parents=True)
    (shim_lib / "schemas").mkdir()
    (shim_lib / "schemas" / "iteration_schema.json").write_text('{"$id":"SHIM"}')

    monkeypatch.setattr("skills.rdd_doctor.scripts.path_resolver._PROJECT_ROOT_ENV", "RDDF_PROJECT_ROOT")
    monkeypatch.setenv("RDDF_PROJECT_ROOT", str(tmp_path))

    result = resolve_real_lib_path("schemas/iteration_schema.json")
    assert result.exists()
    assert result.read_text() == '{"$id":"REAL"}'


def test_raises_when_real_lib_missing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """No _lib/ directory must raise, not silently fall back to shim."""
    monkeypatch.setenv("RDDF_PROJECT_ROOT", str(tmp_path))

    with pytest.raises(LibPathNotFoundError) as exc_info:
        resolve_real_lib_path("schemas/iteration_schema.json")
    assert "real _lib/" in str(exc_info.value).lower()


def test_never_returns_shim_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """When BOTH real _lib/ and skills/_lib/ shim exist, only real is returned."""
    real_lib = tmp_path / "_lib"
    real_lib.mkdir()
    (real_lib / "schemas").mkdir()
    (real_lib / "schemas" / "foo.json").write_text('"real"')

    shim_lib = tmp_path / "skills" / "_lib"
    shim_lib.mkdir(parents=True)
    (shim_lib / "schemas").mkdir()
    (shim_lib / "schemas" / "foo.json").write_text('"shim"')

    monkeypatch.setenv("RDDF_PROJECT_ROOT", str(tmp_path))

    result = resolve_real_lib_path("schemas/foo.json")
    assert "shim" not in result.read_text()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd .rddf/wt/add-rdd-doctor-skill && pytest tests/unit/test_path_resolver.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'skills.rdd_doctor'`

- [ ] **Step 3: Write minimal implementation**

```python
# skills/rdd-doctor/scripts/path_resolver.py
"""Resolve paths to the real _lib/ directory.

CRITICAL: After commit c3a90fe, `skills/_lib/` is a 6-line shim that sources
`${HOME}/.agents/skills/_lib/`. Any code path that loads JSON schema via
the shim risks silently inheriting stale global state. This module returns
ONLY the real _lib/ location.
"""
from __future__ import annotations

import os
from pathlib import Path

_PROJECT_ROOT_ENV = "RDDF_PROJECT_ROOT"


def _project_root() -> Path:
    raw = os.environ.get(_PROJECT_ROOT_ENV)
    if not raw:
        raise LibPathNotFoundError(
            f"{_PROJECT_ROOT_ENV} env var not set. doctor must be invoked through doctor.sh."
        )
    p = Path(raw).resolve()
    if not p.is_dir():
        raise LibPathNotFoundError(f"{_PROJECT_ROOT_ENV}={p} is not a directory")
    return p


def resolve_real_lib_path(relative: str) -> Path:
    """Return absolute path to `<project_root>/_lib/<relative>`.

    Raises LibPathNotFoundError if the file does not exist at the real location.
    Does NOT consult any shim path.
    """
    root = _project_root()
    real = root / "_lib" / relative
    if not real.is_file():
        raise LibPathNotFoundError(
            f"Real _lib file not found: {real}. "
            f"doctor must resolve from real _lib/, not skills/_lib/ shim."
        )
    return real


class LibPathNotFoundError(FileNotFoundError):
    """Raised when a required file is missing from the real _lib/."""
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd .rddf/wt/add-rdd-doctor-skill && pytest tests/unit/test_path_resolver.py -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Defer commit**

Per repo convention, no per-task commit. Aggregate commit happens in archive phase.

---

### Task 2: Doctor render module — severity aggregation + JSON payload (M1 critical)

**Files:**
- Create: `skills/rdd-doctor/scripts/doctor_render.py`
- Test: `tests/unit/test_doctor_render.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/test_doctor_render.py
import json
import pytest
from datetime import datetime

from skills.rdd_doctor.scripts.doctor_render import (
    Finding,
    Severity,
    render_human,
    render_json,
    exit_code_for,
)


def _finding(severity: Severity, category: str = "state") -> Finding:
    return Finding(
        severity=severity,
        category=category,
        file=".rddf/state/iteration.json",
        line=42,
        snippet='  "current_sprint":',
        fix_hint="re-run guide-plan",
    )


def test_exit_code_0_when_no_findings():
    assert exit_code_for([]) == 0


def test_exit_code_1_when_only_info_and_warning():
    findings = [_finding(Severity.INFO), _finding(Severity.WARNING)]
    assert exit_code_for(findings) == 1


def test_exit_code_2_when_critical_present():
    findings = [_finding(Severity.WARNING), _finding(Severity.CRITICAL)]
    assert exit_code_for(findings) == 2


def test_exit_code_3_on_checker_exception_marker():
    findings = [_finding(Severity.CRITICAL)]
    # checker_exception=True forces exit code 3
    assert exit_code_for(findings, checker_exception=True) == 3


def test_human_report_groups_by_severity():
    findings = [_finding(Severity.CRITICAL), _finding(Severity.WARNING)]
    out = render_human(findings, categories_checked=["state", "plans"])
    assert "=== CRITICAL" in out
    assert "=== WARNING" in out
    assert ".rddf/state/iteration.json" in out


def test_json_payload_schema():
    findings = [_finding(Severity.CRITICAL)]
    payload = render_json(findings, categories_checked=["state"])
    parsed = json.loads(payload)
    assert "timestamp" in parsed
    assert parsed["categories_checked"] == ["state"]
    assert isinstance(parsed["findings"], list)
    assert len(parsed["findings"]) == 1
    f = parsed["findings"][0]
    assert f["severity"] == "CRITICAL"
    assert f["category"] == "state"
    assert f["file"] == ".rddf/state/iteration.json"
    assert f["line"] == 42
    assert f["fix_hint"] == "re-run guide-plan"
    assert parsed["summary"] == {"critical": 1, "warning": 0, "info": 0}


def test_quiet_render_single_line():
    findings = [_finding(Severity.CRITICAL), _finding(Severity.WARNING)]
    # quiet mode (render_quiet) returns at most one line
    from skills.rdd_doctor.scripts.doctor_render import render_quiet
    out = render_quiet(findings)
    lines = [line for line in out.strip().split("\n") if line]
    assert len(lines) <= 1
    assert "CRITICAL" in lines[0]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_doctor_render.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'skills.rdd_doctor'`

- [ ] **Step 3: Write minimal implementation**

```python
# skills/rdd-doctor/scripts/doctor_render.py
"""Aggregate findings, compute exit codes, render human or JSON output."""
from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from enum import Enum
from typing import Iterable


class Severity(str, Enum):
    CRITICAL = "CRITICAL"
    WARNING = "WARNING"
    INFO = "INFO"


@dataclass(frozen=True)
class Finding:
    severity: Severity
    category: str
    file: str
    line: int | None
    snippet: str
    fix_hint: str


def exit_code_for(findings: Iterable[Finding], checker_exception: bool = False) -> int:
    """Map findings to exit code.

    0: all OK
    1: only INFO and/or WARNING
    2: at least one CRITICAL
    3: checker raised internal exception
    """
    if checker_exception:
        return 3
    findings = list(findings)
    if not findings:
        return 0
    severities = {f.severity for f in findings}
    if Severity.CRITICAL in severities:
        return 2
    return 1


def render_human(findings: list[Finding], categories_checked: list[str]) -> str:
    """Human-readable grouped report."""
    by_sev: dict[Severity, list[Finding]] = {s: [] for s in Severity}
    for f in findings:
        by_sev[f.severity].append(f)

    parts: list[str] = []
    parts.append(f"🩺 RDD Doctor Report — {datetime.now(timezone.utc).isoformat()}")
    parts.append("")

    if not findings:
        parts.append("✅ All 5 categories OK")
        return "\n".join(parts)

    icons = {Severity.CRITICAL: "❌", Severity.WARNING: "⚠️ ", Severity.INFO: "ℹ️ "}
    for sev in (Severity.CRITICAL, Severity.WARNING, Severity.INFO):
        items = by_sev[sev]
        if not items:
            continue
        parts.append(f"=== {sev} ({len(items)}) ===")
        for f in items:
            line_part = f"Line {f.line}: " if f.line is not None else ""
            parts.append(f"  {icons[sev]} [{f.category}] {f.file}")
            parts.append(f"     {line_part}{f.snippet}")
            parts.append(f"     Fix: {f.fix_hint}")
        parts.append("")

    counts = {s.value: len(by_sev[s]) for s in Severity}
    parts.append(f"Summary: {counts[Severity.CRITICAL.value]} CRITICAL · {counts[Severity.WARNING.value]} WARNING · {counts[Severity.INFO.value]} INFO")
    return "\n".join(parts)


def render_quiet(findings: list[Finding]) -> str:
    """At most one line: the most severe finding summary."""
    if not findings:
        return "✅ All 5 categories OK"
    by_sev: dict[Severity, list[Finding]] = {s: [] for s in Severity}
    for f in findings:
        by_sev[f.severity].append(f)
    for sev in (Severity.CRITICAL, Severity.WARNING, Severity.INFO):
        if by_sev[sev]:
            return f"{sev.value}: {len(by_sev[sev])} ({by_sev[sev][0].category})"
    return "✅ All 5 categories OK"


def render_json(findings: list[Finding], categories_checked: list[str]) -> str:
    """JSON payload. Schema:
    {timestamp, categories_checked, findings[{severity,category,file,line,snippet,fix_hint}], summary{critical,warning,info}}
    """
    by_sev = {s: 0 for s in Severity}
    for f in findings:
        by_sev[f.severity] += 1
    payload = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "categories_checked": categories_checked,
        "findings": [asdict(f) | {"severity": f.severity.value} for f in findings],
        "summary": {s.value.lower(): by_sev[s] for s in Severity},
    }
    return json.dumps(payload, indent=2)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_doctor_render.py -v`
Expected: PASS (7 tests)

- [ ] **Step 5: Defer commit**

---

### Task 3: cat-1 state schema check (M2 critical path)

**Files:**
- Create: `skills/rdd-doctor/scripts/checks/state_schema_check.py`
- Test: `tests/unit/test_state_schema_check.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/test_state_schema_check.py
import json
import pytest
from pathlib import Path
from unittest.mock import patch

from skills.rdd_doctor.scripts.checks.state_schema_check import run as run_check
from skills.rdd_doctor.scripts.doctor_render import Severity


def _write_state(tmp_path: Path, name: str, data: dict) -> Path:
    state = tmp_path / ".rddf" / "state"
    state.mkdir(parents=True, exist_ok=True)
    f = state / name
    f.write_text(json.dumps(data))
    return f


def _valid_iteration() -> dict:
    return {
        "version": 5,
        "updated_at": "2026-08-07T00:00:00+00:00",
        "current_phase": "v2.1",
        "changes": [],
    }


def test_healthy_state_returns_no_findings(tmp_path: Path):
    _write_state(tmp_path, "iteration.json", _valid_iteration())
    findings = run_check(project_root=tmp_path)
    assert findings == []


def test_missing_required_field_reports_critical(tmp_path: Path):
    bad = _valid_iteration()
    del bad["current_phase"]
    _write_state(tmp_path, "iteration.json", bad)
    findings = run_check(project_root=tmp_path)
    assert any(f.severity == Severity.CRITICAL for f in findings)
    assert any("current_phase" in f.snippet for f in findings)


def test_no_state_directory_emits_no_findings(tmp_path: Path):
    """Empty project (fresh) is OK — INFO not finding."""
    findings = run_check(project_root=tmp_path)
    assert findings == []


def test_uses_real_lib_path_not_shim(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Verify state check resolves _lib/schemas/ from real location, not shim."""
    _write_state(tmp_path, "iteration.json", _valid_iteration())

    # Create real _lib/schemas/ with valid iteration schema
    real_lib = tmp_path / "_lib" / "schemas"
    real_lib.mkdir(parents=True)
    schema_path = real_lib / "iteration_schema.json"
    schema_path.write_text(json.dumps({
        "$schema": "http://json-schema.org/draft-07/schema#",
        "type": "object",
        "required": ["version", "updated_at", "current_phase", "changes"],
        "additionalProperties": False,
        "properties": {
            "version": {"type": "integer"},
            "updated_at": {"type": "string"},
            "current_phase": {"type": "string"},
            "changes": {"type": "array"},
        },
    }))

    # Create shim skills/_lib/schemas/ with WRONG schema (catches if shim is used)
    shim_lib = tmp_path / "skills" / "_lib" / "schemas"
    shim_lib.mkdir(parents=True)
    (shim_lib / "iteration_schema.json").write_text('{"WRONG": "schema"}')

    monkeypatch.setenv("RDDF_PROJECT_ROOT", str(tmp_path))
    findings = run_check(project_root=tmp_path)
    # If real path is used: passes. If shim: would fail with CRITICAL.
    assert findings == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_state_schema_check.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Write minimal implementation**

```python
# skills/rdd-doctor/scripts/checks/state_schema_check.py
"""Cat 1 — Validate .rddf/state/*.json against _lib/schemas/*.json."""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import List

import jsonschema

from skills.rdd_doctor.scripts.doctor_render import Finding, Severity
from skills.rdd_doctor.scripts.path_resolver import resolve_real_lib_path, LibPathNotFoundError


# Map state file basename → schema basename
_STATE_FILES = {
    "state_vector.json": "state_vector_schema.json",
    "sessions.json": "sessions_schema.json",
    "iteration.json": "iteration_schema.json",
    "deps_analysis.json": "deps_analysis_schema.json",
}


def run(project_root: Path | None = None) -> List[Finding]:
    """Run cat-1 against project_root (defaults to RDDF_PROJECT_ROOT env)."""
    if project_root is None:
        project_root = Path(os.environ.get("RDDF_PROJECT_ROOT", "."))
    state_dir = project_root / ".rddf" / "state"
    if not state_dir.is_dir():
        return []

    findings: List[Finding] = []
    for state_name, schema_name in _STATE_FILES.items():
        state_file = state_dir / state_name
        if not state_file.is_file():
            continue
        try:
            schema_path = resolve_real_lib_path(f"schemas/{schema_name}")
        except LibPathNotFoundError as e:
            findings.append(Finding(
                severity=Severity.WARNING,
                category="state",
                file=str(state_file),
                line=None,
                snippet=f"schema {schema_name} not found",
                fix_hint=f"check that _lib/schemas/{schema_name} exists (real path)",
            ))
            continue
        try:
            schema = json.loads(schema_path.read_text())
            data = json.loads(state_file.read_text())
        except json.JSONDecodeError as e:
            findings.append(Finding(
                severity=Severity.CRITICAL,
                category="state",
                file=str(state_file),
                line=e.lineno,
                snippet=f"invalid JSON: {e.msg}",
                fix_hint="re-run guide-plan or restore from backup",
            ))
            continue

        validator = jsonschema.Draft7Validator(schema)
        for error in sorted(validator.iter_errors(data), key=lambda e: list(e.path)):
            line = None
            try:
                line = error.absolute_path and list(error.absolute_path)[0] and None
            except Exception:
                pass
            findings.append(Finding(
                severity=Severity.CRITICAL,
                category="state",
                file=str(state_file),
                line=line,
                snippet=f"{'/'.join(map(str, error.absolute_path)) or '<root>'}: {error.message}",
                fix_hint="re-run guide-plan or manually migrate to current schema",
            ))
    return findings
```

- [ ] **Step 4: Install jsonschema and run test**

```bash
cd .rddf/wt/add-rdd-doctor-skill
pip install jsonschema pytest 2>&1 | tail -3
pytest tests/unit/test_state_schema_check.py -v
```

Expected: PASS (4 tests)

- [ ] **Step 5: Defer commit**

---

### Task 4: cat-3 roadmap-meta check (M2 critical — S4 root cause)

**Files:**
- Create: `skills/rdd-doctor/scripts/checks/roadmap_meta_check.py`
- Test: `tests/unit/test_roadmap_meta_check.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/test_roadmap_meta_check.py
from pathlib import Path
import pytest

from skills.rdd_doctor.scripts.checks.roadmap_meta_check import run as run_check
from skills.rdd_doctor.scripts.doctor_render import Severity


def _make_change(tmp_path: Path, name: str, roadmap_content: str) -> None:
    change_dir = tmp_path / "openspec" / "changes" / name
    change_dir.mkdir(parents=True, exist_ok=True)
    (change_dir / "roadmap-meta.yaml").write_text(roadmap_content)


def test_healthy_roadmap_no_findings(tmp_path: Path):
    _make_change(tmp_path, "foo", "phase: v2.1\ncategory: infra-setup\nchange_type: feature\npriority: P1\nparent_feature: \"\"\n")
    findings = run_check(project_root=tmp_path)
    assert findings == []


def test_manual_deps_string_drifts_reports_critical_with_silently_ignore(tmp_path: Path):
    """S4 root cause: deps stage silently skips this drift. Doctor must catch it."""
    _make_change(tmp_path, "foo", """\
phase: v2.1
category: infra-setup
change_type: feature
priority: P1
parent_feature: ""
manual_deps: "x,y"
manual_blocks: []
""")
    findings = run_check(project_root=tmp_path)
    critical = [f for f in findings if f.severity == Severity.CRITICAL]
    assert len(critical) == 1
    assert "silently ignore" in critical[0].fix_hint
    assert "manual_deps" in critical[0].snippet


def test_manual_blocks_string_drifts_reports_critical(tmp_path: Path):
    _make_change(tmp_path, "foo", """\
phase: v2.1
category: infra-setup
change_type: feature
priority: P1
parent_feature: ""
manual_deps: []
manual_blocks: "a,b"
""")
    findings = run_check(project_root=tmp_path)
    assert any(f.severity == Severity.CRITICAL and "manual_blocks" in f.snippet for f in findings)


def test_missing_required_field_reports_warning(tmp_path: Path):
    """Missing optional field is WARNING; missing required is CRITICAL."""
    _make_change(tmp_path, "foo", "phase: v2.1\n")
    findings = run_check(project_root=tmp_path)
    assert any(f.severity == Severity.WARNING for f in findings)


def test_no_changes_dir_returns_no_findings(tmp_path: Path):
    findings = run_check(project_root=tmp_path)
    assert findings == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_roadmap_meta_check.py -v`
Expected: FAIL

- [ ] **Step 3: Write minimal implementation**

```python
# skills/rdd-doctor/scripts/checks/roadmap_meta_check.py
"""Cat 3 — Validate openspec/changes/*/roadmap-meta.yaml schema and types."""
from __future__ import annotations

import os
from pathlib import Path
from typing import List, Any

import yaml

from skills.rdd_doctor.scripts.doctor_render import Finding, Severity


_REQUIRED_FIELDS = ["phase", "category", "change_type", "priority"]
_RECOMMENDED_FIELDS = ["parent_feature"]
_ARRAY_FIELDS = ["manual_deps", "manual_blocks"]


def _parse_yaml_simple(path: Path) -> Any:
    """Tiny YAML loader that handles the 6 fields roadmap-meta uses."""
    text = path.read_text()
    out: dict[str, Any] = {}
    for raw_line in text.splitlines():
        line = raw_line.split("#", 1)[0].rstrip()
        if not line or ":" not in line:
            continue
        key, _, val = line.partition(":")
        key = key.strip()
        val = val.strip().strip('"').strip("'")
        if val.startswith("[") and val.endswith("]"):
            inner = val[1:-1].strip()
            out[key] = [v.strip().strip('"').strip("'") for v in inner.split(",") if v.strip()] if inner else []
        elif val == "" or val.lower() in ("null", "~"):
            out[key] = None
        else:
            out[key] = val
    return out


def run(project_root: Path | None = None) -> List[Finding]:
    if project_root is None:
        project_root = Path(os.environ.get("RDDF_PROJECT_ROOT", "."))
    changes_root = project_root / "openspec" / "changes"
    if not changes_root.is_dir():
        return []

    findings: List[Finding] = []
    for change_dir in sorted(changes_root.iterdir()):
        if not change_dir.is_dir() or change_dir.name == "archive":
            continue
        meta = change_dir / "roadmap-meta.yaml"
        if not meta.is_file():
            continue

        try:
            data = _parse_yaml_simple(meta)
        except Exception as e:
            findings.append(Finding(
                severity=Severity.CRITICAL,
                category="roadmap-meta",
                file=str(meta),
                line=None,
                snippet=f"YAML parse error: {e}",
                fix_hint="re-run propose or manually fix YAML syntax",
            ))
            continue

        for field in _REQUIRED_FIELDS:
            if field not in data or data[field] in (None, ""):
                findings.append(Finding(
                    severity=Severity.WARNING,
                    category="roadmap-meta",
                    file=str(meta),
                    line=None,
                    snippet=f"missing required field '{field}'",
                    fix_hint="re-run propose to regenerate roadmap-meta.yaml",
                ))

        for field in _ARRAY_FIELDS:
            v = data.get(field)
            if v is not None and not isinstance(v, list):
                findings.append(Finding(
                    severity=Severity.CRITICAL,
                    category="roadmap-meta",
                    file=str(meta),
                    line=None,
                    snippet=f"field '{field}' should be array, found {type(v).__name__}",
                    fix_hint=f"convert '{field}' to YAML list form (e.g. `[{v}]` → `[item1, item2]`); "
                             f"deps-driven execution mode will silently ignore this change otherwise",
                ))

    return findings
```

- [ ] **Step 4: Install pyyaml and run test**

```bash
cd .rddf/wt/add-rdd-doctor-skill
pip install pyyaml 2>&1 | tail -1
pytest tests/unit/test_roadmap_meta_check.py -v
```

Expected: PASS (5 tests)

- [ ] **Step 5: Defer commit**

---

### Task 5: cat-4 proposal table check (with parser co-existence note)

**Files:**
- Create: `skills/rdd-doctor/scripts/checks/proposal_table_check.py`
- Test: `tests/unit/test_proposal_table_check.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/test_proposal_table_check.py
from pathlib import Path
import pytest

from skills.rdd_doctor.scripts.checks.proposal_table_check import run as run_check
from skills.rdd_doctor.scripts.doctor_render import Severity


def test_welllyformed_proposal_suggestions_returns_no_findings(tmp_path: Path):
    (tmp_path / "proposal-suggestions.md").write_text(
        "# 提案池\n\n"
        "| 提案 | 优先级 | 来源 | 添加时间 | 状态 |\n"
        "|------|--------|------|----------|------|\n"
        "| [foo](improvements/foo.md) | P1 | src | 2026-08-07 | 待审 |\n"
    )
    findings = run_check(project_root=tmp_path)
    assert findings == []


def test_column_count_drift_reports_warning(tmp_path: Path):
    (tmp_path / "proposal-suggestions.md").write_text(
        "| 提案 | 优先级 | 来源 | 添加时间 |\n"  # missing 状态 column
        "|------|--------|------|----------|\n"
        "| [foo](improvements/foo.md) | P1 | src | 2026-08-07 |\n"
    )
    findings = run_check(project_root=tmp_path)
    assert any(f.severity == Severity.WARNING for f in findings)
    assert any("4 columns" in f.snippet or "5" in f.snippet for f in findings)


def test_broken_link_reports_warning(tmp_path: Path):
    (tmp_path / "proposal-suggestions.md").write_text(
        "| 提案 | 优先级 | 来源 | 添加时间 | 状态 |\n"
        "|------|--------|------|----------|------|\n"
        "| [foo](improvements/nonexistent.md) | P1 | src | 2026-08-07 | 待审 |\n"
    )
    findings = run_check(project_root=tmp_path)
    assert any(f.severity == Severity.WARNING for f in findings)
    assert any("nonexistent" in f.snippet for f in findings)


def test_no_proposal_files_returns_no_findings(tmp_path: Path):
    findings = run_check(project_root=tmp_path)
    assert findings == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_proposal_table_check.py -v`

- [ ] **Step 3: Write minimal implementation**

```python
# skills/rdd-doctor/scripts/checks/proposal_table_check.py
"""Cat 4 — Validate proposal-suggestions.md and proposal-approved.md Markdown tables.

Note: This module uses a lightweight inline parser to avoid circular dependency
on _lib/parse_approved.py (which lives in a separate worktree change
fix-design-proposal-review-approved-parsing). After that change merges, this
module can be migrated to reuse that parser.
"""
from __future__ import annotations

import os
import re
from pathlib import Path
from typing import List

from skills.rdd_doctor.scripts.doctor_render import Finding, Severity


_FILES = ["proposal-suggestions.md", "proposal-approved.md"]
_EXPECTED_COLUMNS = {
    "proposal-suggestions.md": 5,
    "proposal-approved.md": 3,
}
_ROW_PATTERN = re.compile(r"^\|\s*\[([^\]]+)\]\(([^)]+)\)\s*\|")


def _count_columns(line: str) -> int:
    """Count cell separators in a Markdown table row."""
    return line.count("|") - 1


def run(project_root: Path | None = None) -> List[Finding]:
    if project_root is None:
        project_root = Path(os.environ.get("RDDF_PROJECT_ROOT", "."))
    findings: List[Finding] = []

    for fname in _FILES:
        path = project_root / fname
        if not path.is_file():
            continue
        expected_cols = _EXPECTED_COLUMNS[fname]
        lines = path.read_text().splitlines()
        line_no = 0
        in_data = False
        for raw in lines:
            line_no += 1
            stripped = raw.strip()
            if stripped.startswith("|------") or stripped.startswith("| ---"):
                in_data = True
                continue
            if not in_data or not stripped.startswith("|"):
                continue
            m = _ROW_PATTERN.match(stripped)
            if not m:
                continue
            link_target = m.group(2)
            cols = _count_columns(stripped)
            if cols != expected_cols:
                findings.append(Finding(
                    severity=Severity.WARNING,
                    category="proposal-table",
                    file=fname,
                    line=line_no,
                    snippet=f"row has {cols} columns, expected {expected_cols}",
                    fix_hint=f"add/remove columns to match expected schema",
                ))
            if link_target.startswith("improvements/") and not (project_root / link_target).is_file():
                findings.append(Finding(
                    severity=Severity.WARNING,
                    category="proposal-table",
                    file=fname,
                    line=line_no,
                    snippet=f"broken link to {link_target}",
                    fix_hint="verify the improvements file exists or remove this row",
                ))

    return findings
```

- [ ] **Step 4: Run test**

Run: `pytest tests/unit/test_proposal_table_check.py -v`
Expected: PASS (4 tests)

- [ ] **Step 5: Defer commit**

---

### Task 6: cat-5 tasks-checkbox check (with degraded path)

**Files:**
- Create: `skills/rdd-doctor/scripts/checks/tasks_checkbox_check.py`
- Test: `tests/unit/test_tasks_checkbox_check.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/test_tasks_checkbox_check.py
import os
from pathlib import Path
import pytest

from skills.rdd_doctor.scripts.checks.tasks_checkbox_check import run as run_check
from skills.rdd_doctor.scripts.doctor_render import Severity


def _make_change_with_tasks(tmp_path: Path, name: str, content: str) -> None:
    change = tmp_path / "openspec" / "changes" / name
    change.mkdir(parents=True)
    (change / "tasks.md").write_text(content)


def test_welllyformed_tasks_returns_no_findings(tmp_path: Path):
    _make_change_with_tasks(tmp_path, "foo", """\
## 1. Setup
- [ ] 1.1 do thing one
- [x] 1.2 do thing two
""")
    findings = run_check(project_root=tmp_path)
    assert findings == []


def test_missing_tasks_file_reports_warning(tmp_path: Path):
    (tmp_path / "openspec" / "changes" / "foo").mkdir(parents=True)
    # No tasks.md
    findings = run_check(project_root=tmp_path)
    assert any(f.severity == Severity.WARNING and "missing" in f.snippet for f in findings)


def test_zero_checkboxes_reports_warning(tmp_path: Path):
    _make_change_with_tasks(tmp_path, "foo", "# Empty tasks\n\nNo items here.\n")
    findings = run_check(project_root=tmp_path)
    assert any(f.severity == Severity.WARNING and "checkbox count = 0" in f.snippet for f in findings)


def test_emit_info_when_openspec_cli_missing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Degraded path: openspec not on PATH → INFO finding, NOT exit-3."""
    _make_change_with_tasks(tmp_path, "foo", "- [ ] 1.1 do thing\n")
    monkeypatch.setenv("PATH", "")  # Strip PATH so 'openspec' is unfindable
    findings = run_check(project_root=tmp_path)
    info_findings = [f for f in findings if f.severity == Severity.INFO]
    assert any("openspec status unavailable" in f.snippet for f in info_findings)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_tasks_checkbox_check.py -v`

- [ ] **Step 3: Write minimal implementation**

```python
# skills/rdd-doctor/scripts/checks/tasks_checkbox_check.py
"""Cat 5 — Validate openspec/changes/*/tasks.md checkbox state.

v1 intentionally does NOT cross-check with `openspec status --json` because:
1. openspec CLI v1.4.1 requires `schema:` field in .openspec.yaml (currently
   approve_proposal.sh does not write it)
2. `isComplete` is derived from artifact existence, not checkbox progress —
   making any cross-check vacuous even when CLI works

Degraded path: emit INFO finding when `openspec` is not on $PATH. This is
observability, not a failure (exit 3 reserved for genuine exceptions).
"""
from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import List

from skills.rdd_doctor.scripts.doctor_render import Finding, Severity


_CHECKBOX_PATTERN_OPEN = "- [ ]"
_CHECKBOX_PATTERN_DONE = "- [x]"


def _openspec_available() -> bool:
    return shutil.which("openspec") is not None


def run(project_root: Path | None = None) -> List[Finding]:
    if project_root is None:
        project_root = Path(os.environ.get("RDDF_PROJECT_ROOT", "."))
    changes_root = project_root / "openspec" / "changes"
    if not changes_root.is_dir():
        return []

    findings: List[Finding] = []

    if not _openspec_available():
        findings.append(Finding(
            severity=Severity.INFO,
            category="tasks-checkbox",
            file="(global)",
            line=None,
            snippet="openspec status unavailable, skipping cross-check",
            fix_hint="install openspec CLI for v2 to enable status cross-check; "
                     "v1 cat-5 runs without it",
        ))

    for change_dir in sorted(changes_root.iterdir()):
        if not change_dir.is_dir() or change_dir.name == "archive":
            continue
        tasks = change_dir / "tasks.md"
        if not tasks.is_file():
            findings.append(Finding(
                severity=Severity.WARNING,
                category="tasks-checkbox",
                file=str(tasks),
                line=None,
                snippet="tasks.md missing for active change",
                fix_hint="run guide-plan fill to generate tasks.md",
            ))
            continue
        text = tasks.read_text()
        open_count = text.count(_CHECKBOX_PATTERN_OPEN)
        done_count = text.count(_CHECKBOX_PATTERN_DONE)
        total = open_count + done_count
        if total == 0:
            findings.append(Finding(
                severity=Severity.WARNING,
                category="tasks-checkbox",
                file=str(tasks),
                line=None,
                snippet="checkbox count = 0 but change is active",
                fix_hint="add task checkboxes; `execute` cannot track progress without them",
            ))
    return findings
```

- [ ] **Step 4: Run test**

Run: `pytest tests/unit/test_tasks_checkbox_check.py -v`
Expected: PASS (4 tests)

- [ ] **Step 5: Defer commit**

---

### Task 7: cat-2 plan TDD structure check (loose matching)

**Files:**
- Create: `skills/rdd-doctor/scripts/checks/plan_tdd_check.py`
- Test: `tests/unit/test_plan_tdd_check.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/test_plan_tdd_check.py
from pathlib import Path
import pytest

from skills.rdd_doctor.scripts.checks.plan_tdd_check import run as run_check
from skills.rdd_doctor.scripts.doctor_render import Severity


def _write_plan(tmp_path: Path, name: str, content: str) -> None:
    plans = tmp_path / ".rddf" / "plans"
    plans.mkdir(parents=True)
    (plans / f"{name}.md").write_text(content)


def test_complete_plan_no_findings(tmp_path: Path):
    _write_plan(tmp_path, "foo", """\
# Plan
### Task 1: Setup
- [ ] Step 1: Write the failing test
- [ ] Step 2: Run test to verify it fails
- [ ] Step 3: Write minimal implementation
- [ ] Step 4: Run test to verify it passes
- [ ] Step 5: Defer commit
""")
    findings = run_check(project_root=tmp_path)
    assert findings == []


def test_missing_step_reports_warning(tmp_path: Path):
    """Missing 'Verify fail' step → WARNING (S3 root cause scenario)."""
    _write_plan(tmp_path, "foo", """\
# Plan
### Task 1: Setup
- [ ] Step 1: Write the failing test
- [ ] Step 2: skip verify fail
- [ ] Step 3: Write minimal implementation
- [ ] Step 4: Run test to verify it passes
- [ ] Step 5: Defer commit
""")
    findings = run_check(project_root=tmp_path)
    assert any(f.severity == Severity.WARNING and "Verify fail" in f.snippet for f in findings)


def test_no_plans_dir_returns_no_findings(tmp_path: Path):
    findings = run_check(project_root=tmp_path)
    assert findings == []
```

- [ ] **Step 2: Run test to verify it fails**

- [ ] **Step 3: Write minimal implementation**

```python
# skills/rdd-doctor/scripts/checks/plan_tdd_check.py
"""Cat 2 — Loose check for TDD 5-step structure in .rddf/plans/*.md.

WARNING only. Loose matching: 5 step markers must be present, but does NOT
enforce specific phrasing beyond the canonical marker. False-positive risk
is real; tune on the real corpus during execute phase.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import List

from skills.rdd_doctor.scripts.doctor_render import Finding, Severity


_STEP_MARKERS = [
    "Write the failing test",
    "Run test to verify it fails",
    "Write minimal implementation",
    "Run test to verify it passes",
    "Defer commit",  # rdd-workflow convention
]


def run(project_root: Path | None = None) -> List[Finding]:
    if project_root is None:
        project_root = Path(os.environ.get("RDDF_PROJECT_ROOT", "."))
    plans_dir = project_root / ".rddf" / "plans"
    if not plans_dir.is_dir():
        return []

    findings: List[Finding] = []
    for plan_file in sorted(plans_dir.glob("*.md")):
        text = plan_file.read_text()
        missing = [m for m in _STEP_MARKERS if m not in text]
        if missing:
            findings.append(Finding(
                severity=Severity.WARNING,
                category="plan-tdd",
                file=str(plan_file),
                line=None,
                snippet=f"missing TDD step markers: {', '.join(missing)}",
                fix_hint="`execute` may misread steps without the canonical 5-step structure",
            ))
    return findings
```

- [ ] **Step 4: Run test**

Run: `pytest tests/unit/test_plan_tdd_check.py -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Defer commit**

---

### Task 8: Doctor main entry — single Python process aggregating all checkers

**Files:**
- Create: `skills/rdd-doctor/scripts/doctor_main.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/test_doctor_main.py
import pytest
from pathlib import Path

from skills.rdd_doctor.scripts.doctor_main import aggregate_findings
from skills.rdd_doctor.scripts.doctor_render import Severity


def test_aggregate_runs_all_5_categories(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """aggregate_findings invokes all 5 checker modules and combines results."""
    monkeypatch.setenv("RDDF_PROJECT_ROOT", str(tmp_path))
    findings, categories_checked = aggregate_findings(category=None)
    assert set(categories_checked) == {"state", "plan-tdd", "roadmap-meta", "proposal-table", "tasks-checkbox"}


def test_aggregate_with_category_filter(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("RDDF_PROJECT_ROOT", str(tmp_path))
    findings, categories_checked = aggregate_findings(category="state")
    assert categories_checked == ["state"]


def test_aggregate_handles_checker_exception(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """If one checker raises, others still report."""
    import skills.rdd_doctor.scripts.doctor_main as main_mod

    def broken_check(project_root):
        raise RuntimeError("simulated checker crash")

    monkeypatch.setattr(main_mod, "_CHECKERS", {
        "broken": broken_check,
        "ok": lambda p: [],
    })
    findings, categories_checked = aggregate_findings(category=None)
    # Should not raise; should still report categories_checked
    assert isinstance(findings, list)
```

- [ ] **Step 2: Run test to verify it fails**

- [ ] **Step 3: Write minimal implementation**

```python
# skills/rdd-doctor/scripts/doctor_main.py
"""Doctor main: single Python process importing all 5 checkers + aggregator."""
from __future__ import annotations

import os
import traceback
from pathlib import Path
from typing import List, Tuple

from skills.rdd_doctor.scripts.doctor_render import Finding, Severity, exit_code_for
from skills.rdd_doctor.scripts import (
    state_schema_check,
    plan_tdd_check,
    roadmap_meta_check,
    proposal_table_check,
    tasks_checkbox_check,
)


_CHECKERS = {
    "state": state_schema_check.run,
    "plan-tdd": plan_tdd_check.run,
    "roadmap-meta": roadmap_meta_check.run,
    "proposal-table": proposal_table_check.run,
    "tasks-checkbox": tasks_checkbox_check.run,
}


def aggregate_findings(category: str | None) -> Tuple[List[Finding], List[str]]:
    """Run all 5 checkers (or filtered subset) and aggregate findings.

    Returns (findings, categories_checked).
    A checker exception is converted to a single CRITICAL finding rather than
    aborting the whole run.
    """
    project_root = Path(os.environ.get("RDDF_PROJECT_ROOT", "."))
    findings: List[Finding] = []
    categories_checked: List[str] = []

    selected = {category: _CHECKERS[category]} if category else _CHECKERS
    for name, fn in selected.items():
        categories_checked.append(name)
        try:
            cat_findings = fn(project_root=project_root)
            findings.extend(cat_findings)
        except Exception as e:
            findings.append(Finding(
                severity=Severity.CRITICAL,
                category=name,
                file="(checker)",
                line=None,
                snippet=f"checker raised {type(e).__name__}: {e}",
                fix_hint="report bug; this is an internal doctor failure",
            ))

    return findings, categories_checked


def main() -> int:
    import argparse
    parser = argparse.ArgumentParser(prog="rdd-doctor")
    parser.add_argument("--json", action="store_true", help="Write .rddf/state/.doctor-report.json")
    parser.add_argument("--category", choices=list(_CHECKERS.keys()), help="Run only this category")
    parser.add_argument("--quiet", action="store_true", help="Single-line output, most severe only")
    parser.add_argument("--version", action="store_true")
    args = parser.parse_args()

    if args.version:
        print("rdd-doctor 0.1.0")
        return 0

    findings, categories_checked = aggregate_findings(category=args.category)

    if args.json:
        from skills.rdd_doctor.scripts.doctor_render import render_json
        report_path = Path(".rddf/state/.doctor-report.json")
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(render_json(findings, categories_checked))
        print(f"📋 Report: {report_path}")
    elif args.quiet:
        from skills.rdd_doctor.scripts.doctor_render import render_quiet
        print(render_quiet(findings))
    else:
        from skills.rdd_doctor.scripts.doctor_render import render_human
        print(render_human(findings, categories_checked))

    return exit_code_for(findings)


if __name__ == "__main__":
    sys.exit(main())
```

Note: must `import sys` at top for the `sys.exit(main())` line. Adding now:

```python
import sys
```

(at the top, with other stdlib imports)

- [ ] **Step 4: Run test**

Run: `pytest tests/unit/test_doctor_main.py -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Defer commit**

---

### Task 9: Bash entry — flag parsing + invocation contract

**Files:**
- Create: `skills/rdd-doctor/scripts/doctor.sh`

- [ ] **Step 1: Write the bash test**

```bash
# tests/integration/test_rdd_doctor.bats (append)
load 'test_helper'

@test "doctor.sh exists and is executable" {
    [ -x "skills/rdd-doctor/scripts/doctor.sh" ]
}

@test "doctor.sh --help prints usage" {
    run bash skills/rdd-doctor/scripts/doctor.sh --help
    [ "$status" -eq 0 ]
    [[ "$output" == *"rdd-doctor"* ]]
}

@test "doctor.sh --version prints version" {
    run bash skills/rdd-doctor/scripts/doctor.sh --version
    [ "$status" -eq 0 ]
    [[ "$output" == *"0.1.0"* ]]
}

@test "doctor.sh with no flags runs and exits 0 on healthy project" {
    run bash skills/rdd-doctor/scripts/doctor.sh
    [ "$status" -eq 0 ]
}

@test "doctor.sh --json writes .doctor-report.json" {
    rm -f .rddf/state/.doctor-report.json
    run bash skills/rdd-doctor/scripts/doctor.sh --json
    [ "$status" -eq 0 ]
    [ -f .rddf/state/.doctor-report.json ]
}

@test "doctor.sh --category state runs only state checker" {
    run bash skills/rdd-doctor/scripts/doctor.sh --category state
    [ "$status" -eq 0 ]
}
```

- [ ] **Step 2: Run bats to verify they fail**

Run: `bats tests/integration/test_rdd_doctor.bats -t`

- [ ] **Step 3: Write minimal doctor.sh**

```bash
#!/usr/bin/env bash
# skills/rdd-doctor/scripts/doctor.sh
# Bash entry for rdd-doctor skill.
#
# Forwards all flags to the Python implementation. Sets RDDF_PROJECT_ROOT
# from git toplevel so checkers can resolve real _lib/ paths.

set -euo pipefail

PROJECT_ROOT="${PROJECT_ROOT:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
export RDDF_PROJECT_ROOT="$PROJECT_ROOT"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" 2>/dev/null && pwd)"

# Use a single Python process that imports all checkers.
exec python3 -m skills.rdd_doctor.scripts.doctor_main "$@"
```

Make executable: `chmod +x skills/rdd-doctor/scripts/doctor.sh`

- [ ] **Step 4: Run bats to verify they pass**

Run: `bats tests/integration/test_rdd_doctor.bats -t`
Expected: PASS (6 tests)

- [ ] **Step 5: Defer commit**

---

### Task 10: SKILL.md + smoke.bats registration

**Files:**
- Create: `skills/rdd-doctor/SKILL.md`
- Modify: `tests/smoke.bats`

- [ ] **Step 1: Write SKILL.md**

```markdown
---
name: rdd-doctor
description: 手动触发的只读诊断工具 — 校验 5 类结构化文件（.rddf/state/*.json schema / .rddf/plans/*.md TDD 5 步 / openspec/changes/*/roadmap-meta.yaml / proposal-*.md 表格 / openspec/changes/*/tasks.md checkbox）。输出分级报告（CRITICAL/WARNING/INFO）+ 可选 JSON 写入 .rddf/state/.doctor-report.json。退出码对齐 openspec validate (0/1/2/3)。**手动触发 only**，不修改任何 tracked / gitignored 文件（除了 --json 输出）。
license: MIT
compatibility: Requires bash + git + python3.11+ + jsonschema + pyyaml
metadata:
  author: rdd-workflow
  version: 0.1.0
  user-invocable: true
---

# rdd-doctor

## 调用

```bash
bash skills/rdd-doctor/scripts/doctor.sh [--json] [--category state|plan-tdd|roadmap-meta|proposal-table|tasks-checkbox] [--quiet]
```

## 何时该跑

1. **感觉"流程哪里不对"** → 5 秒排查入口
2. **修改 `_lib/schemas/` 后** → 跑 `--category state` 看是否有旧 state 文件需要迁移
3. **CI 升级 `STRICT_ARCH_GATE=yes` 之前** → 跑一次预估会暴露多少问题
4. **接手别人工作树** → 跑一次看 `.rddf/state/*.json` 是否干净

## 退出码

| Code | 含义 |
|------|------|
| 0 | 所有 5 类 OK |
| 1 | 仅 INFO + WARNING，无 CRITICAL |
| 2 | 至少 1 个 CRITICAL |
| 3 | checker 内部异常（其他类仍能报告） |
```

- [ ] **Step 2: Add smoke.bats registration**

Find the smoke.bats file and add a new test line:

```bash
# tests/smoke.bats — add a new test for rdd-doctor (somewhere in the skill matrix)
@test "rdd-doctor: skill file exists and is registered" {
    [ -f "skills/rdd-doctor/SKILL.md" ]
    grep -q "name: rdd-doctor" skills/rdd-doctor/SKILL.md
}
```

- [ ] **Step 3: Run smoke test**

Run: `bats tests/smoke.bats -t`
Expected: PASS (including new rdd-doctor line)

- [ ] **Step 4: Defer commit**

---

### Task 11: Documentation sync — AGENTS.md + tests/README.md

**Files:**
- Modify: `AGENTS.md`
- Modify: `tests/README.md`

- [ ] **Step 1: Add rdd-doctor section to AGENTS.md**

Append at end of AGENTS.md:

```markdown

## rdd-doctor (manual diagnostic skill)

When to invoke `skill_use("rdd-doctor")` (manual trigger only):
1. After completing a phase, before moving to the next — quick sanity check that no file drift has accumulated
2. After modifying `_lib/schemas/*.json` — verify no `.rddf/state/*.json` files are stuck on the old schema
3. Before upgrading `STRICT_ARCH_GATE=yes` or `STRICT_DESIGN_GATE=yes` — preview how many issues the strict mode would surface
4. When troubleshooting a workflow that "feels broken" but no specific error is showing

NOT to run rdd-doctor:
- As part of an automated phase entry (v1 is manual only)
- To fix files (doctor is read-only; for fixes use the relevant skill like `guide-arch` or `guide-plan`)
- To replace any existing gate (`rdd-env-check`, `arch-quality-gate`, etc.)

Flags: `--json` (write `.rddf/state/.doctor-report.json`), `--category <name>` (run only one of 5 categories), `--quiet` (single-line output). Exit codes: 0/1/2/3 matching `openspec validate`.
```

- [ ] **Step 2: Add 1-line entry to tests/README.md**

Find an existing entry like:

```markdown
- `rdd-workflow-writing-plans`: ...
```

And add below it:

```markdown
- `rdd-doctor`: Manual read-only diagnostic over 5 categories of structured files (state JSON, plan TDD structure, roadmap-meta, proposal tables, tasks checkboxes).
```

- [ ] **Step 3: Verify no broken links**

Run: `grep -E "rdd-doctor" AGENTS.md tests/README.md`
Expected: 2 hits (one each)

- [ ] **Step 4: Defer commit**

---

### Task 12: Diseased fixture repo + final integration smoke

**Files:**
- Create: `tests/fixtures/diseased-repo/` (with planted defects)
- Create: `tests/fixtures/healthy-repo/` (clean baseline)

- [ ] **Step 1: Create fixture helpers**

```bash
mkdir -p tests/fixtures/healthy-repo/.rddf/state tests/fixtures/diseased-repo/.rddf/state tests/fixtures/diseased-repo/openspec/changes/drift-change tests/fixtures/diseased-repo/.rddf/plans
```

- [ ] **Step 2: Plant defects via helpers**

```bash
# tests/fixtures/diseased-repo/.rddf/state/iteration.json — missing required field
cat > tests/fixtures/diseased-repo/.rddf/state/iteration.json <<EOF
{
  "version": 5,
  "updated_at": "2026-08-07T00:00:00+00:00",
  "changes": []
}
EOF

# tests/fixtures/diseased-repo/openspec/changes/drift-change/roadmap-meta.yaml — manual_deps as string
mkdir -p tests/fixtures/diseased-repo/openspec/changes/drift-change
cat > tests/fixtures/diseased-repo/openspec/changes/drift-change/roadmap-meta.yaml <<EOF
phase: v2.1
category: infra-setup
change_type: feature
priority: P1
parent_feature: ""
manual_deps: "x,y"
manual_blocks: []
EOF

# Empty tasks.md (zero checkboxes) — cat-5 will report
cat > tests/fixtures/diseased-repo/openspec/changes/drift-change/tasks.md <<EOF
# Drift change tasks
(no items yet)
EOF

# Plan missing "Verify fail" step
cat > tests/fixtures/diseased-repo/.rddf/plans/bad-plan.md <<EOF
# Bad Plan
### Task 1
- [ ] Step 1: Write the failing test
- [ ] Step 2: (skipped)
- [ ] Step 3: Write minimal implementation
- [ ] Step 4: Run test to verify it passes
- [ ] Step 5: Defer commit
EOF

# Proposal with column drift
cat > tests/fixtures/diseased-repo/proposal-suggestions.md <<EOF
| 提案 | 优先级 | 来源 | 添加时间 |
|------|--------|------|----------|
| [foo](improvements/foo.md) | P1 | src | 2026-08-07 |
EOF
```

- [ ] **Step 3: Healthy fixture (empty baseline)**

```bash
mkdir -p tests/fixtures/healthy-repo
# Leave it empty (no .rddf/, no openspec/) — represents fresh project
```

- [ ] **Step 4: Add integration test using fixtures**

```bash
# tests/integration/test_rdd_doctor_fixtures.bats
load 'test_helper'

setup() {
    export FIXTURE_DISEASED="$BATS_TEST_DIRNAME/../fixtures/diseased-repo"
    export FIXTURE_HEALTHY="$BATS_TEST_DIRNAME/../fixtures/healthy-repo"
}

@test "doctor reports at least one CRITICAL on diseased fixture" {
    RDDF_PROJECT_ROOT="$FIXTURE_DISEASED" run bash skills/rdd-doctor/scripts/doctor.sh
    [ "$status" -eq 2 ]
    [[ "$output" == *"CRITICAL"* ]]
}

@test "doctor on healthy fixture exits 0" {
    RDDF_PROJECT_ROOT="$FIXTURE_HEALTHY" run bash skills/rdd-doctor/scripts/doctor.sh
    [ "$status" -eq 0 ]
    [[ "$output" == *"All 5 categories OK"* ]]
}

@test "doctor S4 root cause detected — manual_deps as string" {
    RDDF_PROJECT_ROOT="$FIXTURE_DISEASED" run bash skills/rdd-doctor/scripts/doctor.sh
    [[ "$output" == *"silently ignore"* ]]
    [[ "$output" == *"manual_deps"* ]]
}
```

- [ ] **Step 5: Run bats**

Run: `bats tests/integration/test_rdd_doctor_fixtures.bats -t`
Expected: PASS (3 tests)

- [ ] **Step 6: Defer commit**

---

### Task 13: Read-only enforcement test (AC4)

**Files:**
- Create: `tests/integration/test_rdd_doctor_readonly.bats`

- [ ] **Step 1: Write the test**

```bash
load 'test_helper'

setup() {
    FIXTURE="$BATS_TEST_DIRNAME/../fixtures/diseased-repo"
    export FIXTURE
}

@test "doctor does not modify git tracked files (AC4)" {
    RDDF_PROJECT_ROOT="$FIXTURE" run bash skills/rdd-doctor/scripts/doctor.sh
    cd "$FIXTURE"
    # No git repo here, but verify only .rddf/state/.doctor-report.json is created (and only with --json)
    [ ! -f openspec/changes/drift-change/roadmap-meta.yaml.bak ]
    [ ! -f openspec/changes/drift-change/roadmap-meta.yaml~ ]
}

@test "doctor --json only creates .rddf/state/.doctor-report.json" {
    RDDF_PROJECT_ROOT="$FIXTURE" rm -f .rddf/state/.doctor-report.json
    RDDF_PROJECT_ROOT="$FIXTURE" run bash skills/rdd-doctor/scripts/doctor.sh --json
    [ -f "$FIXTURE/.rddf/state/.doctor-report.json" ]
    # Verify only the report file was created
    created=$(find "$FIXTURE" -newer "$FIXTURE/openspec/changes/drift-change/tasks.md" -type f 2>/dev/null | wc -l)
    [ "$created" -eq 1 ]  # only .doctor-report.json
}

@test "checker does not invoke git rm or rm -f (AC4)" {
    # Run with PATH shadow that fails on rm / git rm
    cat > "$BATS_TMPDIR/no_rm.sh" <<'EOF'
#!/bin/bash
exit 99
EOF
    chmod +x "$BATS_TMPDIR/no_rm.sh"
    PATH="$BATS_TMPDIR/no_rm.sh:$PATH" RDDF_PROJECT_ROOT="$FIXTURE" \
        run bash skills/rdd-doctor/scripts/doctor.sh
    [ "$status" -ne 99 ]  # doctor should NOT have tried to call rm
}
```

- [ ] **Step 2: Run bats**

Run: `bats tests/integration/test_rdd_doctor_readonly.bats -t`
Expected: PASS (3 tests)

- [ ] **Step 3: Defer commit**

---

### Task 14: cat-5 degraded path test (MUST #12 + AC5)

**Files:**
- Create: `tests/integration/test_rdd_doctor_cat5_degraded.bats`

- [ ] **Step 1: Write the test**

```bash
load 'test_helper'

@test "cat-5 emits INFO (not exit 3) when openspec not on PATH" {
    FIXTURE="$BATS_TEST_DIRNAME/../fixtures/diseased-repo"
    # Create empty bin dir with no openspec
    EMPTY_BIN="$BATS_TMPDIR/empty_bin"
    mkdir -p "$EMPTY_BIN"
    PATH="$EMPTY_BIN" RDDF_PROJECT_ROOT="$FIXTURE" run bash skills/rdd-doctor/scripts/doctor.sh
    # Should NOT be exit code 3 (which would mean checker exception)
    [ "$status" -ne 3 ]
    [[ "$output" == *"openspec status unavailable"* ]]
}

@test "cat-5 produces valid output even with degraded CLI" {
    FIXTURE="$BATS_TEST_DIRNAME/../fixtures/diseased-repo"
    EMPTY_BIN="$BATS_TMPDIR/empty_bin2"
    mkdir -p "$EMPTY_BIN"
    PATH="$EMPTY_BIN" RDDF_PROJECT_ROOT="$FIXTURE" run bash skills/rdd-doctor/scripts/doctor.sh
    # Should still detect CRITICAL findings from other categories
    [[ "$output" == *"CRITICAL"* ]]
}
```

- [ ] **Step 2: Run bats**

Run: `bats tests/integration/test_rdd_doctor_cat5_degraded.bats -t`
Expected: PASS (2 tests)

- [ ] **Step 3: Defer commit**

---

### Task 15: Final regression + integration smoke

**Files:** (no new files; run existing test suite)

- [ ] **Step 1: Run full regression**

Run: `./test.sh --full --regression`
Expected: All green (no new failures beyond `tests/KNOWN_FAILURES.txt` baseline)

- [ ] **Step 2: Run doctor against the real rdd-workflow repo as smoke**

Run: `cd /workspace/project/rdd-workflow && bash skills/rdd-doctor/scripts/doctor.sh`
Expected: Real-world output, useful findings (the repo itself has known drift)

- [ ] **Step 3: Verify all AC1-AC10 success criteria**

- [ ] ✅ ≥15 bats tests in `tests/integration/test_rdd_doctor.bats` + related
- [ ] ✅ ≥6 pytest tests in `tests/unit/test_doctor_render.py`
- [ ] ✅ All 5 categories covered with ≥2 scenarios each
- [ ] ✅ 4 CLI modes (default / --json / --category / --quiet) tested
- [ ] ✅ Exit codes 0/1/2/3 mapped correctly
- [ ] ✅ smoke.bats includes rdd-doctor
- [ ] ✅ Read-only verified (git status unchanged)
- [ ] ✅ cat-5 degraded path works
- [ ] ✅ AGENTS.md + tests/README.md updated

- [ ] **Step 4: Defer commit**

---

### Task 16: Aggregate commit + archive pre-flight

- [ ] **Step 1: Verify all task checkboxes in `openspec/changes/add-rdd-doctor-skill/tasks.md` are `[x]`**

Run: `grep -c "^- \[ \]" openspec/changes/add-rdd-doctor-skill/tasks.md`
Expected: 0 (all complete) — if not, finish remaining tasks first

- [ ] **Step 2: Stage all changes**

```bash
git add skills/rdd-doctor/ tests/integration/test_rdd_doctor*.bats tests/unit/test_doctor*.py tests/unit/test_path_resolver.py tests/unit/test_state_schema_check.py tests/unit/test_roadmap_meta_check.py tests/unit/test_proposal_table_check.py tests/unit/test_tasks_checkbox_check.py tests/fixtures/ AGENTS.md tests/README.md tests/smoke.bats
git status --short  # verify what will be committed
```

- [ ] **Step 3: Aggregate commit on worktree branch**

```bash
git commit -m "feat(rdd-doctor): implement 5-category read-only diagnostic skill

- skills/rdd-doctor/scripts/path_resolver.py: always resolve real _lib/, never shim
- skills/rdd-doctor/scripts/doctor_render.py: severity aggregation + JSON payload
- skills/rdd-doctor/scripts/doctor_main.py: single-process dispatcher (perf)
- skills/rdd-doctor/scripts/doctor.sh: bash entry, --json/--category/--quiet flags
- skills/rdd-doctor/scripts/checks/{state,plan_tdd,roadmap_meta,proposal_table,tasks_checkbox}_check.py
- skills/rdd-doctor/SKILL.md: frontmatter + invocation contract
- tests/unit/test_{path_resolver,doctor_render,doctor_main,state_schema_check,roadmap_meta_check,proposal_table_check,tasks_checkbox_check,plan_tdd_check}.py: 26 unit tests
- tests/integration/test_rdd_doctor{,_cli,_readonly,_cat5_degraded,_fixtures}.bats: 19 integration tests
- tests/fixtures/{healthy,diseased}-repo/: with planted defects
- AGENTS.md: rdd-doctor section (~15 lines)
- tests/README.md: 1-line entry
- tests/smoke.bats: rdd-doctor registration

All AC1-AC10 satisfied. ./test.sh --full --regression clean.
"
```

- [ ] **Step 4: Verify commit on branch**

```bash
git log -1 --oneline
```

Expected: 1 commit on `openspec/add-rdd-doctor-skill` branch

- [ ] **Step 5: Mark `openspec/changes/add-rdd-doctor-skill/tasks.md` all `[x]`**

Per execute convention, the tasks.md in openspec/changes/ is the source of truth. Update:

```bash
sed -i 's/- \[ \]/- [x]/g' openspec/changes/add-rdd-doctor-skill/tasks.md
git add openspec/changes/add-rdd-doctor-skill/tasks.md
git commit -m "chore(add-rdd-doctor-skill): mark all tasks complete"
```

- [ ] **Step 6: Run archive pre-flight regression**

Run: `./test.sh --full --regression`
Expected: All green

- [ ] **Step 7: Hand off to guide-ship Phase 3 (archive)**

Reply with: "ready for archive"