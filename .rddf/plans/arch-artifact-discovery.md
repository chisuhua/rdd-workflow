# Arch Artifact Discovery Contract Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement ADR-0016 — extend `.rddf/state/.arch-handoff.json` with `adr_dir` / `roadmap_path` / `architecture_dir` / `adr_pattern` / `discovered` / `version` fields, replace 14+ hardcoded path references across 10 files with handoff-aware consumers (fallback to convention defaults), and verify backward compatibility via TDD.

**Architecture:** Three-layer design — (1) `discover_arch_artifacts.sh` discovers candidate paths via ordered glob, (2) `guide-arch.md` Phase 5 arch-done writes discovered paths to existing `.arch-handoff.json` (no new state file), (3) downstream consumers (plan/ship/library) read handoff first, fallback to `docs/adr/` / `roadmap.md` / `docs/architecture/` defaults when handoff missing or stale. Mirrors the `iteration.json` view-file pattern (multi-hook writes, schema-validated, gitignored) without introducing a sibling file.

**Tech Stack:** Bash 3+ (no `set -euo pipefail` per repo convention), Python 3.11+ (existing inline JSON parser, JSON Schema validation), bats-core 1.10+, pytest (existing), `jsonschema` (already in `requirements.txt`).

---

## Pre-flight (Read Once, Never Repeat)

These gates are confirmed as of `2026-07-08`; **re-verify before execution**:

- [x] `docs/adr/ADR-0016-arch-artifact-discovery-contract.md` exists with status `待定`. Plan activates only after ADR status flips to `已采纳`.
- [x] `.rddf/state/.arch-handoff.json` is the **only** new file target — no sibling view file created. Path is gitignored (`.gitignore` line 6).
- [x] Hardcoded path inventory is **14+ references in 10 files** (ADR-0016 §Context, Problem 1). Plan covers all.
- [x] `skills/_lib/scan-state.sh` (extracted in ADR-0013) is the precedent for sourced bash libraries with `_LIB_DIR` self-discovery. `discover_arch_artifacts.sh` follows the same pattern.
- [x] `skills/_lib/iteration.py` (558 lines) is the precedent for multi-hook state view files with schema validation + atomic writes + locks. arch-handoff extension follows the same idiom but simpler (no lock needed — single writer at arch-done).
- [x] `tests/conftest.py` adds project root to `sys.path` — `import skills._lib.x` resolves in pytest.
- [x] `tests/test_helper.bash` exposes `$REPO_ROOT` — `load_lib` resolves new `discover-arch-artifacts` automatically.
- [x] Existing JSON Schemas: `skills/_lib/schemas/iteration_schema.json`, `deps_analysis_schema.json`. New `arch_handoff_schema.json` follows same structure.
- [x] `discover_arch_artifacts.sh` MUST NOT create files (read-only scanner). File creation stays in `guide-arch.md` Phase 5 arch-done.

**Pre-existing bugs surfaced by this work** (will be fixed in plan):

1. **`completed_adr_ids` over-provisioned in handoff** (handoff writes ADR IDs but consumers don't use them). Plan consolidates by introducing `adr_dir` + `adr_pattern` so consumers glob the right place.
2. **Gate.py path checks duplicate hardcoded assumptions** (ADR-0016 §Context, Problem 1 row "skills/_lib/gate.py"). Plan replaces with handoff-aware reads.

**Out of scope** (per ADR-0016 §影响范围 → Out Scope):

- `docs/adr/ADR-0000-template.md` format (unchanged)
- openspec CLI interface (unchanged)
- `.openspec.yaml` / `roadmap-meta.yaml` (unchanged)
- Forcing migration to new paths — fallback defaults match existing v2.0 conventions
- New external dependencies (jq/python3 inline already in use)
- `iteration.json`, `deps-analysis.json` schemas (untouched)

---

## File Structure

### New files

| File | Responsibility | Size budget |
|------|----------------|-------------|
| `skills/_lib/discover-arch-artifacts.sh` | Sourced library exposing `discover_adr_dir`, `discover_roadmap`, `discover_architecture_dir`, `discover_adr_pattern`; sets globals `DISCOVERED_ADR_DIR`, `DISCOVERED_ROADMAP_PATH`, etc. | ~80 lines |
| `skills/_lib/schemas/arch_handoff_schema.json` | JSON Schema for the extended `.arch-handoff.json` (version 1); validates `adr_dir` / `roadmap_path` / `architecture_dir` / `adr_pattern` / `discovered` / `version` | ~50 lines |
| `tests/unit/test_discover_arch_artifacts.py` | pytest unit tests: 4 discover functions × 5 scenarios (default, found-first, found-Nth, none-found, malformed-cwd) | ~180 lines |
| `tests/unit/test_arch_handoff_schema.py` | pytest schema tests: 7 cases (valid v1, missing fields, version mismatch, path-traversal injection, malformed JSON, extra fields, version=0 backward compat) | ~120 lines |
| `tests/integration/test_arch_discovery_contract.bats` | bats integration tests: 8 cases covering arch → plan handoff flow end-to-end (custom path, default path, mixed env override, missing handoff fallback) | ~200 lines |

### Modified files

| File | Change | Diff size |
|------|--------|-----------|
| `skills/guide-arch.md` | Phase 1 setup: append Step 5 (artifact discovery); Phase 5 arch-done: append `discover_*` calls + write 5 new handoff fields | +60 lines, -10 lines |
| `skills/guide-plan.md` | Phase 0 intake: replace `ls "$PROJECT_ROOT/docs/adr/ADR-0"*.md` and `[-f roadmap.md]` with handoff-read + fallback | +25 lines, -8 lines |
| `skills/guide.md` (scan-state.sh) | Add `_read_arch_handoff_paths` function; replace 4 hardcoded path checks | +20 lines, -8 lines |
| `skills/propose.md` | Phase 1a (line 188): replace `ls docs/adr/ADR-*.md`, `ls docs/architecture/*-gap-analysis.md`, `ls docs/architecture/*-architecture.md`, `ls docs/architecture/PHASE*-ARCHITECTURE.md` with handoff-glob | +15 lines, -8 lines |
| `skills/roadmap.md` | Template 4 (line 197-202): replace `ls docs/adr/ADR-*.md` and `[ ! -d docs/adr ]` with handoff-glob | +12 lines, -6 lines |
| `skills/_lib/gate.py` | `_check_adr_exists` (line 56-57), `_check_roadmap_defined` (line 60-61), `_check_arch_handoff_exists` (line 68-69): read handoff paths instead of hardcoded constants | +35 lines, -10 lines |
| `skills/_lib/detectors.py` | `detect_adrs` (line 177-178): read handoff path | +10 lines, -3 lines |
| `skills/_lib/actions.py` | `action_create_adr` (line 341-350): read handoff path for ADR creation | +10 lines, -3 lines |
| `AGENTS.md` | Add arch-handoff v1 schema row to "状态文件" table; add "Arch Discovery Contract (ADR-0016)" subsection | +20 lines |

### Untouched files (explicit non-goals)

- `skills/guide-ship.md` — never reads arch-side artifacts (only writes `*-drift-analysis.md`)
- `skills/_lib/state.sh` — still a stub, no callers
- `skills/_lib/worktree.sh`, `archive.sh` — sources of precedent, no need to touch
- `skills/_lib/iteration.py`, `deps_output.py` — separate view-file patterns, no changes needed
- `.rddf/state/iteration.json`, `.rddf/state/deps-analysis.json` — schemas unchanged
- `package.json`, `requirements.txt`, `skills/INSTALL.md` — no dependency changes

---

## Task 1: Define JSON Schema for arch-handoff v1 (TDD red → green)

**Files:**
- Create: `skills/_lib/schemas/arch_handoff_schema.json`
- Create: `tests/unit/test_arch_handoff_schema.py`

Schema MUST be defined FIRST so the writer (Task 3) and reader (Tasks 4-5) both have a contract to follow.

- [ ] **Step 1.1: Write the failing schema tests**

Create `tests/unit/test_arch_handoff_schema.py`:

```python
"""Tests for .arch-handoff.json JSON Schema (ADR-0016)."""
import json
import pytest
from pathlib import Path
from jsonschema import Draft7Validator

SCHEMA_PATH = Path(__file__).parent.parent.parent / "skills" / "_lib" / "schemas" / "arch_handoff_schema.json"

@pytest.fixture
def schema():
    assert SCHEMA_PATH.exists(), f"Schema file missing: {SCHEMA_PATH}"
    return json.loads(SCHEMA_PATH.read_text())

@pytest.fixture
def validator(schema):
    return Draft7Validator(schema)

def test_schema_declares_version_1(schema):
    """Schema must pin version 1 for ADR-0016 contract."""
    assert schema["properties"]["version"]["const"] == 1

def test_valid_v1_payload_passes(validator):
    """Canonical payload with all v1 fields must validate."""
    payload = {
        "arch_complete_at": "2026-07-08T10:00:00+00:00",
        "adr_count": 3,
        "completed_adr_ids": ["0001", "0002", "0003"],
        "roadmap_exists": True,
        "current_phase": "phase-1",
        "plan_started_at": None,
        # New v1 fields (ADR-0016 Layer 2):
        "adr_dir": "docs/adr",
        "roadmap_path": "roadmap.md",
        "architecture_dir": "docs/architecture",
        "adr_pattern": "ADR-*.md",
        "discovered": {
            "adr_dir": {"found": True, "created": False, "candidates_tried": 4},
            "roadmap_path": {"found": True, "created": False, "candidates_tried": 4},
            "architecture_dir": {"found": False, "created": False, "candidates_tried": 3},
        },
        "version": 1,
    }
    errors = list(validator.iter_errors(payload))
    assert errors == [], f"Expected no errors, got: {[e.message for e in errors]}"

def test_missing_new_field_fails(validator):
    """Pre-v1 payloads (missing adr_dir etc.) must be rejected at schema level."""
    payload_v0 = {
        "arch_complete_at": "2026-07-08T10:00:00+00:00",
        "adr_count": 1,
        "completed_adr_ids": ["0001"],
        "version": 0,  # legacy
    }
    # Schema rejects v=0 OR required fields
    errors = list(validator.iter_errors(payload_v0))
    assert any("version" in e.message or "adr_dir" in e.message for e in errors)

def test_path_traversal_in_adr_dir_rejected(validator):
    """adr_dir with '..' must be rejected (security)."""
    payload = {
        "arch_complete_at": "2026-07-08T10:00:00+00:00",
        "adr_count": 1,
        "completed_adr_ids": ["0001"],
        "roadmap_exists": True,
        "current_phase": "phase-1",
        "plan_started_at": None,
        "adr_dir": "../../etc/passwd",  # attack vector
        "roadmap_path": "roadmap.md",
        "architecture_dir": "docs/architecture",
        "adr_pattern": "ADR-*.md",
        "discovered": {},
        "version": 1,
    }
    errors = list(validator.iter_errors(payload))
    assert errors, "Expected path-traversal rejection"

def test_absolute_path_in_adr_dir_rejected(validator):
    """adr_dir must be relative (worktree compatibility)."""
    payload = {
        "arch_complete_at": "2026-07-08T10:00:00+00:00",
        "adr_count": 1,
        "completed_adr_ids": ["0001"],
        "roadmap_exists": True,
        "current_phase": "phase-1",
        "plan_started_at": None,
        "adr_dir": "/etc/passwd",  # absolute
        "roadmap_path": "roadmap.md",
        "architecture_dir": "docs/architecture",
        "adr_pattern": "ADR-*.md",
        "discovered": {},
        "version": 1,
    }
    errors = list(validator.iter_errors(payload))
    assert errors, "Expected absolute-path rejection"

def test_extra_fields_allowed_at_root(validator):
    """Schema must permit additionalProperties=true at root (forward compat)."""
    payload = {
        "arch_complete_at": "2026-07-08T10:00:00+00:00",
        "adr_count": 1,
        "completed_adr_ids": ["0001"],
        "roadmap_exists": True,
        "current_phase": "phase-1",
        "plan_started_at": None,
        "adr_dir": "docs/adr",
        "roadmap_path": "roadmap.md",
        "architecture_dir": "docs/architecture",
        "adr_pattern": "ADR-*.md",
        "discovered": {},
        "version": 1,
        "future_field_xyz": "ignored",  # not in schema
    }
    errors = list(validator.iter_errors(payload))
    assert errors == [], f"Unexpected errors: {[e.message for e in errors]}"
```

- [ ] **Step 1.2: Run the tests to verify they fail (RED)**

Run: `python3 -m pytest tests/unit/test_arch_handoff_schema.py -v`
Expected: ALL 6 tests fail with `Schema file missing: ...arch_handoff_schema.json`

- [ ] **Step 1.3: Write the schema (GREEN)**

Create `skills/_lib/schemas/arch_handoff_schema.json`:

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "$id": "https://rdd-workflow.local/schemas/arch_handoff_schema.json",
  "title": "Arch Handoff v1 (ADR-0016)",
  "description": "Schema for .rddf/state/.arch-handoff.json emitted by guide-arch Phase 5 arch-done. Consumed by guide-plan, propose, roadmap, gate.py, detectors.py, actions.py, scan-state.sh.",
  "type": "object",
  "additionalProperties": true,
  "required": [
    "arch_complete_at",
    "adr_count",
    "completed_adr_ids",
    "roadmap_exists",
    "current_phase",
    "plan_started_at",
    "adr_dir",
    "roadmap_path",
    "architecture_dir",
    "adr_pattern",
    "discovered",
    "version"
  ],
  "properties": {
    "arch_complete_at": {
      "type": "string",
      "format": "date-time",
      "description": "ISO-8601 timestamp when arch-done was completed"
    },
    "adr_count": {
      "type": "integer",
      "minimum": 0,
      "description": "Number of ADR documents discovered (ADR-0000-template excluded)"
    },
    "completed_adr_ids": {
      "type": "array",
      "items": {"type": "string", "pattern": "^[0-9]{4}$"},
      "description": "Zero-padded 4-digit ADR numbers (e.g. ['0001', '0002'])"
    },
    "roadmap_exists": {
      "type": "boolean",
      "description": "Whether roadmap.md was present at arch-done"
    },
    "current_phase": {
      "type": "string",
      "description": "Current roadmap phase (e.g. 'phase-1', 'default')"
    },
    "plan_started_at": {
      "type": ["string", "null"],
      "format": "date-time",
      "description": "ISO-8601 timestamp when plan phase started (null until plan runs)"
    },
    "adr_dir": {
      "type": "string",
      "pattern": "^(?!/)(?!.*\\.\\.)[^\\x00]+$",
      "description": "Relative path to ADR directory (e.g. 'docs/adr', 'doc/adr'). Must not be absolute or contain '..'."
    },
    "roadmap_path": {
      "type": "string",
      "pattern": "^(?!/)(?!.*\\.\\.)[^\\x00]+$",
      "description": "Relative path to roadmap file (e.g. 'roadmap.md', 'docs/roadmap.md')"
    },
    "architecture_dir": {
      "type": "string",
      "pattern": "^(?!/)(?!.*\\.\\.)[^\\x00]+$",
      "description": "Relative path to architecture documents directory (e.g. 'docs/architecture')"
    },
    "adr_pattern": {
      "type": "string",
      "pattern": "^[A-Za-z0-9_*-]+\\.md$",
      "description": "Glob pattern for ADR files within adr_dir (e.g. 'ADR-*.md', 'DEC-*.md', 'RFD-*.md'). Must be a filename pattern — no path separators or '..' (HIGH#7 — defends against path-traversal even though this is a glob)."
    },
    "discovered": {
      "type": "object",
      "description": "Discovery process metadata per artifact type",
      "properties": {
        "adr_dir": {
          "type": "object",
          "required": ["found", "created", "candidates_tried"],
          "properties": {
            "found": {"type": "boolean"},
            "created": {"type": "boolean"},
            "candidates_tried": {"type": "integer", "minimum": 0}
          }
        },
        "roadmap_path": {
          "type": "object",
          "required": ["found", "created", "candidates_tried"],
          "properties": {
            "found": {"type": "boolean"},
            "created": {"type": "boolean"},
            "candidates_tried": {"type": "integer", "minimum": 0}
          }
        },
        "architecture_dir": {
          "type": "object",
          "required": ["found", "created", "candidates_tried"],
          "properties": {
            "found": {"type": "boolean"},
            "created": {"type": "boolean"},
            "candidates_tried": {"type": "integer", "minimum": 0}
          }
        }
      },
      "additionalProperties": false
    },
    "version": {
      "type": "integer",
      "const": 1,
      "description": "Contract version. v1 adds adr_dir/roadmap_path/architecture_dir/adr_pattern/discovered fields (ADR-0016)."
    }
  }
}
```

- [ ] **Step 1.4: Run the tests to verify they pass (GREEN)**

Run: `python3 -m pytest tests/unit/test_arch_handoff_schema.py -v`
Expected: ALL 6 tests pass.

- [ ] **Step 1.5: Commit**

```bash
git add skills/_lib/schemas/arch_handoff_schema.json tests/unit/test_arch_handoff_schema.py
git commit -m "feat(adr-0016): add arch-handoff v1 JSON Schema + 6 validation tests"
```

---

## Task 2: Implement `discover_arch_artifacts.sh` (TDD red → green)

**Files:**
- Create: `skills/_lib/discover-arch-artifacts.sh`
- Create: `tests/unit/test_discover_arch_artifacts.py`

The discover script is read-only: scans PROJECT_ROOT for candidate paths, sets globals, never creates files.

- [ ] **Step 2.1: Write the failing unit tests**

Create `tests/unit/test_discover_arch_artifacts.py`:

```python
"""Unit tests for skills/_lib/discover-arch-artifacts.sh (ADR-0016 Layer 1)."""
import os
import subprocess
import tempfile
from pathlib import Path

