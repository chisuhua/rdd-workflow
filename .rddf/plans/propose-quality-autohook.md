# propose-quality-autohook Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use skill_use("execute") to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Wire the existing `propose_quality_check.py` structural checker into the propose flow (Phase 4 hook) and into the `plan_done` gate, with warning-by-default behavior and `STRICT_PROPOSE_GATE=yes` upgrade.

**Architecture:** A thin `propose_quality_hook.py` entrypoint reuses `propose_quality_check.run_all_checks()` and writes a machine-readable `.rddf/state/propose-quality.json`. A bash wrapper exposes `invoke_propose_quality_hook <name>` to `propose.md` Phase 4. `gate.py` registers a `propose_quality_checks` Check in `plan_done` that reads the cached report or re-runs the checker, wrapped by `strict_wrap(..., env_var="STRICT_PROPOSE_GATE")`.

**Tech Stack:** Python 3.11, pytest, bash, bats-core

---

## File Structure

### Production Code

| File | Responsibility |
|---|---|
| `skills/propose/scripts/propose_quality_hook.py` | Phase 4 hook: runs 5 checks, prints warnings, persists `.rddf/state/propose-quality.json`, returns exit code |
| `skills/propose/scripts/propose_quality_hook.sh` | Bash wrapper that sources/invokes the Python hook via env vars (Oracle C1 safe) |
| `skills/propose/SKILL.md` | Phase 4 documentation: invoke hook after skeleton and full branches |
| `skills/_lib/gate.py` | Register `propose_quality_checks` Check in `plan_done` defaults |

### Tests

| File | Responsibility |
|---|---|
| `tests/unit/test_propose_quality_hook.py` | Unit tests for `run_quality_check` and `invoke_from_propose_phase4` |
| `tests/unit/test_gate.py` | Extended tests for `plan_done` registration/behavior of `propose_quality_checks` |
| `tests/integration/test_propose_quality_hook.bats` | Bats tests for wrapper existence, propose.md invocation, valid/broken proposal exit codes |

---

## Task 1: Create `propose_quality_hook.py` entrypoint

**Files:**
- Create: `skills/propose/scripts/propose_quality_hook.py`
- Test: `tests/unit/test_propose_quality_hook.py`

- [ ] **Step 1: Write the failing test**

```python
def test_run_quality_check_writes_valid_json(tmp_path):
    from skills.propose.scripts import propose_quality_hook as pqh
    import json
    report = pqh.run_quality_check(str(tmp_path), "c1")
    assert report["schema_version"] == 1
    assert report["change"] == "c1"
    assert "warnings" in report
    saved = (tmp_path / ".rddf" / "state" / "propose-quality.json").read_text()
    assert json.loads(saved)["change"] == "c1"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/unit/test_propose_quality_hook.py::test_run_quality_check_writes_valid_json -v`
Expected: FAIL with `ModuleNotFoundError` or `ImportError` for `propose_quality_hook`.

- [ ] **Step 3: Write minimal implementation**

Create `skills/propose/scripts/propose_quality_hook.py`:

```python
"""skills/propose/scripts/propose_quality_hook.py - Phase 4 quality hook.

Wires propose_quality_check.run_all_checks into the propose flow.
Called by propose.md Phase 4 after artifact creation.
"""
from __future__ import annotations

import datetime
import json
import os
import sys
from typing import Any

from skills._lib.arch_quality_gate import is_strict_mode
from skills.propose.scripts.propose_quality_check import run_all_checks


PROPOSE_QUALITY_SCHEMA_VERSION = 1


def run_quality_check(project_root: str, change_name: str) -> dict[str, Any]:
    """Run all 5 structural checks and persist a machine-readable report.

    Returns the report dict and writes it to
    <project_root>/.rddf/state/propose-quality.json.
    """
    warnings = run_all_checks(change_name, project_root)
    strict_mode = is_strict_mode("STRICT_PROPOSE_GATE")
    report = {
        "schema_version": PROPOSE_QUALITY_SCHEMA_VERSION,
        "change": change_name,
        "warnings": warnings,
        "checked_at": datetime.datetime.now(tz=datetime.timezone.utc).isoformat(),
        "strict_mode": strict_mode,
        "check_count": 5,
        "passed_count": 5 - len(warnings),
    }
    report_path = os.path.join(project_root, ".rddf", "state", "propose-quality.json")
    os.makedirs(os.path.dirname(report_path), exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
        f.write("\n")
    return report


def invoke_from_propose_phase4(change_name: str) -> int:
    """Bash-callable entrypoint.

    Reads PROJECT_ROOT from environment. Prints warnings and exits:
      - 0 by default, or when strict + no warnings
      - 1 when STRICT_PROPOSE_GATE=yes and there are warnings
    """
    project_root = os.environ.get("PROJECT_ROOT", os.getcwd())
    report = run_quality_check(project_root, change_name)
    warnings = report["warnings"]
    strict_mode = report["strict_mode"]

    if warnings:
        print(f"⚠️  Quality warnings for '{change_name}':")
        for w in warnings:
            print(f"   - {w}")
        if strict_mode:
            print("❌ STRICT_PROPOSE_GATE=yes: exiting with error")
            return 1
        print("ℹ️  Set STRICT_PROPOSE_GATE=yes to upgrade warnings to errors")
    else:
        print(f"✅ '{change_name}' passes all quality checks")

    return 0


if __name__ == "__main__":
    change_name = os.environ.get("CHANGE_NAME") or (sys.argv[1] if len(sys.argv) > 1 else "")
    if not change_name:
        print("❌ CHANGE_NAME or positional argument required", file=sys.stderr)
        sys.exit(2)
    sys.exit(invoke_from_propose_phase4(change_name))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/unit/test_propose_quality_hook.py::test_run_quality_check_writes_valid_json -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add skills/propose/scripts/propose_quality_hook.py tests/unit/test_propose_quality_hook.py
# Do NOT commit yet; remaining tasks will add more tests and code.
```

---

## Task 2: Add remaining unit tests for `propose_quality_hook.py`

**Files:**
- Create: `tests/unit/test_propose_quality_hook.py` (extend)
- Modify: `skills/propose/scripts/propose_quality_hook.py` (already created)

- [ ] **Step 1: Write the failing tests**

```python
import json
import os
from pathlib import Path
import pytest
from skills.propose.scripts import propose_quality_hook as pqh


def _seed_good_change(root: str, name: str) -> None:
    change_dir = Path(root) / "openspec" / "changes" / name
    change_dir.mkdir(parents=True, exist_ok=True)
    proposal = (
        "## Why\n\n" + ("x" * 500) + "\n\nRefs ADR-0019.\n\n"
        "## In Scope\n\ndo thing\n\n## Out of Scope\n\nnot doing\n"
    )
    (change_dir / "proposal.md").write_text(proposal, encoding="utf-8")
    (change_dir / "tasks.md").write_text("## Tasks\n\n- [ ] one\n- [ ] two\n", encoding="utf-8")
    (Path(root) / "roadmap.md").write_text(f"# Roadmap\n\n- {name}\n", encoding="utf-8")


def test_invoke_returns_zero_in_default_mode(tmp_path, monkeypatch, capsys):
    _seed_good_change(str(tmp_path), "c1")
    monkeypatch.setenv("PROJECT_ROOT", str(tmp_path))
    monkeypatch.delenv("STRICT_PROPOSE_GATE", raising=False)
    assert pqh.invoke_from_propose_phase4("c1") == 0
    captured = capsys.readouterr()
    assert "passes all quality checks" in captured.out


def test_invoke_returns_one_under_strict_with_warnings(tmp_path, monkeypatch, capsys):
    change_dir = tmp_path / "openspec" / "changes" / "c1"
    change_dir.mkdir(parents=True)
    (change_dir / "proposal.md").write_text("## Why\n\nshort\n", encoding="utf-8")
    monkeypatch.setenv("PROJECT_ROOT", str(tmp_path))
    monkeypatch.setenv("STRICT_PROPOSE_GATE", "yes")
    assert pqh.invoke_from_propose_phase4("c1") == 1


def test_invoke_returns_zero_under_strict_no_warnings(tmp_path, monkeypatch, capsys):
    _seed_good_change(str(tmp_path), "c1")
    monkeypatch.setenv("PROJECT_ROOT", str(tmp_path))
    monkeypatch.setenv("STRICT_PROPOSE_GATE", "yes")
    assert pqh.invoke_from_propose_phase4("c1") == 0


def test_report_has_correct_schema_version_and_counts(tmp_path):
    _seed_good_change(str(tmp_path), "c1")
    report = pqh.run_quality_check(str(tmp_path), "c1")
    assert report["schema_version"] == 1
    assert report["check_count"] == 5
    assert report["passed_count"] == 5
    saved = json.loads((tmp_path / ".rddf" / "state" / "propose-quality.json").read_text())
    assert saved["passed_count"] == 5


def test_run_quality_check_aggregates_warnings(tmp_path, monkeypatch):
    change_dir = tmp_path / "openspec" / "changes" / "c1"
    change_dir.mkdir(parents=True)
    (change_dir / "proposal.md").write_text(
        "## Why\n\n<skeleton motivation - 1-2 sentences>\n\n"
        "## What Changes\n\n- <file path or module affected>\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("STRICT_PROPOSE_GATE", "yes")
    report = pqh.run_quality_check(str(tmp_path), "c1")
    assert len(report["warnings"]) >= 1
    assert report["passed_count"] == 5 - len(report["warnings"])
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/unit/test_propose_quality_hook.py -v`
Expected: tests that exercise `invoke_from_propose_phase4` may fail because the function prints warnings list and the implementation must handle them correctly. Fix any failures.