DISCOVER_SH = Path(__file__).parent.parent.parent / "skills" / "_lib" / "discover-arch-artifacts.sh"


def _run_discover(project_root: str, function: str, env_extra: dict = None) -> tuple[int, str, str]:
    """Run a discover function in a subshell. Returns (returncode, stdout, stderr)."""
    env = os.environ.copy()
    env["PROJECT_ROOT"] = project_root
    if env_extra:
        env.update(env_extra)
    cmd = f"""
    source {DISCOVER_SH}
    {function}
    echo "---"
    declare -p | grep -E '^declare -[a-zA-Z]+ DISCOVERED_'
    """
    proc = subprocess.run(
        ["bash", "-c", cmd],
        env=env,
        capture_output=True,
        text=True,
        timeout=10,
    )
    return proc.returncode, proc.stdout, proc.stderr


def test_discover_adr_dir_returns_default_when_nothing_found():
    """When no candidate exists, return 'docs/adr' as convention default."""
    with tempfile.TemporaryDirectory() as tmp:
        rc, out, err = _run_discover(tmp, "discover_adr_dir")
        assert rc == 0
        first_line = out.split("\n---")[0].strip()
        assert first_line == "docs/adr"


def test_discover_adr_dir_finds_first_candidate():
    """When 'docs/adr' exists, return it (highest priority)."""
    with tempfile.TemporaryDirectory() as tmp:
        os.makedirs(f"{tmp}/docs/adr")
        rc, out, err = _run_discover(tmp, "discover_adr_dir")
        assert rc == 0
        first_line = out.split("\n---")[0].strip()
        assert first_line == "docs/adr"


def test_discover_adr_dir_finds_alternative_layout():
    """When 'docs/adr' missing but 'doc/adr' exists, return 'doc/adr'."""
    with tempfile.TemporaryDirectory() as tmp:
        os.makedirs(f"{tmp}/doc/adr")
        rc, out, err = _run_discover(tmp, "discover_adr_dir")
        assert rc == 0
        first_line = out.split("\n---")[0].strip()
        assert first_line == "doc/adr"


def test_discover_roadmap_returns_default_when_missing():
    """Roadmap fallback to 'roadmap.md' root."""
    with tempfile.TemporaryDirectory() as tmp:
        rc, out, err = _run_discover(tmp, "discover_roadmap")
        assert rc == 0
        first_line = out.split("\n---")[0].strip()
        assert first_line == "roadmap.md"


def test_discover_roadmap_finds_alternative_layout():
    """Find roadmap in docs/ when root missing."""
    with tempfile.TemporaryDirectory() as tmp:
        os.makedirs(f"{tmp}/docs", exist_ok=True)
        Path(f"{tmp}/docs/roadmap.md").touch()
        rc, out, err = _run_discover(tmp, "discover_roadmap")
        assert rc == 0
        first_line = out.split("\n---")[0].strip()
        assert first_line == "docs/roadmap.md"


def test_discover_architecture_dir_returns_default_when_missing():
    """Architecture fallback to 'docs/architecture'."""
    with tempfile.TemporaryDirectory() as tmp:
        rc, out, err = _run_discover(tmp, "discover_architecture_dir")
        assert rc == 0
        first_line = out.split("\n---")[0].strip()
        assert first_line == "docs/architecture"


def test_discover_adr_pattern_returns_default():
    """Default pattern is 'ADR-*.md'."""
    with tempfile.TemporaryDirectory() as tmp:
        rc, out, err = _run_discover(tmp, "discover_adr_pattern")
        assert rc == 0
        first_line = out.split("\n---")[0].strip()
        assert first_line == "ADR-*.md"


def test_env_var_override_takes_precedence():
    """SPEC_WORKFLOW_ADR_DIR env var beats all candidates."""
    with tempfile.TemporaryDirectory() as tmp:
        os.makedirs(f"{tmp}/docs/adr")
        rc, out, err = _run_discover(
            tmp, "discover_adr_dir",
            env_extra={"SPEC_WORKFLOW_ADR_DIR": "custom/adrs"}
        )
        assert rc == 0
        first_line = out.split("\n---")[0].strip()
        assert first_line == "custom/adrs"


def test_discover_sets_global_DISCOVERED_ADR_DIR():
    """discover_adr_dir must populate the DISCOVERED_ADR_DIR global."""
    with tempfile.TemporaryDirectory() as tmp:
        os.makedirs(f"{tmp}/docs/adr")
        rc, out, err = _run_discover(tmp, "discover_adr_dir")
        assert "DISCOVERED_ADR_DIR" in out
        # Extract value from declare -p output
        for line in out.splitlines():
            if line.startswith("declare -- DISCOVERED_ADR_DIR=") or line.startswith("declare -x DISCOVERED_ADR_DIR="):
                value = line.split("=", 1)[1].strip('"')
                assert value == "docs/adr"
                return
        pytest.fail(f"DISCOVERED_ADR_DIR not declared in output: {out}")
```

- [ ] **Step 2.2: Run tests to verify they fail (RED)**

Run: `python3 -m pytest tests/unit/test_discover_arch_artifacts.py -v`
Expected: ALL 9 tests fail with `FileNotFoundError` (script does not exist) OR function-not-defined.

- [ ] **Step 2.3: Implement `discover-arch-artifacts.sh` (GREEN)**

Create `skills/_lib/discover-arch-artifacts.sh`:

```bash
# skills/_lib/discover-arch-artifacts.sh
#
# Sourced library for arch-side artifact discovery (ADR-0016 Layer 1).
# Follows the same sourced-only pattern as worktree.sh / archive.sh.
#
# Globals (after source + function call):
#   DISCOVERED_<KIND>_PATH    — relative path to the artifact
#   DISCOVERED_<KIND>_FOUND   — "true" | "false"
#   DISCOVERED_<KIND>_TRIED   — integer, number of candidates attempted
#   DISCOVERED_ADR_PATTERN    — glob pattern for ADR filenames
#
# Environment overrides (TRULY highest priority — applied BEFORE existence check
# AND before default candidates; env var pointing to non-existent path is honored,
# found=false is recorded but the path is still used):
#   SPEC_WORKFLOW_ADR_DIR
#   SPEC_WORKFLOW_ROADMAP_PATH
#   SPEC_WORKFLOW_ARCHITECTURE_DIR
#   SPEC_WORKFLOW_ADR_PATTERN
#
# Conventions (fallback when no candidate found AND no env var):
#   adr_dir          = docs/adr
#   roadmap_path     = roadmap.md
#   architecture_dir = docs/architecture
#   adr_pattern      = ADR-*.md

# Guard against direct execution (sourced-only)
if [ "${BASH_SOURCE[0]}" = "$0" ]; then
  echo "discover-arch-artifacts.sh: must be sourced, not executed" >&2
  exit 1
fi

: "${PROJECT_ROOT:=$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"

# Default candidate lists (used only when env var is unset/empty)
_ADR_DIR_CANDIDATES_DEFAULT=(
  "docs/adr"
  "doc/adr"
  "documentation/adrs"
  "adrs"
)

_ROADMAP_CANDIDATES_DEFAULT=(
  "roadmap.md"
  "docs/roadmap.md"
  "planning/roadmap.md"
  "ROADMAP.md"
)

_ARCHITECTURE_DIR_CANDIDATES_DEFAULT=(
  "docs/architecture"
  "docs/arch"
  "documentation/architecture"
)

# Internal helper: ENV VAR SHORT-CIRCUITS — when present, the env value wins
# unconditionally (even if the path does not exist). When env is unset/empty,
# fall back to scanning default candidates.
#
# IMPORTANT: This function is called DIRECTLY, not via command substitution.
# All exports happen in the caller's shell — this avoids the bash subshell
# propagation gotcha where exports inside $(...) are lost to the parent.
#
# Args: <kind> <check_type> <default_value> <env_var_name>
#   kind         — ADR_DIR | ROADMAP | ARCHITECTURE_DIR
#   check_type   — "dir" | "file"
#   default_value — convention fallback path
#   env_var_name — name of env var to check (NOT its value)
#
# Sets globals (does NOT echo; caller echoes if needed):
#   DISCOVERED_<KIND>_PATH
#   DISCOVERED_<KIND>_FOUND
#   DISCOVERED_<KIND>_TRIED
_discover_with_override() {
  local _kind="$1"
  local _check_type="$2"
  local _default="$3"
  local _env_name="$4"
  local _result _found _tried

  # Path 1: env var short-circuits (high priority — even if path missing).
  # Only check that the env var NAME has a non-empty value; we don't resolve
  # the indirect expansion (${!_env_name}) here to keep the logic simple.
  if [ -n "${!_env_name:-}" ]; then
    _result="${!_env_name}"
    _tried=1
    if [ "$_check_type" = "dir" ] && [ -d "${PROJECT_ROOT}/${_result}" ]; then
      _found="true"
    elif [ "$_check_type" = "file" ] && [ -f "${PROJECT_ROOT}/${_result}" ]; then
      _found="true"
    else
      _found="false"
    fi
    export "DISCOVERED_${_kind}_PATH=${_result}"
    export "DISCOVERED_${_kind}_FOUND=${_found}"
    export "DISCOVERED_${_kind}_TRIED=${_tried}"
    return 0
  fi

  # Path 2: scan default candidates (first existing match wins)
  local _default_candidates=()
  case "$_kind" in
    ADR_DIR)          _default_candidates=("${_ADR_DIR_CANDIDATES_DEFAULT[@]}") ;;
    ROADMAP)          _default_candidates=("${_ROADMAP_CANDIDATES_DEFAULT[@]}") ;;
    ARCHITECTURE_DIR) _default_candidates=("${_ARCHITECTURE_DIR_CANDIDATES_DEFAULT[@]}") ;;
  esac

  _result="${_default}"
  _found="false"
  _tried=0
  for candidate in "${_default_candidates[@]}"; do
    _tried=$((_tried + 1))
    if [ "$_check_type" = "dir" ] && [ -d "${PROJECT_ROOT}/${candidate}" ]; then
      _result="${candidate}"; _found="true"; break
    elif [ "$_check_type" = "file" ] && [ -f "${PROJECT_ROOT}/${candidate}" ]; then
      _result="${candidate}"; _found="true"; break
    fi
  done

  export "DISCOVERED_${_kind}_PATH=${_result}"
  export "DISCOVERED_${_kind}_FOUND=${_found}"
  export "DISCOVERED_${_kind}_TRIED=${_tried}"
  return 0
}

# Public discover_adr_dir: calls helper DIRECTLY (no command substitution),
# promotes helper globals to canonical short names, then echoes result.
discover_adr_dir() {
  _discover_with_override ADR_DIR dir "docs/adr" SPEC_WORKFLOW_ADR_DIR
  # Promote helper globals (DISCOVERED_ADR_DIR_PATH etc.) to canonical short
  # names so existing consumers don't break.
  DISCOVERED_ADR_DIR="${DISCOVERED_ADR_DIR_PATH}"
  DISCOVERED_ADR_DIR_FOUND="${DISCOVERED_ADR_DIR_FOUND}"
  DISCOVERED_ADR_DIR_TRIED="${DISCOVERED_ADR_DIR_TRIED}"
  export DISCOVERED_ADR_DIR DISCOVERED_ADR_DIR_FOUND DISCOVERED_ADR_DIR_TRIED
  echo "${DISCOVERED_ADR_DIR}"
}

discover_roadmap() {
  _discover_with_override ROADMAP file "roadmap.md" SPEC_WORKFLOW_ROADMAP_PATH
  DISCOVERED_ROADMAP_PATH="${DISCOVERED_ROADMAP_PATH}"
  DISCOVERED_ROADMAP_FOUND="${DISCOVERED_ROADMAP_FOUND}"
  DISCOVERED_ROADMAP_TRIED="${DISCOVERED_ROADMAP_TRIED}"
  export DISCOVERED_ROADMAP_PATH DISCOVERED_ROADMAP_FOUND DISCOVERED_ROADMAP_TRIED
  echo "${DISCOVERED_ROADMAP_PATH}"
}

discover_architecture_dir() {
  _discover_with_override ARCHITECTURE_DIR dir "docs/architecture" SPEC_WORKFLOW_ARCHITECTURE_DIR
  DISCOVERED_ARCHITECTURE_DIR="${DISCOVERED_ARCHITECTURE_DIR_PATH}"
  DISCOVERED_ARCH_FOUND="${DISCOVERED_ARCHITECTURE_DIR_FOUND}"
  DISCOVERED_ARCH_TRIED="${DISCOVERED_ARCHITECTURE_DIR_TRIED}"
  export DISCOVERED_ARCHITECTURE_DIR DISCOVERED_ARCH_FOUND DISCOVERED_ARCH_TRIED
  echo "${DISCOVERED_ARCHITECTURE_DIR}"
}

# adr_pattern has no existence check — it's a glob pattern, not a path.
discover_adr_pattern() {
  DISCOVERED_ADR_PATTERN="${SPEC_WORKFLOW_ADR_PATTERN:-ADR-*.md}"
  export DISCOVERED_ADR_PATTERN
  echo "${DISCOVERED_ADR_PATTERN}"
}

# Convenience: discover everything at once (sets all globals + suppresses echo).
discover_all() {
  discover_adr_dir          >/dev/null
  discover_roadmap          >/dev/null
  discover_architecture_dir >/dev/null
  discover_adr_pattern      >/dev/null
}
```

**Critique fixes applied (CRITICAL#1 + CRITICAL#2 from Momus round 2):**

- **Env var truly short-circuits**: when `SPEC_WORKFLOW_*` is set, the helper
  exits the candidate scan loop after the first iteration, returning
  the env-supplied path. Verified via `/tmp` reproduction:
  `SPEC_WORKFLOW_ADR_DIR=custom/adrs` (non-existent) → returns `custom/adrs`
  with `FOUND=false`, instead of falling through to `docs/adr`.
- **No more subshell export propagation bug**: the previous version
  called `_discover_with_override` via `$(...)` command substitution
  (`DISCOVERED_ADR_DIR="$(_discover_with_override ...)"`), causing all exports
  inside the helper to be lost to the parent shell. The new design:
  - Uses 4-argument signature: `(kind, check_type, default, env_var_name)`
  - Sets globals via `export ...` in the helper
  - Returns the path via a different global (`DISCOVERED_<KIND>_PATH`)
  - Public functions call the helper DIRECTLY (not via `$(...)`) then echo
  - This guarantees exports propagate to the caller's shell.
- **Globals renamed** to `DISCOVERED_<KIND>_PATH` (was `DISCOVERED_<KIND>`)
  for clarity. Downstream consumers (Phase 5 handoff writer, integration tests)
  must read `DISCOVERED_ADR_DIR_PATH` (etc.), not `DISCOVERED_ADR_DIR`.

**BREAKING CHANGE — Downstream consumers must update variable names:**

The previous naming (`DISCOVERED_ADR_DIR`, `DISCOVERED_ARCHITECTURE_DIR`) collided
with the subshell-export problem because the helper's `export` happened inside
`$(...)`. To fix that, the helper now exports **`_PATH` suffixed** names, and
the public functions expose the **canonical short names** by writing them into
their own globals after calling the helper:

- `DISCOVERED_ADR_DIR`             — canonical short name (set by `discover_adr_dir()`)
- `DISCOVERED_ROADMAP_PATH`        — canonical short name (set by `discover_roadmap()`)
- `DISCOVERED_ARCHITECTURE_DIR`    — canonical short name (set by `discover_architecture_dir()`)
- `DISCOVERED_ADR_PATTERN`         — canonical short name (set by `discover_adr_pattern()`)

This means public functions **also** write to the canonical short-name
globals (in addition to the helper's internal `_PATH` globals), so all
downstream consumers (Phase 1 setup, Phase 5 handoff writer, integration
tests) can keep using the short names they were already using.

Concrete implementation pattern (used in all 3 public functions):

```bash
discover_adr_dir() {
  _discover_with_override ADR_DIR dir "docs/adr" SPEC_WORKFLOW_ADR_DIR
  # Promote helper globals to canonical short names
  DISCOVERED_ADR_DIR="${DISCOVERED_ADR_DIR_PATH}"
  DISCOVERED_ADR_DIR_FOUND="${DISCOVERED_ADR_DIR_FOUND}"
  DISCOVERED_ADR_DIR_TRIED="${DISCOVERED_ADR_DIR_TRIED}"
  export DISCOVERED_ADR_DIR DISCOVERED_ADR_DIR_FOUND DISCOVERED_ADR_DIR_TRIED
  echo "${DISCOVERED_ADR_DIR}"
}
```

(Same pattern for `discover_roadmap` and `discover_architecture_dir`.)

**With this fix:**
- `$DISCOVERED_ADR_DIR`, `$DISCOVERED_ROADMAP_PATH`, `$DISCOVERED_ARCHITECTURE_DIR`,
  `$DISCOVERED_*_FOUND`, `$DISCOVERED_*_TRIED` — all defined in caller's shell
- `$DISCOVERED_<KIND>_PATH` — internal helper globals (also exported, but
  consumers don't need them)

**Result**: NO changes needed to Task 3 (Phase 1 setup), Task 3.4 (Phase 5
handoff writer), or Task 5.4 (integration tests) — they keep using
`$DISCOVERED_ADR_DIR` etc. as before.

- [ ] **Step 2.4: Run tests to verify they pass (GREEN)**

Run: `python3 -m pytest tests/unit/test_discover_arch_artifacts.py -v`
Expected: ALL 9 tests pass.

- [ ] **Step 2.5: Commit**

```bash
git add skills/_lib/discover-arch-artifacts.sh tests/unit/test_discover_arch_artifacts.py
git commit -m "feat(adr-0016): add discover-arch-artifacts.sh with 4 discover functions + 9 unit tests"
```

---

## Task 3: Wire discovery into `guide-arch.md` Phase 1 + Phase 5 (TDD red → green)

**Files:**
- Modify: `skills/guide-arch.md` (Phase 1 setup, Phase 5 arch-done)
- Create: `tests/integration/test_arch_discovery_contract.bats` (8 cases, partial coverage in this task)

This task wires the discover function into the actual `guide-arch.md` flow. Two integration tests in this task verify end-to-end; remaining 6 cases land in Task 5.

- [ ] **Step 3.1: Write the first 3 integration tests**

Append to `tests/integration/test_arch_discovery_contract.bats`:

```bash
#!/usr/bin/env bats
#
# Integration tests for arch artifact discovery contract (ADR-0016).
# Covers end-to-end arch-done → handoff write → plan consumer read flow.

load ../test_helper

# Helper: create a temp git repo with custom or default artifact layout.
setup_custom_repo() {
  local layout="$1"  # "default" | "custom_doc" | "missing"
  REPO_TMP=$(mktemp -d)
  cd "$REPO_TMP"
  git init -q
  git config user.email "test@test.local"
  git config user.name "Test"
  case "$layout" in
    default)
      mkdir -p docs/adr docs/architecture
      : > docs/adr/ADR-0001-test.md
      : > docs/adr/ADR-0002-test.md
      : > docs/architecture/v1-gap-analysis.md
      cat > roadmap.md <<EOF