- [ ] **Step 3: Adjust implementation if needed**

No new code needed if Step 3 of Task 1 is complete; this task only verifies behavior.

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/unit/test_propose_quality_hook.py -v`
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add tests/unit/test_propose_quality_hook.py
git commit -m "feat(propose): add propose_quality_hook entrypoint and unit tests"
```

---

## Task 3: Create `propose_quality_hook.sh` bash wrapper

**Files:**
- Create: `skills/propose/scripts/propose_quality_hook.sh`
- Test: `tests/integration/test_propose_quality_hook.bats`

- [ ] **Step 1: Write the failing test**

```bats
@test "propose_quality_hook.sh: wrapper exists and exposes invoke_propose_quality_hook" {
  run test -f "${REPO_ROOT}/skills/propose/scripts/propose_quality_hook.sh"
  [ "$status" -eq 0 ]
  grep -q "invoke_propose_quality_hook" "${REPO_ROOT}/skills/propose/scripts/propose_quality_hook.sh"
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `bats tests/integration/test_propose_quality_hook.bats`
Expected: FAIL because `propose_quality_hook.sh` does not exist.

- [ ] **Step 3: Write minimal implementation**

Create `skills/propose/scripts/propose_quality_hook.sh`:

```bash
# skills/propose/scripts/propose_quality_hook.sh
# Bash wrapper for propose_quality_hook.py (Phase 4 quality check).
# Env-var only passing (Oracle C1 safe). No bash string interpolation.

invoke_propose_quality_hook() {
    local CHANGE_NAME="$1"
    local SCRIPT_DIR
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" 2>/dev/null && pwd)"
    PROJECT_ROOT="${PROJECT_ROOT:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"

    CHANGE_NAME="$CHANGE_NAME" PROJECT_ROOT="$PROJECT_ROOT" \
        python3 "$SCRIPT_DIR/propose_quality_hook.py"
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `bats tests/integration/test_propose_quality_hook.bats`
Expected: PASS for the wrapper-existence test (other tests may still fail).

- [ ] **Step 5: Commit**

```bash
git add skills/propose/scripts/propose_quality_hook.sh
# Do not commit bats file yet; add more tests in Task 6.
```

---

## Task 4: Wire `propose.md` Phase 4 to invoke the hook

**Files:**
- Modify: `skills/propose/SKILL.md`
- Test: `tests/integration/test_propose_quality_hook.bats`

- [ ] **Step 1: Write the failing test**

```bats
@test "propose.md: Phase 4 invokes propose_quality_hook.sh" {
  grep -q "propose_quality_hook.sh" "${REPO_ROOT}/skills/propose/SKILL.md"
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `bats tests/integration/test_propose_quality_hook.bats`
Expected: FAIL because `propose.md` does not mention the hook.

- [ ] **Step 3: Write minimal implementation**

In `skills/propose/SKILL.md`, inside the Phase 4 bash code block (after the skeleton branch before `continue`, and after the full branch before the closing `\`\`\``), add:

```bash
    # Step 4e: Quality check (propose-quality-autohook)
    if [ -f "$SCRIPT_DIR/propose_quality_hook.sh" ]; then
        source "$SCRIPT_DIR/propose_quality_hook.sh"
        invoke_propose_quality_hook "<name>"
        # exit code 0 = pass or warnings-only; 1 = STRICT_PROPOSE_GATE=yes + warnings
    fi
```