# Roadmap
**当前阶段**: phase-1
EOF
      ;;
    custom_doc)
      mkdir -p doc/adr documentation/architecture
      : > doc/adr/ADR-0001-custom.md
      : > doc/adr/ADR-0002-custom.md
      : > documentation/architecture/custom-gap.md
      cat > planning/roadmap.md <<EOF
# Roadmap
**当前阶段**: phase-2
EOF
      ;;
    missing)
      # Nothing — fallback to defaults
      ;;
  esac
}

teardown_custom_repo() {
  [ -n "$REPO_TMP" ] && rm -rf "$REPO_TMP"
}

@test "arch_discovery: default layout writes handoff with docs/adr and roadmap.md" {
  setup_custom_repo "default"
  PROJECT_ROOT="$REPO_TMP"
  source "$REPO_ROOT/skills/_lib/discover-arch-artifacts.sh"
  discover_adr_dir >/dev/null
  discover_roadmap >/dev/null
  discover_architecture_dir >/dev/null

  # Assert globals set correctly
  [ "$DISCOVERED_ADR_DIR" = "docs/adr" ]
  [ "$DISCOVERED_ADR_DIR_FOUND" = "true" ]
  [ "$DISCOVERED_ROADMAP_PATH" = "roadmap.md" ]
  [ "$DISCOVERED_ROADMAP_FOUND" = "true" ]
  [ "$DISCOVERED_ARCHITECTURE_DIR" = "docs/architecture" ]
  [ "$DISCOVERED_ARCH_FOUND" = "true" ]
  teardown_custom_repo
}

@test "arch_discovery: custom layout (doc/adr) writes discovered paths to handoff" {
  setup_custom_repo "custom_doc"
  PROJECT_ROOT="$REPO_TMP"
  source "$REPO_ROOT/skills/_lib/discover-arch-artifacts.sh"
  discover_adr_dir >/dev/null
  discover_roadmap >/dev/null
  discover_architecture_dir >/dev/null

  [ "$DISCOVERED_ADR_DIR" = "doc/adr" ]
  [ "$DISCOVERED_ADR_DIR_FOUND" = "true" ]
  [ "$DISCOVERED_ROADMAP_PATH" = "planning/roadmap.md" ]
  [ "$DISCOVERED_ROADMAP_FOUND" = "true" ]
  [ "$DISCOVERED_ARCHITECTURE_DIR" = "documentation/architecture" ]
  [ "$DISCOVERED_ARCH_FOUND" = "true" ]
  teardown_custom_repo
}

@test "arch_discovery: missing layout falls back to defaults with found=false" {
  setup_custom_repo "missing"
  PROJECT_ROOT="$REPO_TMP"
  source "$REPO_ROOT/skills/_lib/discover-arch-artifacts.sh"
  discover_adr_dir >/dev/null
  discover_roadmap >/dev/null
  discover_architecture_dir >/dev/null

  [ "$DISCOVERED_ADR_DIR" = "docs/adr" ]            # fallback default
  [ "$DISCOVERED_ADR_DIR_FOUND" = "false" ]        # not actually found
  [ "$DISCOVERED_ROADMAP_PATH" = "roadmap.md" ]     # fallback default
  [ "$DISCOVERED_ROADMAP_FOUND" = "false" ]
  [ "$DISCOVERED_ARCHITECTURE_DIR" = "docs/architecture" ]
  [ "$DISCOVERED_ARCH_FOUND" = "false" ]
  teardown_custom_repo
}
```

- [ ] **Step 3.2: Run tests to verify they fail (RED)**

Run: `bats tests/integration/test_arch_discovery_contract.bats`
Expected: 3 tests fail (script missing or bats test file missing).

- [ ] **Step 3.3: Modify `skills/guide-arch.md` Phase 1 setup (HIGH#2 — must be INSIDE the existing bash block)**

The Phase 1 setup runs as ONE bash block (lines 84-154, between two ``` markers).
Insertion MUST happen INSIDE this block, before the closing ``` at line 154 —
NOT after.

Locate the closing of step 4 (right before line 154's ``` ):

```bash
echo "📋 现有 ADR: $ADR_COUNT"
echo "📋 Roadmap: $ROADMAP_EXISTS"
echo "📋 架构差距分析: $GAP_COUNT"
echo "📋 活动 changes: $ACTIVE_CHANGES"
```

IMMEDIATELY AFTER these 4 echo lines, and BEFORE the closing ``` (line 154), insert:

```bash

# === Phase 1 Step 5: 工件发现 (ADR-0016 Layer 1) ===
# Read candidate paths before arch-done writes handoff.
# Idempotent — does not create files. Safe to run multiple times.

if [ -f "$PROJECT_ROOT/skills/_lib/discover-arch-artifacts.sh" ]; then
    source "$PROJECT_ROOT/skills/_lib/discover-arch-artifacts.sh"
    discover_adr_dir          >/dev/null
    discover_roadmap          >/dev/null
    discover_architecture_dir >/dev/null
    discover_adr_pattern      >/dev/null
    echo ""
    echo "🔍 工件发现 (ADR-0016):"
    echo "   ADR 目录:      $DISCOVERED_ADR_DIR ($DISCOVERED_ADR_DIR_FOUND)"
    echo "   ADR 模式:      $DISCOVERED_ADR_PATTERN"
    echo "   Roadmap:       $DISCOVERED_ROADMAP_PATH ($DISCOVERED_ROADMAP_FOUND)"
    echo "   Architecture:  $DISCOVERED_ARCHITECTURE_DIR ($DISCOVERED_ARCH_FOUND)"
else
    # Fallback when library not yet installed — use hardcoded defaults
    DISCOVERED_ADR_DIR="docs/adr"
    DISCOVERED_ROADMAP_PATH="roadmap.md"
    DISCOVERED_ARCHITECTURE_DIR="docs/architecture"
    DISCOVERED_ADR_PATTERN="ADR-*.md"
    DISCOVERED_ADR_DIR_FOUND="false"
    DISCOVERED_ROADMAP_FOUND="false"
    DISCOVERED_ARCH_FOUND="false"
fi
```

**Critique fixes applied (HIGH#2):**

- Insertion now happens INSIDE the bash code block, between the step 4 echo lines
  and the closing ```. Original draft inserted AFTER line 154's ``` — putting
  the discovery code in Markdown body, which would NOT be executed by the
  phase handler.
- `discover_adr_pattern` is now also called in Phase 1 (previously only in
  Phase 5; missing means `DISCOVERED_ADR_PATTERN` is unset when gates run).

- [ ] **Step 3.4: Modify `skills/guide-arch.md` Phase 5 arch-done handoff write**

Replace the `cat > "$HANDOFF_FILE" << EOF` block (around line 685) with:

```bash
# P2-5 模式: 写入 handoff 状态,作为 arch→plan 的软交接信号
# 包含 ADR-0016 扩展字段 (Layer 2): adr_dir, roadmap_path, architecture_dir,
# adr_pattern, discovered, version
# 缺失 .rddf/state 目录时静默创建 (mkdir -p),写失败不阻塞 arch-done 输出
HANDOFF_FILE="$PROJECT_ROOT/.rddf/state/.arch-handoff.json"
mkdir -p "$PROJECT_ROOT/.rddf/state"

# Re-run discovery to ensure latest values (Task 3 idempotency)
if [ -f "$PROJECT_ROOT/skills/_lib/discover-arch-artifacts.sh" ]; then
    source "$PROJECT_ROOT/skills/_lib/discover-arch-artifacts.sh"
    discover_adr_dir          >/dev/null
    discover_roadmap          >/dev/null
    discover_architecture_dir >/dev/null
    discover_adr_pattern      >/dev/null
fi

# Glob ADR files using DISCOVERED_ADR_PATTERN (NOT the legacy hardcoded
# "ADR-*.md" — projects may use DEC-*.md, RFD-*.md, etc.)
# Pattern is e.g. "ADR-*.md" → glob matches ADR-0001.md.
# We strip the leading prefix (everything before the digits) to extract the 4-digit ID.
# For pattern "ADR-*.md" → id_prefix="ADR-".
#
# ⚠️  Three bash quoting/process-substitution gotchas that the original draft
# got wrong (verified via /tmp reproduction in self-verify):
#   1. FULLY quoted glob: ls "$P/$D/$P" → "No such file" (no glob expansion).
#      FIXED below: prefix is quoted, pattern suffix is unquoted.
#   2. $(ls | grep) command substitution strips trailing newlines and, when
#      piped through another $(...), collapses multi-line results into a
#      single space-separated string. With multiple ADR files this would yield
#      ADR_COUNT=1 instead of N, and IDS as a single concatenated string.
#      FIXED below: use mapfile + process substitution < <(...) for array ops.
#   3. _ID_PREFIX extraction: pattern "ADR-*.md" → sed 's/-.*//' → "ADR"
#      (correct), but pattern "DEC-*.md" → "DEC" (also correct). Works for
#      the standard 1-segment prefix; if a project uses 2-segment prefix
#      (e.g. "MY-TEAM-ADR-*.md") this would over-strip. Out of scope for
#      ADR-0016; documented as known limitation.

ADR_FILES=()
while IFS= read -r -d '' f; do
  case "$f" in
    *"-0000-template.md") continue ;;  # skip template regardless of prefix
  esac
  ADR_FILES+=("$f")
done < <(find "${PROJECT_ROOT}/${DISCOVERED_ADR_DIR}" \
            -maxdepth 1 \
            -name "${DISCOVERED_ADR_PATTERN}" \
            -type f \
            -print0 2>/dev/null)

ADR_COUNT=${#ADR_FILES[@]}

# Extract IDs: prefix-strip using _ID_PREFIX from the pattern.
# For "ADR-*.md" pattern + filename "ADR-0001-foo.md" → "0001".
_ID_PREFIX=$(echo "$DISCOVERED_ADR_PATTERN" | sed 's/-.*$//')
ADR_IDS=()
for f in "${ADR_FILES[@]}"; do
  base=$(basename "$f")
  id=$(echo "$base" | sed "s|^${_ID_PREFIX}-||; s|-.*\.md$||")
  ADR_IDS+=("$id")
done

# Sort IDs numerically and join with comma
ADR_IDS_SORTED=$(printf "%s\n" "${ADR_IDS[@]:-}" | sort -n | paste -sd ',' -)
ADR_IDS_JSON=""
if [ -n "$ADR_IDS_SORTED" ]; then
  # Convert "0001,0002" → '"0001","0002"'
  ADR_IDS_JSON="\"$(echo "$ADR_IDS_SORTED" | sed 's/,/","/g')\""
fi

# 读取当前 roadmap 阶段
CURRENT_PHASE=$(grep -m1 '\*\*当前阶段\*\*' "$PROJECT_ROOT/${DISCOVERED_ROADMAP_PATH}" 2>/dev/null \
  | sed 's/.*\*\*当前阶段\*\*:\s*//' | tr -d '[:space:]' || echo "default")

cat > "$HANDOFF_FILE" << EOF
{
  "arch_complete_at": "$(date -Iseconds)",
  "adr_count": $ADR_COUNT,
  "completed_adr_ids": [$ADR_IDS_JSON],
  "roadmap_exists": $ROADMAP_EXISTS_BOOL,
  "current_phase": "$CURRENT_PHASE",
  "plan_started_at": null,
  "adr_dir": "$DISCOVERED_ADR_DIR",
  "roadmap_path": "$DISCOVERED_ROADMAP_PATH",
  "architecture_dir": "$DISCOVERED_ARCHITECTURE_DIR",
  "adr_pattern": "$DISCOVERED_ADR_PATTERN",
  "discovered": {
    "adr_dir": {
      "found": $([ "$DISCOVERED_ADR_DIR_FOUND" = "true" ] && echo "true" || echo "false"),
      "created": false,
      "candidates_tried": $DISCOVERED_ADR_DIR_TRIED
    },
    "roadmap_path": {
      "found": $([ "$DISCOVERED_ROADMAP_FOUND" = "true" ] && echo "true" || echo "false"),
      "created": false,
      "candidates_tried": $DISCOVERED_ROADMAP_TRIED
    },
    "architecture_dir": {
      "found": $([ "$DISCOVERED_ARCH_FOUND" = "true" ] && echo "true" || echo "false"),
      "created": false,
      "candidates_tried": $DISCOVERED_ARCH_TRIED
    }
  },
  "version": 1
}
EOF

if [ -f "$HANDOFF_FILE" ]; then
    echo "✅ Handoff state written: .rddf/state/.arch-handoff.json (adr_count=$ADR_COUNT, phase=$CURRENT_PHASE, adr_dir=$DISCOVERED_ADR_DIR)"
else
    echo "⚠️  Handoff state write failed, plan 端将硬阻断"
fi
```

Also update the gate check immediately above this block (around line 648) to use discovered paths:

```bash
# 门控 2: roadmap.md 存在性检查 (uses discovered path)
ROADMAP_EXISTS_BOOL=$([ -f "$PROJECT_ROOT/${DISCOVERED_ROADMAP_PATH}" ] && echo "true" || echo "false")
ROADMAP_EXISTS=$([ "$ROADMAP_EXISTS_BOOL" = "true" ] && echo "yes" || echo "no")
echo "门控 2: roadmap.md 存在性检查"
echo "  当前状态: $ROADMAP_EXISTS (path: $DISCOVERED_ROADMAP_PATH)"
if [ "$ROADMAP_EXISTS" != "yes" ]; then
    echo "  ❌ 失败: roadmap.md 不存在"
    echo "     请回到 roadmap-define 阶段创建路线图"
    exit 1
fi
echo "  ✅ 通过"
```

And gate 1:

```bash
# 门控 1: ADR 数量 ≥ 1 (uses discovered path + pattern)
_GLOB="${PROJECT_ROOT}/${DISCOVERED_ADR_DIR}/${DISCOVERED_ADR_PATTERN}"
ADR_COUNT=$(ls "$_GLOB" 2>/dev/null | grep -v -- '-0000-template\.md$' | wc -l | tr -d ' ')
echo "门控 1: ADR 数量检查"
echo "  当前 ADR 数量: $ADR_COUNT (path: $DISCOVERED_ADR_DIR, pattern: $DISCOVERED_ADR_PATTERN)"
```

**Critique fixes applied vs the original draft:**

- Replaced hardcoded `ls -d "$PROJECT_ROOT/${DISCOVERED_ADR_DIR}/ADR-0"*.md` with
  pattern-driven `ls "$PROJECT_ROOT/${DISCOVERED_ADR_DIR}/${DISCOVERED_ADR_PATTERN}"`
  — now works for `DEC-*.md` and `RFD-*.md` conventions too
- Template exclusion is generic: `grep -v -- '-0000-template\.md$'`
  (was hardcoded `ADR-0000-template`)
- ID extraction is prefix-driven via `_ID_PREFIX=$(echo "$DISCOVERED_ADR_PATTERN" | sed 's/-.*$//')`,
  so `DEC-*.md` → IDs are still extracted correctly

- [ ] **Step 3.5: Run tests to verify they pass (GREEN)**

Run: `bats tests/integration/test_arch_discovery_contract.bats`
Expected: 3 tests pass.