Insert this block twice: once inside the skeleton branch after the suggestion-status update and before `continue`, and once inside the full branch after `propose_finalize_change` and before the closing code fence.

- [ ] **Step 4: Run test to verify it passes**

Run: `bats tests/integration/test_propose_quality_hook.bats`
Expected: grep test PASS.

- [ ] **Step 5: Commit**

```bash
git add skills/propose/SKILL.md
git commit -m "feat(propose): wire quality hook into Phase 4 skeleton and full branches"
```

---

## Task 5: Register `propose_quality_checks` Check in `gate.py`

**Files:**
- Modify: `skills/_lib/gate.py`
- Test: `tests/unit/test_gate.py`

- [ ] **Step 1: Write the failing test**

In `tests/unit/test_gate.py` add:

```python
def test_plan_done_includes_propose_quality_checks(state_path, log_path):
    sv = make_state()
    sv.save(state_path)
    gate = GateMechanism(state_path=state_path, event_log_path=log_path, load_defaults=True)
    names = gate.get_registered_check_names()
    assert "propose_quality_checks" in names
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/unit/test_gate.py::test_plan_done_includes_propose_quality_checks -v`
Expected: FAIL because `propose_quality_checks` is not registered.

- [ ] **Step 3: Write minimal implementation**

In `skills/_lib/gate.py`:

1. Add import:
```python
from skills.propose.scripts.propose_quality_check import run_all_checks
```

2. Add the check function before `_DEFAULT_CHECKS`:
```python
def _check_propose_quality(ctx: dict) -> tuple[bool, Optional[str]]:
    """Re-run or reuse cached propose quality checks. Default warning."""
    sv = ctx.get("state_vector")
    if sv is None:
        return (True, None)
    name = sv.get_field("plan_side.current_change") or sv.get_field("arch_side.current_change")
    if not name:
        return (True, None)

    project_root = ctx.get("project_root", ".")
    report_path = os.path.join(project_root, ".rddf", "state", "propose-quality.json")
    warnings: list[str] = []
    if os.path.isfile(report_path):
        try:
            with open(report_path, encoding="utf-8") as f:
                report = json.load(f)
            warnings = report.get("warnings", [])
        except (json.JSONDecodeError, OSError):
            warnings = run_all_checks(name, project_root)
    else:
        warnings = run_all_checks(name, project_root)
    return (len(warnings) == 0, "warning")
```

3. Add the Check to `_DEFAULT_CHECKS["plan_done"]` after `change_task_traceability`:
```python
        Check(
            "propose_quality_checks",
            strict_wrap(_check_propose_quality, env_var="STRICT_PROPOSE_GATE"),
            "propose quality checks failed",
            "Fix proposal/tasks content; see .rddf/state/propose-quality.json",
            "warning",
        ),
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/unit/test_gate.py::test_plan_done_includes_propose_quality_checks -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add skills/_lib/gate.py
# Do not commit tests yet; add gate behavior tests in Task 6.
```

---

## Task 6: Extend `gate.py` behavior tests

**Files:**
- Modify: `tests/unit/test_gate.py`
- Modify: `skills/_lib/gate.py` (already updated)

- [ ] **Step 1: Write the failing tests**

Add to `tests/unit/test_gate.py`:

```python
def _seed_good_change(root: str, name: str) -> None:
    from pathlib import Path
    change_dir = Path(root) / "openspec" / "changes" / name
    change_dir.mkdir(parents=True, exist_ok=True)
    proposal = (
        "## Why\n\n" + ("x" * 500) + "\n\nRefs ADR-0019.\n\n"
        "## In Scope\n\ndo thing\n\n## Out of Scope\n\nnot doing\n"
    )
    (change_dir / "proposal.md").write_text(proposal, encoding="utf-8")
    (change_dir / "tasks.md").write_text("## Tasks\n\n- [ ] one\n- [ ] two\n", encoding="utf-8")
    (Path(root) / "roadmap.md").write_text(f"# Roadmap\n\n- {name}\n", encoding="utf-8")


def test_propose_quality_check_default_warning(state_path, log_path, tmp_path, monkeypatch):
    """Warnings -> gate passes, warning recorded."""
    from skills._lib import gate as gate_mod
    _seed_good_change(str(tmp_path), "c1")
    change_dir = tmp_path / "openspec" / "changes" / "c1"
    (change_dir / "proposal.md").write_text("## Why\n\nshort\n", encoding="utf-8")

    sv = make_state()
    sv.update_field("plan_side.current_change", "c1")
    sv.save(state_path)
    monkeypatch.setenv("PROJECT_ROOT", str(tmp_path))
    monkeypatch.delenv("STRICT_PROPOSE_GATE", raising=False)
    gate = gate_mod.GateMechanism(state_path=state_path, event_log_path=log_path, load_defaults=True)
    result = gate.verify_transition("plan_done", {"project_root": str(tmp_path)})
    assert result.passed is True
    assert "propose_quality_checks" in result.warnings


def test_propose_quality_check_strict_error(state_path, log_path, tmp_path, monkeypatch):
    """STRICT_PROPOSE_GATE=yes: warnings -> gate fails."""
    from skills._lib import gate as gate_mod
    _seed_good_change(str(tmp_path), "c1")
    change_dir = tmp_path / "openspec" / "changes" / "c1"
    (change_dir / "proposal.md").write_text("## Why\n\nshort\n", encoding="utf-8")

    sv = make_state()
    sv.update_field("plan_side.current_change", "c1")
    sv.save(state_path)
    monkeypatch.setenv("PROJECT_ROOT", str(tmp_path))
    monkeypatch.setenv("STRICT_PROPOSE_GATE", "yes")
    gate = gate_mod.GateMechanism(state_path=state_path, event_log_path=log_path, load_defaults=True)
    result = gate.verify_transition("plan_done", {"project_root": str(tmp_path)})
    assert result.passed is False
    assert "propose_quality_checks" in result.failed_checks


def test_propose_quality_check_missing_state_vector_skips(state_path, log_path):
    """No state vector -> check returns pass."""
    from skills._lib import gate as gate_mod
    gate = gate_mod.GateMechanism(state_path=state_path, event_log_path=log_path, load_defaults=True)
    passed, severity = gate_mod._check_propose_quality({})
    assert passed is True
    assert severity is None


def test_propose_quality_check_missing_state_file_reruns(state_path, log_path, tmp_path, monkeypatch):
    """No cached report -> gate falls back to re-running run_all_checks."""
    from skills._lib import gate as gate_mod
    _seed_good_change(str(tmp_path), "c1")
    change_dir = tmp_path / "openspec" / "changes" / "c1"
    (change_dir / "proposal.md").write_text("## Why\n\nshort\n", encoding="utf-8")

    sv = make_state()
    sv.update_field("plan_side.current_change", "c1")
    sv.save(state_path)
    monkeypatch.setenv("PROJECT_ROOT", str(tmp_path))
    monkeypatch.delenv("STRICT_PROPOSE_GATE", raising=False)
    gate = gate_mod.GateMechanism(state_path=state_path, event_log_path=log_path, load_defaults=True)
    result = gate.verify_transition("plan_done", {"project_root": str(tmp_path)})
    assert result.passed is True
    assert "propose_quality_checks" in result.warnings
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/unit/test_gate.py -k propose_quality -v`
Expected: FAIL if implementation is missing; otherwise PASS after Task 5.

- [ ] **Step 3: Adjust implementation if needed**

No changes required if Task 5 implementation is correct.

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/unit/test_gate.py -k propose_quality -v`
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add tests/unit/test_gate.py
git commit -m "test(gate): add plan_done propose_quality_checks behavior tests"
```

---

## Task 7: Add bats integration tests for the hook

**Files:**
- Create: `tests/integration/test_propose_quality_hook.bats`

- [ ] **Step 1: Write the failing test**

Create `tests/integration/test_propose_quality_hook.bats`:

```bats
#!/usr/bin/env bats
# Integration tests for propose_quality_autohook.

load test_helper

@test "propose-quality-hook: wrapper exists and exposes function" {
    assert_file_exists "$REPO_ROOT/skills/propose/scripts/propose_quality_hook.sh"
    assert_file_contains "$REPO_ROOT/skills/propose/scripts/propose_quality_hook.sh" "invoke_propose_quality_hook"
}

@test "propose-quality-hook: propose.md Phase 4 invokes the hook" {
    assert_file_contains "$REPO_ROOT/skills/propose/SKILL.md" "propose_quality_hook.sh"
}

@test "propose-quality-hook: gate.py registers propose_quality_checks" {
    assert_file_contains "$REPO_ROOT/skills/_lib/gate.py" "propose_quality_checks"
}

@test "propose-quality-hook: hook runs against a valid proposal" {
    local root="$BATS_TMPDIR/hook-valid-$$"
    mkdir -p "$root/openspec/changes/c1"
    cat > "$root/openspec/changes/c1/proposal.md" <<'EOF'
## Why

EOF
    printf 'x%.0s' {1..500} >> "$root/openspec/changes/c1/proposal.md"
    cat >> "$root/openspec/changes/c1/proposal.md" <<'EOF'

Refs ADR-0019.

## In Scope

do thing

## Out of Scope

not doing
EOF
    cat > "$root/openspec/changes/c1/tasks.md" <<'EOF'
## Tasks

- [ ] one
- [ ] two
EOF
    echo "- c1" > "$root/roadmap.md"

    run env PROJECT_ROOT="$root" CHANGE_NAME="c1" \
        python3 "$REPO_ROOT/skills/propose/scripts/propose_quality_hook.py"
    [ "$status" -eq 0 ]
    [ -f "$root/.rddf/state/propose-quality.json" ]
}

@test "propose-quality-hook: hook with broken proposal default exits 0" {
    local root="$BATS_TMPDIR/hook-broken-$$"
    mkdir -p "$root/openspec/changes/c1"
    echo "## Why

short" > "$root/openspec/changes/c1/proposal.md"

    run env PROJECT_ROOT="$root" CHANGE_NAME="c1" \
        python3 "$REPO_ROOT/skills/propose/scripts/propose_quality_hook.py"
    [ "$status" -eq 0 ]
    [ -f "$root/.rddf/state/propose-quality.json" ]
}

@test "propose-quality-hook: hook with broken proposal strict exits 1" {
    local root="$BATS_TMPDIR/hook-strict-$$"
    mkdir -p "$root/openspec/changes/c1"
    echo "## Why

short" > "$root/openspec/changes/c1/proposal.md"

    run env PROJECT_ROOT="$root" CHANGE_NAME="c1" STRICT_PROPOSE_GATE="yes" \
        python3 "$REPO_ROOT/skills/propose/scripts/propose_quality_hook.py"
    [ "$status" -eq 1 ]
}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `bats tests/integration/test_propose_quality_hook.bats`
Expected: FAIL if any prerequisite file is missing; otherwise PASS.

- [ ] **Step 3: Adjust implementation if needed**

No implementation changes should be needed; fix bats test syntax if required.

- [ ] **Step 4: Run tests to verify they pass**

Run: `bats tests/integration/test_propose_quality_hook.bats`
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add tests/integration/test_propose_quality_hook.bats
git commit -m "test(integration): add bats tests for propose quality hook"
```

---

## Task 8: Run full verification suite and update tasks.md

**Files:**
- Modify: `openspec/changes/propose-quality-autohook/tasks.md`

- [ ] **Step 1: Write the failing test**

Run targeted tests first:

```bash
python3 -m pytest tests/unit/test_propose_quality_hook.py tests/unit/test_gate.py -q --tb=short
```

- [ ] **Step 2: Run test to verify it fails (if any)**

Expected: no failures if all previous tasks passed. If failures appear, fix the corresponding task and rerun.

- [ ] **Step 3: Apply fixes if needed**

No new code changes if all previous tasks passed.

- [ ] **Step 4: Run full verification**

```bash
python3 -m pytest tests/unit/ -q --tb=short
bats tests/integration/test_propose_quality_hook.bats
bats tests/smoke.bats tests/integration/test_propose_skill.bats
```

- [ ] **Step 5: Mark tasks.md complete and commit**

Use `sed` or manual edit to mark checkboxes in `openspec/changes/propose-quality-autohook/tasks.md` as `[x]` for all items. Then commit:

```bash
git add openspec/changes/propose-quality-autohook/tasks.md
# If this is the final commit, combine with all remaining staged files:
git add -A
git commit -m "feat(propose): wire propose_quality_check.py into Phase 4 + plan_done gate"
```

---

## Self-Review

1. **Spec coverage**: The proposal requires Phase 4 invocation (Task 4), plan_done Check (Task 5), hook/wrapper (Tasks 1-3), and tests (Tasks 2, 6, 7). All covered.
2. **Placeholder scan**: No `TBD`, `TODO`, or vague instructions remain; every step includes concrete code or commands.
3. **Type consistency**: `run_quality_check` returns `dict[str, Any]`; `invoke_from_propose_phase4` returns `int`; `_check_propose_quality` returns `tuple[bool, Optional[str]]` consistent with other gate checks.