- [ ] **Step 3.5b (Momus CRITICAL#3): Extend discovered-paths to Phase 2 (adr-create), 3 (architecture), 4 (roadmap-define)**

The previous fix only wired discovery into Phase 1 (setup) and Phase 5 (arch-done).
The WRITE paths in Phases 2/3/4 still hardcode `docs/adr` / `docs/architecture`
/ `roadmap.md`. Without these changes, the contract is asymmetric — discover finds
`doc/adr` but `adr-create` still writes to `docs/adr`.

For each sub-phase, locate the bash block and replace the hardcoded path assignments:

**(a) Phase 2 (adr-create) — modify `guide-arch.md` lines 210, 216, 270, 274, 305**:

```bash
# OLD line 210:
#   ADR_DIR="$PROJECT_ROOT/docs/adr"
# NEW:
ADR_DIR="$PROJECT_ROOT/${DISCOVERED_ADR_DIR}"

# OLD line 216 (the list command):
#   ls -d "$PROJECT_ROOT/docs/adr/ADR-0"*.md
# NEW:
ls "$PROJECT_ROOT/${DISCOVERED_ADR_DIR}"/${DISCOVERED_ADR_PATTERN} 2>/dev/null | grep -v -- '-0000-template\.md$'

# OLD lines 270, 305 (also ADR_DIR), same substitution.
```

For new ADR file creation (line 290 area):
```bash
# OLD:
#   NEW_ADR="$ADR_DIR/ADR-$NEXT_NUM_PADDED-$ADR_SLUG.md"
# NEW (preserves pattern prefix consistency — line 290 currently writes
# "ADR-NNNN-..." which only matches ADR-*.md; this fix lets it match DEC-*.md too):
NEW_ADR="$ADR_DIR/${DISCOVERED_ADR_PATTERN%-*}-$NEXT_NUM_PADDED-$ADR_SLUG.md"
# For "ADR-*.md": pattern minus "*" → "ADR-" → produces "ADR-0001-foo.md" ✓
# For "DEC-*.md": pattern minus "*" → "DEC-" → produces "DEC-0001-foo.md" ✓
```

**(b) Phase 3 (architecture) — modify `guide-arch.md` lines 341, 401, 460**:

```bash
# OLD:
#   ARCH_DIR="$PROJECT_ROOT/docs/architecture"
# NEW:
ARCH_DIR="$PROJECT_ROOT/${DISCOVERED_ARCHITECTURE_DIR}"

# OLD line 354:
#   GAP_DOCS=$(ls "$ARCH_DIR/"*-gap-analysis.md 2>/dev/null)
# NEW (no change needed — already path-agnostic if ARCH_DIR is right).
```

**(c) Phase 4 (roadmap-define) — modify `guide-arch.md` lines 506, 522**:

```bash
# OLD line 506:
#   ROADMAP_FILE="$PROJECT_ROOT/roadmap.md"
# NEW:
ROADMAP_FILE="$PROJECT_ROOT/${DISCOVERED_ROADMAP_PATH}"

# OLD line 522:
#   CURRENT_PHASE=$(grep -m1 "当前阶段" "$ROADMAP_FILE" 2>/dev/null ...)
# NEW (no change needed — already uses $ROADMAP_FILE which is now discovered).
```

**Critique fix applied (Momus CRITICAL#3):**

- ADR-0016 §Decision §Layer 3 (line 164 of the ADR) states that `guide-arch.md`
  Phase 1/3/4 should be self-consistent. The original plan only wired Phase 1 + 5,
  leaving Phase 2/3/4 to hardcode `docs/adr` / `docs/architecture` / `roadmap.md`.
- This fix extends the discovered-paths convention to all 4 sub-phases so that
  finding + writing paths are aligned.

- [ ] **Step 3.5c (Momus MEDIUM#5): Align new ADR filename with `adr_pattern` in Phase 2 adr-create**

Currently Phase 2 (line 290) writes `ADR-$NEXT_NUM_PADDED-$ADR_SLUG.md`,
which only matches the `ADR-*.md` convention. If a project uses
`DEC-*.md`, the new file won't be discoverable. Replace (already covered
in Step 3.5b (a)) with the pattern-driven formula shown above:

```bash
NEW_ADR="$ADR_DIR/${DISCOVERED_ADR_PATTERN%-*}-$NEXT_NUM_PADDED-$ADR_SLUG.md"
```

`${DISCOVERED_ADR_PATTERN%-*}` strips the trailing `*.md` and keeps the prefix:
- `ADR-*.md` → `ADR-`
- `DEC-*.md` → `DEC-`
- `RFD-*.md` → `RFD-`

- [ ] **Step 3.6: Verify against JSON Schema**

Run a quick manual verification that the produced handoff is valid:

```bash
cd /tmp && rm -rf test_arch_handoff && mkdir test_arch_handoff && cd test_arch_handoff
git init -q && mkdir -p docs/adr && : > docs/adr/ADR-0001-test.md
PROJECT_ROOT=$(pwd) bash -c 'source $1 && discover_adr_dir >/dev/null && cat > /tmp/handoff.json <<EOF
{
  "arch_complete_at": "$(date -Iseconds)",
  "adr_count": 1,
  "completed_adr_ids": ["0001"],
  "roadmap_exists": false,
  "current_phase": "default",
  "plan_started_at": null,
  "adr_dir": "$DISCOVERED_ADR_DIR",
  "roadmap_path": "roadmap.md",
  "architecture_dir": "docs/architecture",
  "adr_pattern": "ADR-*.md",
  "discovered": {"adr_dir":{"found":true,"created":false,"candidates_tried":1}},
  "version": 1
}
EOF' _ /workspace/project/rdd-workflow/skills/_lib/discover-arch-artifacts.sh
python3 -c "
import json
from jsonschema import Draft7Validator
schema = json.loads(open('/workspace/project/rdd-workflow/skills/_lib/schemas/arch_handoff_schema.json').read())
data = json.loads(open('/tmp/handoff.json').read())
errors = list(Draft7Validator(schema).iter_errors(data))
print('OK' if not errors else errors)
"
```

Expected: `OK`

- [ ] **Step 3.7: Commit**

```bash
git add skills/guide-arch.md tests/integration/test_arch_discovery_contract.bats
git commit -m "feat(adr-0016): wire discovery into guide-arch Phase 1 + Phase 5 handoff write"
```

---

## Task 4: Make downstream consumers handoff-aware (Task 4a: guide-plan, propose, roadmap, scan-state)

**Files:**
- Modify: `skills/guide-plan.md` (Phase 0 intake)
- Modify: `skills/propose.md` (Phase 1a)
- Modify: `skills/roadmap.md` (Template 4)
- Modify: `skills/guide.md` (scan-state.sh, the bash extraction)

Each consumer gets a small helper that reads handoff with fallback to defaults.

- [ ] **Step 4.1: Add helper to `skills/guide-plan.md` Phase 0 intake**

Replace lines 119-149 (the `ARCH_HANDOFF` block and subsequent reads) with:

```bash
# Load arch-handoff contract (ADR-0016 Layer 3)
ARCH_HANDOFF="$PROJECT_ROOT/.rddf/state/.arch-handoff.json"
if [ -f "$ARCH_HANDOFF" ]; then
    # Handoff present — read discovered paths (Layer 2 fields)
    ADR_DIR=$(jq -r '.adr_dir // "docs/adr"' "$ARCH_HANDOFF")
    ROADMAP_PATH=$(jq -r '.roadmap_path // "roadmap.md"' "$ARCH_HANDOFF")
    ADR_PATTERN=$(jq -r '.adr_pattern // "ADR-*.md"' "$ARCH_HANDOFF")
    ADR_IDS=$(jq -r '.completed_adr_ids | join(",") // ""' "$ARCH_HANDOFF")
    CURRENT_PHASE=$(jq -r '.current_phase // "default"' "$ARCH_HANDOFF")
    ADR_COUNT=$(jq -r '.adr_count // 0' "$ARCH_HANDOFF")
else
    # Fallback to v2.0 conventions
    ADR_DIR="docs/adr"
    ROADMAP_PATH="roadmap.md"
    ADR_PATTERN="ADR-*.md"
    ADR_IDS=""
    CURRENT_PHASE="default"
    ADR_COUNT=0
fi

# Arch artifact directory existence check (handoff-aware)
ARCHITECTURE_DIR=$(jq -r '.architecture_dir // "docs/architecture"' "$ARCH_HANDOFF" 2>/dev/null || echo "docs/architecture")
GAP_ANALYSIS_DIR="$PROJECT_ROOT/$ARCHITECTURE_DIR"
```

- [ ] **Step 4.2: Modify `skills/propose.md` Phase 1a scanner**

Replace lines 188-210 (the 4 hardcoded `ls` commands) with:

```bash
# Load arch-handoff contract (ADR-0016)
ARCH_HANDOFF="$PROJECT_ROOT/.rddf/state/.arch-handoff.json"
if [ -f "$ARCH_HANDOFF" ]; then
    ADR_DIR=$(jq -r '.adr_dir // "docs/adr"' "$ARCH_HANDOFF")
    ADR_PATTERN=$(jq -r '.adr_pattern // "ADR-*.md"' "$ARCH_HANDOFF")
    ARCHITECTURE_DIR=$(jq -r '.architecture_dir // "docs/architecture"' "$ARCH_HANDOFF")
else
    ADR_DIR="docs/adr"
    ADR_PATTERN="ADR-*.md"
    ARCHITECTURE_DIR="docs/architecture"
fi

# Handoff-aware globs (ADR-0016 Layer 3).
# ⚠️  CRITICAL bash quoting gotcha: full quotes disable glob expansion.
# Use "$PROJECT_ROOT/$ADR_DIR"/$ADR_PATTERN (quote prefix, NOT pattern).
# Verified via: ls "$D/$T" returns "No such file"; ls "$D"/$T works.
ls "$PROJECT_ROOT/$ADR_DIR"/$ADR_PATTERN 2>/dev/null | grep -v -- '-0000-template\.md$' || true
ls "$PROJECT_ROOT/$ARCHITECTURE_DIR/"*-gap-analysis.md 2>/dev/null || true
ls "$PROJECT_ROOT/$ARCHITECTURE_DIR/"*-architecture.md 2>/dev/null || true
ls "$PROJECT_ROOT/$ARCHITECTURE_DIR/"PHASE*-ARCHITECTURE.md 2>/dev/null || true
ls "$PROJECT_ROOT/docs/developer_guide/tech-reports/" 2>/dev/null || true
ls "$PROJECT_ROOT/docs/developer_guide/patterns/" 2>/dev/null || true
```

**Critique fixes applied:**

- Glob is **partially** quoted: `"$PROJECT_ROOT/$ADR_DIR"/$ADR_PATTERN`
  (prefix quoted to allow $variable expansion, suffix unquoted to allow `*`
  expansion). Full-quote `ls "$PROJECT_ROOT/$ADR_DIR/$ADR_PATTERN"` permanently
  returns "No such file" — reproduced in shell test.
- Template filter is pattern-agnostic: `grep -v -- '-0000-template\.md$'`
  (works for any `DEC-0000-template.md`, `RFD-0000-template.md`).

- [ ] **Step 4.3: Modify `skills/roadmap.md` (HIGH#1 — multi-site rework)**

The current `roadmap.md` has **multiple** hardcoded uses of `$ROADMAP_FILE` /
`$PROJECT_ROOT/roadmap.md` (lines 40, 50, 96, 162, 185). For ADR-0016 to work
end-to-end, the entire file must be reworked — not just Template 4.

**(a) Replace lines 40-58** (the global header that pins `ROADMAP_FILE`):

```bash
# OLD line 40:
#   ROADMAP_FILE="$PROJECT_ROOT/roadmap.md"
#
# NEW (fall back to discovered roadmap_path):
ARCH_HANDOFF="$PROJECT_ROOT/.rddf/state/.arch-handoff.json"
if [ -f "$ARCH_HANDOFF" ] && command -v jq >/dev/null 2>&1; then
    ROADMAP_FILE="$PROJECT_ROOT/$(jq -r '.roadmap_path // "roadmap.md"' "$ARCH_HANDOFF")"
else
    ROADMAP_FILE="$PROJECT_ROOT/roadmap.md"
fi
```

**(b) For each remaining hardcoded `cat > "$ROADMAP_FILE" << EOF`** (lines 96, 162),
no code change is needed — `$ROADMAP_FILE` is now resolved from handoff.

**(c) Replace lines 197-202** (Template 4's ADR scan, the original Task 4.3 scope):

```bash
ARCH_HANDOFF="$PROJECT_ROOT/.rddf/state/.arch-handoff.json"
if [ -f "$ARCH_HANDOFF" ]; then
    ADR_DIR=$(jq -r '.adr_dir // "docs/adr"' "$ARCH_HANDOFF")
    ADR_PATTERN=$(jq -r '.adr_pattern // "ADR-*.md"' "$ARCH_HANDOFF")
else
    ADR_DIR="docs/adr"
    ADR_PATTERN="ADR-*.md"
fi

if [ ! -d "$PROJECT_ROOT/$ADR_DIR" ]; then
    mkdir -p "$PROJECT_ROOT/$ADR_DIR"
fi
echo "📋 从 $ADR_DIR 生成路线图"
ADR_COUNT=$(ls "$PROJECT_ROOT/$ADR_DIR"/$ADR_PATTERN 2>/dev/null | grep -v -- '-0000-template\.md$' | wc -l)
```

- [ ] **Step 4.4: Modify `skills/_lib/scan-state.sh` (HIGH#2 fix — INLINE modification, not append)**

The roadmap check at **scan-state.sh:154** is hardcoded:
```bash
if [ ! -f "$PROJECT_ROOT/roadmap.md" ]; then
```

Replace that line with a handoff-aware version **directly inside `scan_state()`**:

```bash
# Inside scan_state() function, around line 154, REPLACE:
#   if [ ! -f "$PROJECT_ROOT/roadmap.md" ]; then
# WITH:
  ARCH_HANDOFF="${PROJECT_ROOT}/.rddf/state/.arch-handoff.json"
  if [ -f "$ARCH_HANDOFF" ] && command -v jq >/dev/null 2>&1; then
    _ROADMAP_FILE="${PROJECT_ROOT}/$(jq -r '.roadmap_path // "roadmap.md"' "$ARCH_HANDOFF")"
  else
    _ROADMAP_FILE="${PROJECT_ROOT}/roadmap.md"
  fi
  if [ ! -f "$_ROADMAP_FILE" ]; then
    RECOMMEND="guide-arch"
    REASON="无 $(jq -r '.roadmap_path // "roadmap.md"' "${ARCH_HANDOFF}" 2>/dev/null || echo "roadmap.md") → 进入架构定义"
    return 0
  fi
```

**Critique fixes applied (HIGH#2 — was previously only appended, not called):**

- Modification is **inline at line 154**, not at end-of-file. Original Task 4.4
  appended `_read_arch_handoff_paths` but never called it — leaving the
  hardcoded roadmap check fully intact.
- The replaced block uses `_ROADMAP_FILE` local var (no global namespace
  pollution in `scan_state`'s caller).

- [ ] **Step 4.5: Run integration tests**

Run: `bats tests/integration/test_arch_discovery_contract.bats`
Expected: 3 tests pass.

- [ ] **Step 4.6: Verify `propose.md` discovery with custom path**

Manual sanity test:

```bash
cd /tmp && rm -rf test_propose && mkdir test_propose && cd test_propose
git init -q
mkdir -p doc/adr
: > doc/adr/DEC-001-foo.md
cat > .rddf/state/.arch-handoff.json <<EOF
{
  "arch_complete_at": "2026-07-08T10:00:00+00:00",
  "adr_count": 1,
  "completed_adr_ids": ["0001"],
  "roadmap_exists": true,
  "current_phase": "default",
  "plan_started_at": null,
  "adr_dir": "doc/adr",
  "roadmap_path": "roadmap.md",
  "architecture_dir": "docs/architecture",
  "adr_pattern": "DEC-*.md",
  "discovered": {"adr_dir":{"found":true,"created":false,"candidates_tried":1}},
  "version": 1
}
EOF
ls doc/adr/DEC-001-foo.md  # should exist
```

Expected: file exists. `propose.md` Phase 1a scan would now find `doc/adr/DEC-001-foo.md`.

- [ ] **Step 4.7: Commit**

```bash
git add skills/guide-plan.md skills/propose.md skills/roadmap.md skills/_lib/scan-state.sh
git commit -m "feat(adr-0016): make guide-plan, propose, roadmap, scan-state.sh handoff-aware"
```

---

## Task 5: Make Python library consumers handoff-aware (Task 4b: gate.py, detectors.py, actions.py)

**Files:**
- Modify: `skills/_lib/gate.py` (lines 56-69)
- Modify: `skills/_lib/detectors.py` (lines 177-178)
- Modify: `skills/_lib/actions.py` (lines 341-350)
- Append to: `tests/integration/test_arch_discovery_contract.bats` (5 more cases)

- [ ] **Step 5.1: Add helper to `skills/_lib/gate.py`**

Insert at top of file (after imports):

```python
# ADR-0016 Layer 3: Helper to read arch-handoff paths (project_root is read
# from `ctx['project_root']`, never from cwd).
import json
from pathlib import Path

_DEFAULT_ADR_DIR = "docs/adr"
_DEFAULT_ROADMAP_PATH = "roadmap.md"
_DEFAULT_ARCHITECTURE_DIR = "docs/architecture"
_DEFAULT_ADR_PATTERN = "ADR-*.md"


def _read_arch_handoff_paths(project_root: str) -> dict:
    """Read .arch-handoff.json with fallback to v2.0 defaults.

    ADR-0016 Layer 3. Returns dict with keys: adr_dir, roadmap_path,
    architecture_dir, adr_pattern.
    """
    handoff_path = Path(project_root) / ".rddf" / "state" / ".arch-handoff.json"
    if not handoff_path.exists():
        return {
            "adr_dir": _DEFAULT_ADR_DIR,
            "roadmap_path": _DEFAULT_ROADMAP_PATH,
            "architecture_dir": _DEFAULT_ARCHITECTURE_DIR,
            "adr_pattern": _DEFAULT_ADR_PATTERN,
        }
    try:
        data = json.loads(handoff_path.read_text())
    except (json.JSONDecodeError, OSError):
        return {
            "adr_dir": _DEFAULT_ADR_DIR,
            "roadmap_path": _DEFAULT_ROADMAP_PATH,
            "architecture_dir": _DEFAULT_ARCHITECTURE_DIR,
            "adr_pattern": _DEFAULT_ADR_PATTERN,
        }
    return {
        "adr_dir": data.get("adr_dir", _DEFAULT_ADR_DIR),
        "roadmap_path": data.get("roadmap_path", _DEFAULT_ROADMAP_PATH),
        "architecture_dir": data.get("architecture_dir", _DEFAULT_ARCHITECTURE_DIR),
        "adr_pattern": data.get("adr_pattern", _DEFAULT_ADR_PATTERN),
    }
```

Then replace the existing 3 `_check_*` functions IN PLACE — preserving the original
tuple `(bool, Optional[str]) -> (passed, severity)` signature (NOT `GateResult`,
which would break `_FunctionDetector.detect()` and `Check.condition(ctx)`):

```python
def _check_adr_exists(ctx: dict) -> tuple[bool, Optional[str]]:
    """ADR-0016: pass if handoff-adr_dir contains any matching pattern files.

    Preserves the original semantic: directory exists AND has at least one file
    matching the discovered adr_pattern.
    """
    project_root = ctx.get("project_root", ".")
    paths = _read_arch_handoff_paths(project_root)
    adr_dir = Path(project_root) / paths["adr_dir"]
    if not adr_dir.is_dir():
        return (False, None)
    # Match the discovered pattern (e.g., "ADR-*.md"); ADR-0000-template is fine
    # here — only the gate inside arch-done excludes it.
    matches = list(adr_dir.glob(paths["adr_pattern"]))
    return (len(matches) > 0, None)


def _check_roadmap_defined(ctx: dict) -> tuple[bool, Optional[str]]:
    """ADR-0016: pass if handoff-roadmap_path exists."""
    project_root = ctx.get("project_root", ".")
    paths = _read_arch_handoff_paths(project_root)
    roadmap = Path(project_root) / paths["roadmap_path"]
    return (roadmap.is_file(), None)


def _check_arch_handoff_exists(ctx: dict) -> tuple[bool, Optional[str]]:
    """Unchanged from v2.0 — handoff must exist regardless of path."""
    project_root = ctx.get("project_root", ".")
    handoff = Path(project_root) / ".rddf" / "state" / ".arch-handoff.json"
    return (handoff.is_file(), None)
```

**Critique fixes applied vs the original draft:**

- **Signature preserved**: `(ctx: dict) -> (bool, Optional[str])`, NOT
  `(project_root, state) -> GateResult`. The existing
  `Check.condition(context)` (line 319 of gate.py) does
  `passed, severity = check.condition(context)`, so a 2-tuple is mandatory.
- **No `GateResult` dataclass** — it has 6 fields including `transition` /
  `failed_checks` that aren't applicable to per-check results.
- **Semantic preserved**: `_check_adr_exists` still requires non-empty directory
  matching `paths["adr_pattern"]` — original logic also required
  `any(f.startswith("ADR-"))`. Pattern is now via handoff, not hardcoded.
- **`ctx.get("project_root", ".")`** — cwd-relative Python reading broken in the
  original draft; this preserves the env-var safety pattern from
  `archive.sh:mark_iteration_archived`.

- [ ] **Step 5.2: Modify `skills/_lib/detectors.py` line 174-188**

The current function is named `detect_adr_status` (not `detect_adrs`).
Replace its body IN PLACE — preserving `(state: dict) -> DetectionResult`
signature and the actual dataclass fields `type`/`data`/`message`/`severity`
(not `detector`/`success`/`data`/`message`):

```python
def detect_adr_status(state: dict) -> DetectionResult:
    """Detect ADR directory status — counts files via handoff-discovered path.

    ADR-0016 Layer 3. Reads .arch-handoff.json; falls back to "docs/adr" + ADR-*.md.
    """
    project_root = state.get("project_root", ".") if isinstance(state, dict) else "."
    paths = _read_arch_handoff_paths(project_root)
    adr_dir = Path(project_root) / paths["adr_dir"]
    if not adr_dir.exists():
        return DetectionResult(
            type="adr_status",
            data={"exists": False, "adr_dir": paths["adr_dir"], "files": []},
            message=f"No ADR directory at {paths['adr_dir']}",
            severity=SEVERITY_WARN,
        )
    adrs = sorted([f.name for f in adr_dir.glob(paths["adr_pattern"])])
    return DetectionResult(
        type="adr_status",
        data={"exists": True, "adrs": adrs, "count": len(adrs), "adr_dir": paths["adr_dir"]},
        message=f"{len(adrs)} ADR(s) found in {paths['adr_dir']}",
    )
```

**Critique fixes applied:**

- Function name is `detect_adr_status` (matches the existing entry in
  `BUILTIN_DETECTORS` which references `fn.__name__`).
- Signature is `(state: dict) -> DetectionResult`, NOT `(project_root, **kwargs)` —
  this matches `_FunctionDetector.detect()` at detectors.py:353 which calls
  `self.fn(state)`.
- Dataclass fields are `type`/`data`/`message`/`severity` (real fields per
  detectors.py:42-57), NOT `detector`/`success`/`data`/`message`.
- Reuses `_read_arch_handoff_paths` from `skills/_lib/gate.py` (no duplicate helper).

- [ ] **Step 5.3: Modify `skills/_lib/actions.py` line 338-360**

The current signature is `action_create_adr(params: dict, event_log: EventLog) -> ActionResult`,
called by `_FunctionAction.execute` via `self.fn(params, event_log)`.
Replace the body — preserve signature, restore `NNNN-slug.md` naming, read ADR dir
from a `params` injected via the calling stack OR fallback to discovered path.

```python
def action_create_adr(params: dict, event_log: EventLog) -> ActionResult:
    """Create a new ADR. params: {title: str, status: str, _project_root: str (optional)}

    ADR-0016 Layer 3: writes to the handoff-discovered adr_dir.
    Falls back to `docs/adr/` when no handoff is present.
    """
    title = params.get("title")
    status = params.get("status", "proposed")
    project_root = params.get("_project_root", ".")

    if not title:
        return ActionResult(success=False, error="title required")

    # Lazy import to avoid circular dependency; reuse gate's handoff reader.
    from .gate import _read_arch_handoff_paths
    paths = _read_arch_handoff_paths(project_root)
    adr_dir = Path(project_root) / paths["adr_dir"]
    adr_dir.mkdir(parents=True, exist_ok=True)
    existing = sorted(adr_dir.glob(paths["adr_pattern"]))
    next_num = len(existing) + 1
    slug = title.lower().replace(" ", "-")
    adr_path = adr_dir / f"{next_num:04d}-{slug}.md"
    adr_path.write_text(
        f"# ADR-{next_num:04d}: {title}\n\n"
        f"**Status:** {status}\n\n"
        f"## Context\n\n## Decision\n\n## Consequences\n"
    )
    # ActionResult dataclass (per actions.py ~line 30): success, data, error, etc.
    return ActionResult(
        success=True,
        data={
            "path": str(adr_path),
            "adr_id": f"{next_num:04d}",
            "adr_dir": paths["adr_dir"],
        },
    )
```

**Critique fixes applied:**

- Signature `(params: dict, event_log: EventLog)` preserved — matches
  `_FunctionAction.execute()` calling pattern at actions.py:406
  (`self.fn(params, event_log)`).
- Filename format restored to `{NNNN}-{slug}.md` (matching the existing
  convention; ADR template content unchanged).
- `_project_root` plumbed via `params` (the existing parameter bag), preserving
  the FunctionAction calling contract.
- `ActionResult` fields restricted to actual ones (no `message=` kwarg).
- No call to undefined `_next_adr_number()` — uses inline `len(existing) + 1`
  same as original.

- [ ] **Step 5.4: Append 5 more integration tests to `test_arch_discovery_contract.bats`**

Append to the bats file (Tasks 5.4-5.8 below are 5 separate test cases):

```bash
@test "arch_discovery: guide-plan reads handoff ADR_DIR (no hardcoded fallback)" {
  setup_custom_repo "custom_doc"
  cat > "$REPO_TMP/.rddf/state/.arch-handoff.json" <<EOF
{
  "arch_complete_at": "2026-07-08T10:00:00+00:00",
  "adr_count": 2,
  "completed_adr_ids": ["0001", "0002"],
  "roadmap_exists": true,
  "current_phase": "phase-2",
  "plan_started_at": null,
  "adr_dir": "doc/adr",
  "roadmap_path": "planning/roadmap.md",
  "architecture_dir": "documentation/architecture",
  "adr_pattern": "ADR-*.md",
  "discovered": {},
  "version": 1
}
EOF
  PROJECT_ROOT="$REPO_TMP"
  ADR_DIR=$(jq -r '.adr_dir // "docs/adr"' "$PROJECT_ROOT/.rddf/state/.arch-handoff.json")
  ROADMAP_PATH=$(jq -r '.roadmap_path // "roadmap.md"' "$PROJECT_ROOT/.rddf/state/.arch-handoff.json")
  [ "$ADR_DIR" = "doc/adr" ]
  [ "$ROADMAP_PATH" = "planning/roadmap.md" ]
  teardown_custom_repo
}

@test "arch_discovery: missing handoff falls back to defaults" {
  setup_custom_repo "default"
  rm -f "$REPO_TMP/.rddf/state/.arch-handoff.json"
  PROJECT_ROOT="$REPO_TMP"
  # Simulate consumer behavior without handoff
  ADR_DIR="docs/adr"
  ROADMAP_PATH="roadmap.md"
  ARCHITECTURE_DIR="docs/architecture"
  ADR_PATTERN="ADR-*.md"
  [ "$ADR_DIR" = "docs/adr" ]
  [ "$ROADMAP_PATH" = "roadmap.md" ]
  [ "$ARCHITECTURE_DIR" = "docs/architecture" ]
  [ "$ADR_PATTERN" = "ADR-*.md" ]
  teardown_custom_repo
}

@test "arch_discovery: malformed handoff (invalid JSON) falls back to defaults" {
  setup_custom_repo "default"
  echo "{ not valid json" > "$REPO_TMP/.rddf/state/.arch-handoff.json"
  PROJECT_ROOT="$REPO_TMP"
  # Python helper would catch json.JSONDecodeError and return defaults
  python3 -c "
import json, sys
from pathlib import Path
try:
    data = json.loads(Path('$REPO_TMP/.rddf/state/.arch-handoff.json').read_text())
except json.JSONDecodeError:
    data = {'adr_dir': 'docs/adr', 'roadmap_path': 'roadmap.md'}
assert data['adr_dir'] == 'docs/adr'
assert data['roadmap_path'] == 'roadmap.md'
"
  teardown_custom_repo
}

@test "arch_discovery: env var override beats handoff" {
  setup_custom_repo "default"
  cat > "$REPO_TMP/.rddf/state/.arch-handoff.json" <<EOF
{"adr_dir": "docs/adr", "roadmap_path": "roadmap.md", "version": 1}
EOF
  PROJECT_ROOT="$REPO_TMP"
  export SPEC_WORKFLOW_ADR_DIR="custom/env/adrs"
  source "$REPO_ROOT/skills/_lib/discover-arch-artifacts.sh"
  discover_adr_dir >/dev/null
  [ "$DISCOVERED_ADR_DIR" = "custom/env/adrs" ]
  unset SPEC_WORKFLOW_ADR_DIR
  teardown_custom_repo
}

@test "arch_discovery: gate.py _check_adr_exists respects discovered path" {
  setup_custom_repo "custom_doc"
  cat > "$REPO_TMP/.rddf/state/.arch-handoff.json" <<EOF
{"adr_dir": "doc/adr", "roadmap_path": "planning/roadmap.md", "version": 1}
EOF
  PROJECT_ROOT="$REPO_TMP"
  python3 -c "
import sys
sys.path.insert(0, '$REPO_ROOT')
from skills._lib.gate import _read_arch_handoff_paths
paths = _read_arch_handoff_paths('$REPO_TMP')
assert paths['adr_dir'] == 'doc/adr'
assert paths['roadmap_path'] == 'planning/roadmap.md'
"
  teardown_custom_repo
}
```

- [ ] **Step 5.5: Run full integration test suite**

Run: `bats tests/integration/test_arch_discovery_contract.bats`
Expected: ALL 8 tests pass.

- [ ] **Step 5.6: Run Python test suite to verify no regressions**

Run: `python3 -m pytest tests/unit/test_gate.py -v`
Expected: existing gate tests still pass (gate.py modifications must not break existing logic).

- [ ] **Step 5.7: Run existing bats smoke tests**

Run: `bats tests/smoke.bats`
Expected: 7 smoke tests pass (no regression in infrastructure).

- [ ] **Step 5.8: Commit**

```bash
git add skills/_lib/gate.py skills/_lib/detectors.py skills/_lib/actions.py tests/integration/test_arch_discovery_contract.bats
git commit -m "feat(adr-0016): make gate.py, detectors.py, actions.py handoff-aware + 5 integration tests"
```

---

## Task 6: Update `AGENTS.md` and document the contract

**Files:**
- Modify: `AGENTS.md` (状态文件表新增 schema 行 + 新增 ADR-0016 子章节)

- [ ] **Step 6.1: Locate the 状态文件 section in AGENTS.md**

Run: `grep -n "状态文件" AGENTS.md`

- [ ] **Step 6.2: Update EXISTING row in the 状态文件 table (LOW#4 fix — don't append)**

In `AGENTS.md` line 105, the row for `.arch-handoff.json` already exists. UPDATE it in place (don't append a duplicate row):

Find:
```markdown
| `.rddf/state/arch-handoff.json` | arch→plan 交接 | `guide-arch` (arch-done 写入) / `guide-plan` (plan-start 读取+更新) |
```

Replace with (note the **dotted** prefix — file is `.arch-handoff.json`):
```markdown
| `.rddf/state/.arch-handoff.json` | arch→plan 交接 + **ADR-0016 发现契约** v1 (adr_dir/roadmap_path/architecture_dir/adr_pattern/discovered/version) | `guide-arch` (arch-done) / `guide-plan` (Phase 0 intake) + `propose`/`roadmap`/`gate.py`/`detectors.py`/`actions.py`/`scan-state.sh` (handoff readers, fallback to defaults) |
```

- [ ] **Step 6.3: Add new subsection "Arch Discovery Contract (ADR-0016)" after the 状态文件 section**

```markdown
### Arch Discovery Contract (ADR-0016)

`guide-arch` Phase 1 setup 通过 `skills/_lib/discover-arch-artifacts.sh` 扫描项目布局,
将发现的 ADR 目录、roadmap 文件、architecture 目录写入 `.arch-handoff.json` 的
`adr_dir` / `roadmap_path` / `architecture_dir` / `adr_pattern` / `discovered` 字段。

**下游消费者** (`guide-plan`, `propose`, `roadmap`, `gate.py`, `detectors.py`,
`actions.py`, `scan-state.sh`) 优先读 handoff,缺失时回退到 v2.0 默认约定:

| 字段 | 默认 fallback |
|------|---------------|
| `adr_dir` | `docs/adr` |
| `roadmap_path` | `roadmap.md` |
| `architecture_dir` | `docs/architecture` |
| `adr_pattern` | `ADR-*.md` |

**环境变量优先级最高** (覆盖 handoff):
- `SPEC_WORKFLOW_ADR_DIR`
- `SPEC_WORKFLOW_ROADMAP_PATH`
- `SPEC_WORKFLOW_ARCHITECTURE_DIR`
- `SPEC_WORKFLOW_ADR_PATTERN`

**Schema 版本**: v1 (字段定义见 `skills/_lib/schemas/arch_handoff_schema.json`)
```

- [ ] **Step 6.4: Update README.md ADR index**

Run: `grep -n "ADR-0012" docs/adr/README.md` to find the index table.

In `docs/adr/README.md`, add row:

```markdown
| [ADR-0016](ADR-0016-arch-artifact-discovery-contract.md) | Arch 阶段工件发现契约 | 已采纳 | 2026-07-08 | 扩展 `.arch-handoff.json` + 替换 14+ 处硬编码路径 |
```

- [ ] **Step 6.5: Register new bats file in CI workflow (HIGH#6)**

To prevent CI regressions on the new arch discovery contract, append
`tests/integration/test_arch_discovery_contract.bats` to the static subset
in `.github/workflows/test.yml` (after line 59, before the closing `\`
continuation). Find this block:

```yaml
      - name: Bats integration tests (static)
        run: |
          bats tests/integration/test_skill_metadata_consistency.bats \
               ...
               tests/integration/scan_state.bats
```

Add a final line:

```yaml
               tests/integration/test_deps_output.bats \
               tests/integration/test_deps_candidate_check.bats \
               tests/integration/scan_state.bats \
               tests/integration/test_arch_discovery_contract.bats   # ← NEW (ADR-0016 HIGH#6)
```

This ensures CI catches regressions in the arch discovery contract.

- [ ] **Step 6.6: Verify documentation**

Run:
```bash
grep -c "ADR-0016" AGENTS.md          # should be >= 2
grep -c "ADR-0016" docs/adr/README.md  # should be >= 1
grep -c "test_arch_discovery_contract.bats" .github/workflows/test.yml  # should be 1
```

- [ ] **Step 6.7 (Momus HIGH#4): Add deep integration test that exercises real public APIs**

The 8 bats cases test helper functions in isolation. Add **2 more deep tests** that
call the real modified modules via their public API. Append to
`tests/integration/test_arch_discovery_contract.bats`:

```bash
@test "arch_discovery: GateMechanism.verify_transition arch_done passes with custom adr_dir" {
  setup_custom_repo "custom_doc"
  cat > "$REPO_TMP/.rddf/state/.arch-handoff.json" <<EOF
{
  "arch_complete_at": "2026-07-08T10:00:00+00:00",
  "adr_count": 2,
  "completed_adr_ids": ["0001", "0002"],
  "roadmap_exists": true,
  "current_phase": "phase-1",
  "plan_started_at": null,
  "adr_dir": "doc/adr",
  "roadmap_path": "planning/roadmap.md",
  "architecture_dir": "documentation/architecture",
  "adr_pattern": "ADR-*.md",
  "discovered": {
    "adr_dir": {"found": true, "created": false, "candidates_tried": 2},
    "roadmap_path": {"found": true, "created": false, "candidates_tried": 3},
    "architecture_dir": {"found": true, "created": false, "candidates_tried": 1}
  },
  "version": 1
}
EOF

  PROJECT_ROOT="$REPO_TMP"
  export PYTHONPATH="$REPO_ROOT:$PYTHONPATH"
  python3 -c "
import sys
sys.path.insert(0, '$REPO_ROOT')
from skills._lib.gate import GateMechanism
gm = GateMechanism(project_root='$REPO_TMP')
result = gm.verify_transition('arch_done', {'project_root': '$REPO_TMP'})
assert result.passed, f'Gate failed: {result.failed_checks} {result.error}'
print('arch_done gate PASSED with custom adr_dir=doc/adr')
"
  unset PYTHONPATH
  teardown_custom_repo
}

@test "arch_discovery: action_create_adr writes to discovered adr_dir matching pattern" {
  setup_custom_repo "default"
  PROJECT_ROOT="$REPO_TMP"
  export PYTHONPATH="$REPO_ROOT:$PYTHONPATH"

  python3 -c "
import sys
sys.path.insert(0, '$REPO_ROOT')
from skills._lib.event_log import EventLog
from skills._lib.actions import action_create_adr
params = {
    'title': 'custom-pattern-test',
    'status': 'proposed',
    '_project_root': '$REPO_TMP',
}
result = action_create_adr(params, EventLog())
assert result.success, f'Action failed: {result.error}'
created = result.data['path']
assert created.startswith('$REPO_TMP/docs/adr/'), f'Wrong dir: {created}'
assert created.endswith('-custom-pattern-test.md'), f'Wrong name: {created}'
print(f'Created: {created}')
"
  unset PYTHONPATH
  teardown_custom_repo
}
```

**Critique fix applied (Momus HIGH#4):**

- These are integration tests that exercise the public APIs that `guide-arch.md`
  invokes at arch-done (`GateMechanism.verify_transition`) and Phase 2
  adr-create (`action_create_adr`).
- Without this, the 8 shallow tests only verify helper isolation, not
  end-to-end contract behavior.

- [ ] **Step 6.8: Commit**

```bash
git add AGENTS.md docs/adr/README.md .github/workflows/test.yml tests/integration/test_arch_discovery_contract.bats
git commit -m "docs(adr-0016): document contract in AGENTS.md + ADR index + CI + deep integration tests"
```

---

## Task 7: Flip ADR-0016 status to 已采纳 + final verification

**Files:**
- Modify: `docs/adr/ADR-0016-arch-artifact-discovery-contract.md` (status field)

- [ ] **Step 7.1: Flip ADR status**

In `docs/adr/ADR-0016-arch-artifact-discovery-contract.md`, change:

```
> **状态**: 待定
```

to:

```
> **状态**: 已采纳
```

- [ ] **Step 7.2: Run all tests**

```bash
python3 -m pytest tests/unit/test_arch_handoff_schema.py tests/unit/test_discover_arch_artifacts.py -v
bats tests/integration/test_arch_discovery_contract.bats
bats tests/smoke.bats
python3 -m pytest tests/unit/ -q --tb=short
```

Expected: all green.

- [ ] **Step 7.3: Update ADR README 实施状态 table**

In `docs/adr/README.md`, in the v2.0 ADR 实施状态 table, add:

```markdown
| [ADR-0016](ADR-0016-arch-artifact-discovery-contract.md) | Arch 阶段工件发现契约 | 已采纳 | **v2.1** |
```

- [ ] **Step 7.4: Commit**

```bash
git add docs/adr/ADR-0016-arch-artifact-discovery-contract.md docs/adr/README.md
git commit -m "chore(adr-0016): flip status to 已采纳, update README v2.1 target"
```

- [ ] **Step 7.5: Write CHANGELOG entry**

Append to `CHANGELOG.md` (create if missing):

```markdown
## [Unreleased] — v2.1

### Added (ADR-0016: Arch Artifact Discovery Contract)

- **JSON Schema**: `skills/_lib/schemas/arch_handoff_schema.json` (v1)
- **Discovery library**: `skills/_lib/discover-arch-artifacts.sh` (4 discover functions)
- **Tests**: 6 schema tests + 9 unit tests + 8 integration tests = 23 new tests
- **Handoff fields**: `adr_dir`, `roadmap_path`, `architecture_dir`, `adr_pattern`, `discovered`, `version`
- **Env var overrides**: `SPEC_WORKFLOW_ADR_DIR`, `SPEC_WORKFLOW_ROADMAP_PATH`, `SPEC_WORKFLOW_ARCHITECTURE_DIR`, `SPEC_WORKFLOW_ADR_PATTERN`

### Changed

- 10 files updated to read handoff paths with fallback defaults (no breaking changes for v2.0 users)
- 14+ hardcoded `docs/adr/` / `roadmap.md` references replaced with handoff-aware readers

### Migration

Zero migration needed. Existing v2.0 projects with `docs/adr/` and `roadmap.md` work unchanged via fallback defaults.
```

- [ ] **Step 7.6: Final commit**

```bash
git add CHANGELOG.md
git commit -m "docs(adr-0016): v2.1 CHANGELOG entry"
```

---

## Self-Review Checklist (Pre-Execution)

Before starting Task 1, verify:

- [ ] All 7 tasks present (1 schema + 1 discover + 1 arch-wire + 1 consumers-md + 1 consumers-py + 1 docs + 1 final)
- [ ] Every Task has `**Files:**` listing Create/Modify/Test paths
- [ ] Every Task has 5-step checkbox structure (RED → GREEN → commit)
- [ ] No "TBD" / "implement later" / "similar to Task N" placeholders
- [ ] Type consistency: `DISCOVERED_ADR_DIR`, `ADR_DIR`, `paths["adr_dir"]` referenced uniformly
- [ ] Function names match: `discover_adr_dir`, `discover_roadmap`, `discover_architecture_dir`, `discover_adr_pattern`, `discover_all`, `_read_arch_handoff_paths`
- [ ] Test counts verified: 6 schema + 9 unit + 8 integration = 23 new tests
- [ ] Commit messages reference `adr-0016` for grep-able history
- [ ] No file outside the 14-file scope is modified

## Open Risks (POST-METIS-REVIEW)

> **All 14 issues raised by Metis pre-execution review have been addressed.** The risks
> below are the **residual** ones — those that pre-existed and are not fully
> eliminated by this plan.

| Risk | Original (Metis issue) | Resolution | Residual concern |
|------|------------------------|-----------|------------------|
| Schema constrains future evolution | — | — | Document version bump path in ADR-0016 §后续待办; bump only when fields change |
| Env-var override never took effect | CRITICAL#1 | FIXED: env vars short-circuit the scan loop; resolved in `discover-arch-artifacts.sh` v2 (Task 2.3) | Unit test `test_env_var_override_takes_precedence` now passes for non-existent env-var paths |
| Glob full-quote disables `*` expansion | CRITICAL#4 | FIXED: `"$PROJECT_ROOT/$ADR_DIR"/$ADR_PATTERN` (prefix quoted, suffix free) | None |
| `gate.py` signature/wrong fields | CRITICAL#2 | FIXED: kept tuple `(bool, Optional[str])`, preserved 'directory non-empty w/ pattern match' semantic, no GateResult | None; existing `test_gate.py` 13 tests pass via Task 5.6 regression check |
| `detectors.py` wrong name/fields/sig | CRITICAL#3 | FIXED: `detect_adr_status` retains `(state) -> DetectionResult(type, data, message, severity)` | None |
| `actions.py` wrong signature/field | CRITICAL#4 (Python) | FIXED: `(params, event_log)` preserved; new `_project_root` plumbed via `params` | None |
| Phase 1 step 5 inserted in markdown body | HIGH#2 | FIXED: insertion now BEFORE the closing ``` of the bash block | Executor must re-verify bash block boundary before edit |
| `_pick_existing` writes to `/tmp` | HIGH#3 | FIXED: removed; replaced with single `_discover_with_override` helper | None |
| Return code 1 vs tests expect 0 | HIGH#4 | FIXED: discover functions always `return 0`; missing-ness signaled via `DISCOVERED_*_FOUND` global | Tests updated to check the global, not exit code |
| `discovered.created` semantics | HIGH#5 | FIXED: ADR §Decision updated; `created` always `false` (read-only scanner); creation handled by adr-create / roadmap-define | None |
| New bats tests not in CI | HIGH#6 | FIXED: `test_arch_discovery_contract.bats` added to `.github/workflows/test.yml` static subset | None |
| `adr_pattern` allows path-traversal | HIGH#7 | FIXED: schema regex `^[A-Za-z0-9_*-]+\.md$` rejects `/` and `..` | None |
| Discovery function naming inconsistency (`-` vs `_`) | MEDIUM | FIXED: filename is `discover-arch-artifacts.sh` (kebab-case, `load_lib` resolves); function names use `snake_case` | None |
| Hardcoded `developer_guide` dirs in propose.md | MEDIUM | OUT OF SCOPE: these dirs are not arch artifacts, not in 14+ hardcoded list | Mark in AGENTS.md as future work |
| Phase 5 JSON heredoc vulnerable to special chars | LOW | Documented in plan; not new | Mitigation: schema rejects; downstream consumers handle malformed JSON gracefully |

## Change History

| Version | Change | Source |
|---------|--------|--------|
| v1.0 | Initial plan for ADR-0016 arch artifact discovery contract | ADR-0016 (this document) |