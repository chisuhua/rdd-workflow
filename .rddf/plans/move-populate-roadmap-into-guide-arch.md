# move-populate-roadmap-into-guide-arch Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use skill_use("execute") to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Embed `populate-roadmap-from-arch` v1.1 into `guide-arch` Phase 6 (arch-done exit) with a four-mode incremental roadmap update (skip / adr_only / code_only / full) backed by a new `.populate-state.json` schema v2 and an env-var-driven 3-file split (`roadmap_incremental_update.{sh,py,env.py}`); deprecate `populate-roadmap-from-arch` as a thin wrapper (v1.2).

**Architecture:** Two-phase plan:
1. Build shared scanning + state layer in `_lib/` (ADR catalog, schema v2, 7 new `populate_lib.py` functions).
2. Wire the incremental updater into `guide-arch` Phase 6 + deprecate standalone skill + write 18 scenario tests (T1-T18).

Key design constraints (from design.md): gate is **warning-level only** (not blocking, matches ADR-0018), codegraph signal is **env-var injected** (no MCP from Python subprocess), state file is `.rddf/state/.populate-state.json` (separate from v1.1 supplementary), writes happen in fixed order `save_supplementary` → `save_populate_state` (crash-safe: state lags → conservative fallback).

**Tech Stack:** Python 3.11 (stdlib + jsonschema + pyyaml) + bash (sh wrappers) + bats 1.10+ (integration) + pytest (unit). Oracle C1 env-var pattern (no bash `$VAR` string interpolation in `python3 -c "..."`).

**OpenSpec change artifacts** (canonical): `openspec/changes/move-populate-roadmap-into-guide-arch/{proposal,design,tasks}.md` + `specs/` + `roadmap-meta.yaml`.

---

## File Structure

### Production Code (new)

| File | Responsibility |
|---|---|
| `skills/_lib/adr_catalog.py` | Shared ADR scanner returning `{adr_id: AdrMeta}` (sha256 hash + frontmatter) |
| `skills/_lib/schemas/populate_state_schema.json` | Schema v2 for `.populate-state.json` (version const=2) |
| `skills/guide-arch/scripts/roadmap_incremental_update.sh` | sh wrapper: env var → Python call → stderr redirect |
| `skills/guide-arch/scripts/roadmap_incremental_update.py` | Main module: 4-mode algorithm (skip/adr_only/code_only/full) |
| `skills/guide-arch/scripts/roadmap_incremental_update.env.py` | Env var validation (Oracle C1: no bash `$VAR` injection) |

### Production Code (modify)

| File | Responsibility |
|---|---|
| `skills/populate-roadmap-from-arch/scripts/populate_lib.py` | ADD 7 public functions to `__all__`; refactor `catalog_sources()` to wrapper around `adr_catalog.scan_adr_catalog` |
| `skills/populate-roadmap-from-arch/scripts/populate.sh` | Convert to thin wrapper that sources guide-arch's `roadmap_incremental_update.sh` |
| `skills/populate-roadmap-from-arch/SKILL.md` | Bump `version: 1.2`, add `evolved-from: populate-roadmap-from-arch`, add deprecation banner, add troubleshooting reset command |
| `skills/guide-arch/SKILL.md` | Phase 6 (arch-done exit): add internal "Roadmap Sync" step BEFORE handoff write; update frontmatter `role.boundaries.owns` (ADR-0028 boundary fix) |

### Tests (new)

| File | Responsibility |
|---|---|
| `tests/unit/test_populate_lib_incremental.py` | ≥18 unit tests covering T1-T9 + T13-T16 decision matrix |
| `tests/integration/test_roadmap_incremental_update.bats` | ≥12 bats tests covering T10-T12 + T17-T18 + cross-call chain |

### Tests (modify)

| File | Responsibility |
|---|---|
| `tests/unit/test_schema_version_field.py` | Add `populate_state_schema` to the schema list (20 → 21 schemas) |

### Documentation

| File | Responsibility |
|---|---|
| `AGENTS.md` | "常见陷阱" section: add 3 new entries |
| `docs/proposal-suggestions-format.md` | Add v2 schema example |
| `README.md` | "v2.2 新特性" section: add roadmap incremental section |

---

## Pre-flight

- [ ] **Verify baseline tests pass before changes**

```bash
cd /workspace/project/rdd-workflow
./test.sh --quick
```
Expected: smoke + pytest unit pass. Note pre-existing failures from `tests/KNOWN_FAILURES.txt` baseline.

- [ ] **Locate existing populate_lib.py catalog_sources() (Oracle-verified reuse point)**

```bash
grep -n "def catalog_sources\|class AdrRecord" skills/populate-roadmap-from-arch/scripts/populate_lib.py
```
Expected: `catalog_sources` defined around line 194; `AdrRecord` dataclass nearby.

- [ ] **Confirm guide-arch Phase 6 location for new Step**

```bash
grep -n "Phase 6\|arch-done exit\|写 handoff\|write_arch_handoff" skills/guide-arch/SKILL.md | head -20
```

- [ ] **Set env vars for Oracle C1 compliance**

```bash
export RDDF_CODEGRAPH_FINGERPRINT=""   # populate_lib reads this; empty = use git+rg only
export RDDF_CODEGRAPH_STALE_DAYS=7    # threshold (0 = never stale)
```

---

### Task A: Shared ADR catalog (`_lib/adr_catalog.py`) — TDD

**Files:** `skills/_lib/adr_catalog.py` (NEW), `skills/populate-roadmap-from-arch/scripts/populate_lib.py` (MODIFY line 194)

- [ ] **Step A.1: Write failing pytest for `scan_adr_catalog`**

```python
# tests/unit/test_adr_catalog.py (NEW)
from pathlib import Path
from skills._lib.adr_catalog import scan_adr_catalog, AdrMeta

def test_scan_adr_catalog_returns_dict_of_adrmeta(tmp_path):
    adr_dir = tmp_path / "adr"
    adr_dir.mkdir()
    (adr_dir / "ADR-0001-foo.md").write_text(
        "---\nstatus: 已采纳\ntitle: Foo\n---\n# Foo"
    )
    (adr_dir / "ADR-0002-bar.md").write_text(
        "---\nstatus: 待定\ntitle: Bar\n---\n# Bar"
    )
    result = scan_adr_catalog(tmp_path)
    assert isinstance(result, dict)
    assert set(result.keys()) == {"ADR-0001", "ADR-0002"}
    assert isinstance(result["ADR-0001"], AdrMeta)
    assert result["ADR-0001"].title == "Foo"
    assert len(result["ADR-0001"].file_hash) == 64   # sha256 hex
```

- [ ] **Step A.2: Verify test fails**

```bash
cd /workspace/project/rdd-workflow
python3 -m pytest tests/unit/test_adr_catalog.py -v --tb=short
```
Expected: `ModuleNotFoundError: No module named 'skills._lib.adr_catalog'`.

- [ ] **Step A.3: Implement `AdrMeta` dataclass + `scan_adr_catalog`**

Create `skills/_lib/adr_catalog.py`:
```python
"""Shared ADR catalog scanner (extracted from populate_lib.py::catalog_sources, ADR-0021)."""
from __future__ import annotations
import hashlib
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

ADR_PATTERN = re.compile(r"^ADR-(\d{4})-.*\.md$")

@dataclass
class AdrMeta:
    adr_id: str           # e.g. "ADR-0001"
    file_path: Path
    file_hash: str        # sha256 hex
    title: str
    status: str
    phase: Optional[str] = None
    category: Optional[str] = None

def _parse_frontmatter(text: str) -> dict:
    """Minimal YAML frontmatter parser for status/title fields."""
    if not text.startswith("---"):
        return {}
    end = text.find("\n---", 3)
    if end < 0:
        return {}
    fm = text[3:end].strip()
    out = {}
    for line in fm.splitlines():
        if ":" in line:
            k, _, v = line.partition(":")
            out[k.strip()] = v.strip()
    return out

def scan_adr_catalog(project_root: Path, adr_dir: str = "docs/adr") -> dict[str, AdrMeta]:
    """Scan {project_root}/{adr_dir}/ADR-*.md, return {adr_id: AdrMeta}."""
    root = Path(project_root) / adr_dir
    out: dict[str, AdrMeta] = {}
    if not root.is_dir():
        return out
    for f in sorted(root.glob("ADR-*.md")):
        m = ADR_PATTERN.match(f.name)
        if not m:
            continue
        adr_id = f"ADR-{m.group(1)}"
        text = f.read_text(encoding="utf-8", errors="replace")
        meta = _parse_frontmatter(text)
        out[adr_id] = AdrMeta(
            adr_id=adr_id,
            file_path=f,
            file_hash=hashlib.sha256(text.encode("utf-8")).hexdigest(),
            title=meta.get("title", ""),
            status=meta.get("status", "未知"),
            phase=meta.get("phase"),
            category=meta.get("category"),
        )
    return out
```

- [ ] **Step A.4: Verify test passes**

```bash
cd /workspace/project/rdd-workflow
python3 -m pytest tests/unit/test_adr_catalog.py -v --tb=short
```
Expected: 1 passed.

- [ ] **Step A.5: Defer commit**

按仓库约定，execute 阶段不逐任务 commit；所有变更将在 archive 阶段统一提交。

---

### Task B: State schema v2 — TDD

**Files:** `skills/_lib/schemas/populate_state_schema.json` (NEW), `tests/unit/test_schema_version_field.py` (MODIFY)

- [ ] **Step B.1: Write schema v2 (top-level `version: {const: 2}`)**

Create `skills/_lib/schemas/populate_state_schema.json`:
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "populate-state v2",
  "type": "object",
  "required": ["version", "generated_at", "codebase_commit", "adrs", "reverse_index", "phases"],
  "properties": {
    "version": {"const": 2},
    "generated_at": {"type": "string", "format": "date-time"},
    "codebase_commit": {"type": "string", "minLength": 7},
    "codegraph_fingerprint": {"type": ["string", "null"]},
    "adrs": {
      "type": "object",
      "additionalProperties": {
        "type": "object",
        "required": ["file_path", "file_hash", "title", "status"],
        "properties": {
          "file_path": {"type": "string"},
          "file_hash": {"type": "string", "minLength": 64, "maxLength": 64},
          "title": {"type": "string"},
          "status": {"type": "string"},
          "phase": {"type": ["string", "null"]},
          "category": {"type": ["string", "null"]}
        }
      }
    },
    "reverse_index": {
      "type": "object",
      "description": "symbol -> [adr_id] mapping (populated by adr scan)",
      "additionalProperties": {"type": "array", "items": {"type": "string"}}
    },
    "phases": {
      "type": "object",
      "additionalProperties": {
        "type": "object",
        "required": ["fragment_path", "last_generated_at"],
        "properties": {
          "fragment_path": {"type": "string"},
          "last_generated_at": {"type": "string", "format": "date-time"}
        }
      }
    }
  },
  "additionalProperties": false
}
```

- [ ] **Step B.2: Verify schema is valid JSON + version const=2**

```bash
cd /workspace/project/rdd-workflow
python3 -c "import json; d=json.load(open('skills/_lib/schemas/populate_state_schema.json')); assert d['properties']['version']['const']==2; print('✅ schema valid')"
```
Expected: `✅ schema valid`.

- [ ] **Step B.3: Register schema in test_schema_version_field.py**

Edit `tests/unit/test_schema_version_field.py`: add `"populate_state_schema"` to the list of schemas checked. Search for the existing 20-schema list and append.

- [ ] **Step B.4: Verify registration test passes**

```bash
cd /workspace/project/rdd-workflow
python3 -m pytest tests/unit/test_schema_version_field.py -v --tb=short
```
Expected: pass with new schema in list (20 → 21).

- [ ] **Step B.5: Defer commit**

按仓库约定。

---

### Task C: `populate_lib.py` 7 new public functions — TDD

**Files:** `skills/populate-roadmap-from-arch/scripts/populate_lib.py` (MODIFY: add to `__all__`)

- [ ] **Step C.1: Write failing pytest for all 7 functions (T1-T9 + T13-T16 covered in I.1; here test the 7 functions exist with correct signatures)**

The unit tests for the actual decision matrix belong in `test_populate_lib_incremental.py` (Task I.1). For this step, write a smoke test asserting imports + signatures:

```python
# tests/unit/test_populate_lib_api.py (NEW)
import inspect

def test_load_populate_state_or_default_exists():
    from skills.populate_roadmap_from_arch.scripts.populate_lib import load_populate_state_or_default
    sig = inspect.signature(load_populate_state_or_default)
    assert "project_root" in sig.parameters

def test_save_populate_state_exists():
    from skills.populate_roadmap_from_arch.scripts.populate_lib import save_populate_state
    sig = inspect.signature(save_populate_state)
    assert set(sig.parameters.keys()) >= {"state", "project_root", "codebase_commit"}

def test_detect_adr_changes_exists():
    from skills.populate_roadmap_from_arch.scripts.populate_lib import detect_adr_changes
    sig = inspect.signature(detect_adr_changes)
    assert set(sig.parameters.keys()) >= {"state", "project_root", "scan_adr_catalog_fn"}

def test_detect_code_changes_exists():
    from skills.populate_roadmap_from_arch.scripts.populate_lib import detect_code_changes
    sig = inspect.signature(detect_code_changes)
    assert set(sig.parameters.keys()) >= {"state", "project_root"}

def test_decide_update_mode_exists():
    from skills.populate_roadmap_from_arch.scripts.populate_lib import decide_update_mode
    sig = inspect.signature(decide_update_mode)
    assert set(sig.parameters.keys()) >= {"adr_changes", "code_changes"}

def test_select_adrs_for_incremental_verify_exists():
    from skills.populate_roadmap_from_arch.scripts.populate_lib import select_adrs_for_incremental_verify
    sig = inspect.signature(select_adrs_for_incremental_verify)
    assert set(sig.parameters.keys()) >= {"adrs", "state", "mode", "extra"}

def test_should_rewrite_phase_fragment_exists():
    from skills.populate_roadmap_from_arch.scripts.populate_lib import should_rewrite_phase_fragment
    sig = inspect.signature(should_rewrite_phase_fragment)
    assert set(sig.parameters.keys()) >= {"phase_id", "prev_state", "new_state", "mode"}
```

- [ ] **Step C.2: Verify tests fail**

```bash
cd /workspace/project/rdd-workflow
python3 -m pytest tests/unit/test_populate_lib_api.py -v --tb=short
```
Expected: all 7 fail with `ImportError`.

- [ ] **Step C.3: Implement the 7 functions + add to `__all__`**

Edit `skills/populate-roadmap-from-arch/scripts/populate_lib.py`:
- Add 7 new function stubs/impls as documented in `tasks.md` C1-C7
- Append their names to `__all__` list

Key behaviors (per design.md §4 + §6):
- `load_populate_state_or_default` returns None if file missing or schema mismatch (fail-loud with `stderr "schema version X unsupported"`)
- `save_populate_state` uses atomic write (tempfile + `os.replace`)
- `detect_code_changes` reads env var `RDDF_CODEGRAPH_FINGERPRINT`; does NOT call MCP
- `decide_update_mode` returns `(mode, reason, extra)` where mode ∈ {skip, adr_only, code_only, full}
- `should_rewrite_phase_fragment` returns bool

Also refactor `catalog_sources()` (line 194) to be a wrapper:
```python
def catalog_sources(project_root, **kwargs):
    from skills._lib.adr_catalog import scan_adr_catalog
    catalog = scan_adr_catalog(project_root, **kwargs)
    return {k: v for k, v in catalog.items()}  # backward-compat shape
```

- [ ] **Step C.4: Verify tests pass + no v1.1 regressions**

```bash
cd /workspace/project/rdd-workflow
python3 -m pytest tests/unit/test_populate_lib_api.py -v --tb=short
python3 -m pytest tests/unit/ -q --tb=short -k "populate"
```
Expected: 7 new tests pass; 25 v1.1 tests + 12 supplementary tests still pass.

- [ ] **Step C.5: Defer commit**

---

### Task D: `guide-arch/scripts/roadmap_incremental_update.{sh,py,env.py}` — TDD

**Files:** `skills/guide-arch/scripts/roadmap_incremental_update.{sh,py,env.py}` (NEW), `tests/integration/test_roadmap_incremental_update.bats` (NEW)

- [ ] **Step D.1: Write failing bats tests (T10-T12 + T17-T18 subset for D-series)**

Create `tests/integration/test_roadmap_incremental_update.bats` with these initial tests:
- `roadmap_incremental_update: sh wrapper rejects missing PROJECT_ROOT`
- `roadmap_incremental_update: env var validation rejects malformed CODEBASE_COMMIT`
- `roadmap_incremental_update: full run on empty state.json writes baseline`
- `roadmap_incremental_update: T10 cross-call chain (Phase 6 → roadmap_incremental_update → state updated)`

- [ ] **Step D.2: Verify bats tests fail**

```bash
cd /workspace/project/rdd-workflow
bats tests/integration/test_roadmap_incremental_update.bats
```
Expected: all fail with `roadmap_incremental_update: command not found`.

- [ ] **Step D.3: Create `roadmap_incremental_update.env.py` (Oracle C1 env-var validator)**

```python
"""Validate env vars for roadmap_incremental_update (Oracle C1 — no bash $VAR injection)."""
import os, sys, re

def validate() -> int:
    project_root = os.environ.get("RDDF_PROJECT_ROOT")
    if not project_root or not os.path.isdir(project_root):
        print("ERROR: RDDF_PROJECT_ROOT not set or not a directory", file=sys.stderr)
        return 2
    codebase_commit = os.environ.get("RDDF_CODEBASE_COMMIT", "")
    if codebase_commit and not re.match(r"^[0-9a-f]{7,40}$", codebase_commit):
        print(f"ERROR: RDDF_CODEBASE_COMMIT malformed: {codebase_commit!r}", file=sys.stderr)
        return 2
    # codegraph_fingerprint is optional; "stale" sentinel triggers fallback
    return 0

if __name__ == "__main__":
    sys.exit(validate())
```

- [ ] **Step D.4: Create `roadmap_incremental_update.py` (main 4-mode algorithm)**

```python
"""Main roadmap incremental updater. See tasks.md C1-C7 + design.md Decisions."""
import os, sys, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from skills.populate_roadmap_from_arch.scripts.populate_lib import (
    load_populate_state_or_default, save_populate_state,
    detect_adr_changes, detect_code_changes, decide_update_mode,
    select_adrs_for_incremental_verify, should_rewrite_phase_fragment,
)
from skills._lib.adr_catalog import scan_adr_catalog

def main() -> int:
    project_root = Path(os.environ["RDDF_PROJECT_ROOT"])
    codebase_commit = os.environ.get("RDDF_CODEBASE_COMMIT", "")
    roadmap_update = os.environ.get("RDDF_ROADMAP_UPDATE", "on")  # on/off/force
    incremental = os.environ.get("RDDF_INCREMENTAL", "on") == "on"

    if roadmap_update == "off":
        return 0

    state = load_populate_state_or_default(project_root)
    is_force = roadmap_update == "force" or not incremental
    if state is None or is_force:
        mode = "full"
        reason = "no baseline" if state is None else "force flag"
        adr_changes = ([], [], [])
        code_changes = (set(), [], "stale" if os.environ.get("RDDF_CODEGRAPH_FINGERPRINT") == "stale" else "ok")
    else:
        adr_changes = detect_adr_changes(state, project_root, scan_adr_catalog)
        code_changes = detect_code_changes(state, project_root)
        mode, reason, extra = decide_update_mode(adr_changes, code_changes)

    # ... apply 4-mode logic, update state.json
    new_state = {...}  # build from scan_adr_catalog
    save_populate_state(new_state, project_root, codebase_commit)
    print(f"Mode: {mode} | Reason: {reason}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step D.5: Create `roadmap_incremental_update.sh` (env-var orchestrator)**

```bash
#!/usr/bin/env bash
# sh wrapper — uses env-var passing (Oracle C1), never bash $VAR in python3 -c
set -euo pipefail
PROJECT_ROOT="${RDDF_PROJECT_ROOT:?RDDF_PROJECT_ROOT required}"
GUIDE_ARCH_DIR="${HOME}/.agents/skills/rdd-workflow/skills/guide-arch/scripts"

# Forward caller env vars (already set by caller)
exec python3 "$GUIDE_ARCH_DIR/roadmap_incremental_update.py"
```

- [ ] **Step D.6: Wire sh wrapper call order (crash-safe)**

Per design.md Decision 6: write order is **save_supplementary first** (v1.1), then **save_populate_state** (v2). Add to `.py`:

```python
# Crash-safe write order: supplementary first (v1.1), state last (v2)
# If crash between writes, state lags → conservative fallback next run.
save_supplementary(...)
save_populate_state(...)
```

- [ ] **Step D.7: Verify bats tests pass**

```bash
cd /workspace/project/rdd-workflow
bats tests/integration/test_roadmap_incremental_update.bats
```
Expected: all pass.

- [ ] **Step D.8: Defer commit**

---

### Task E: `guide-arch/SKILL.md` Phase 6 internal Roadmap Sync step — TDD

**Files:** `skills/guide-arch/SKILL.md` (MODIFY: Phase 6 + frontmatter `role.boundaries.owns`)

- [ ] **Step E.1: Write failing integration test**

Add to `tests/integration/test_roadmap_incremental_update.bats`:
- `guide_arch_phase6: contains Roadmap Sync internal step`
- `guide_arch_phase6: frontmatter owns .populate-state.json (ADR-0028)`

- [ ] **Step E.2: Verify tests fail**

```bash
bats tests/integration/test_roadmap_incremental_update.bats
```
Expected: 2 new tests fail (grep returns no matches).

- [ ] **Step E.3: Add internal "Roadmap Sync" step to Phase 6 in guide-arch/SKILL.md**

Locate Phase 6 section (search for `## Phase 6` or `arch-done exit`). Before the existing "write handoff" substep, insert:

```markdown
#### Step X: Roadmap Sync (internal)

> Trigger: arch-done gate passed. Auto-call (no opt-out flag).

Run:
\`\`\`bash
RDDF_PROJECT_ROOT="$PROJECT_ROOT" \
RDDF_CODEBASE_COMMIT="$(git rev-parse HEAD)" \
RDDF_ROADMAP_UPDATE=on \
RDDF_INCREMENTAL=on \
bash "${GUIDE_ARCH_DIR}/roadmap_incremental_update.sh"
\`\`\`

Behavior:
- exit 0 + stderr "Mode: skip" when no changes detected
- exit 0 + writes `.rddf/state/.populate-state.json` when changes
- warning written to `.rddf/quality-reports/.arch-quality-report.json` when roadmap is stale
- **Not** blocking; arch-done gate still only checks ADR ≥ 1 + roadmap.md exists
```

- [ ] **Step E.4: Update frontmatter `role.boundaries.owns` (ADR-0028)**

Add to `role.boundaries.owns` array:
```
- `.rddf/state/.populate-state.json`
- `.rddf/roadmap/phases/*.md`
```

- [ ] **Step E.5: Verify integration tests pass + Phase 5 dual gate unchanged**

```bash
cd /workspace/project/rdd-workflow
bats tests/integration/test_roadmap_incremental_update.bats
bats tests/integration/test_guide_arch_skill.bats
```
Expected: new E-series tests pass; existing guide-arch tests pass (Phase 5 dual gate untouched).

- [ ] **Step E.6: Defer commit**

---

### Task F: `populate-roadmap-from-arch` v1.2 deprecation — TDD

**Files:** `skills/populate-roadmap-from-arch/SKILL.md` (MODIFY), `skills/populate-roadmap-from-arch/scripts/populate.sh` (MODIFY to thin wrapper)

- [ ] **Step F.1: Write failing tests for thin wrapper + v1.2 metadata**

Create `tests/integration/test_populate_wrapper.bats`:
- `populate_wrapper: v1.2 frontmatter has version 1.2 + evolved-from`
- `populate_wrapper: SKILL.md contains deprecation banner mentioning guide-arch`
- `populate_wrapper: SKILL.md troubleshooting has reset command`
- `populate_wrapper: populate.sh sources guide-arch's roadmap_incremental_update.sh`

- [ ] **Step F.2: Verify tests fail**

```bash
bats tests/integration/test_populate_wrapper.bats
```
Expected: 4 fail.

- [ ] **Step F.3: Update SKILL.md frontmatter**

```yaml
metadata:
  version: "1.2"
  evolved-from: "populate-roadmap-from-arch"
  deprecated: true
  replacement: "guide-arch"
```

- [ ] **Step F.4: Add deprecation banner at top of SKILL.md (after frontmatter)**

```markdown
> ⚠️ **DEPRECATED (v2.2+)**: This skill is superseded by `guide-arch`'s built-in Phase 6 Roadmap Sync step. New projects should call `skill_use("guide-arch")` directly. This skill is preserved as a thin wrapper for backward compatibility; use `--standalone` flag to invoke the v1.1 behavior.
```

- [ ] **Step F.5: Add troubleshooting reset command**

In the troubleshooting section, add:
```markdown
### Reset roadmap incremental state

\`\`\`bash
rm .rddf/state/.populate-state.json   # next run will fallback to full mode
\`\`\`

Use when:
- Branch/worktree switch left stale state
- codegraph signal corrupted state
- Manual full regeneration desired
```

- [ ] **Step F.6: Convert `populate.sh` to thin wrapper**

Replace the body of `skills/populate-roadmap-from-arch/scripts/populate.sh`:
```bash
#!/usr/bin/env bash
# Thin wrapper — delegates to guide-arch's roadmap_incremental_update.sh
set -euo pipefail
PROJECT_ROOT="${1:-$(git rev-parse --show-toplevel)}"

# Forward CLI flags as env vars
export RDDF_PROJECT_ROOT="$PROJECT_ROOT"
export RDDF_CODEBASE_COMMIT="${RDDF_CODEBASE_COMMIT:-$(git rev-parse HEAD)}"
[ "${1:-}" = "--standalone" ] && export RDDF_ROADMAP_UPDATE=force
[ "${2:-}" = "--incremental=off" ] && export RDDF_INCREMENTAL=off

GUIDE_ARCH_SCRIPTS="${HOME}/.agents/skills/rdd-workflow/skills/guide-arch/scripts"
exec bash "$GUIDE_ARCH_SCRIPTS/roadmap_incremental_update.sh"
```

- [ ] **Step F.7: Preserve CLI compatibility**

Accept flags: `--code-verify=off|on|strict`, `--incremental`, `--standalone`. Map to env vars.

- [ ] **Step F.8: Verify tests pass + v1.1 tests still pass**

```bash
cd /workspace/project/rdd-workflow
bats tests/integration/test_populate_wrapper.bats
bats tests/integration/test_populate_roadmap_from_arch.bats  # 5 v1.1 tests
python3 -m pytest tests/unit/ -q -k "populate"  # 25 unit tests
```
Expected: all pass (v1.1 backward compat maintained).

- [ ] **Step F.9: Defer commit**

---

### Task G: Test coverage T1-T18 (decision matrix) — TDD

**Files:** `tests/unit/test_populate_lib_incremental.py` (NEW, ≥18 tests), `tests/integration/test_roadmap_incremental_update.bats` (extend to ≥12 tests)

- [ ] **Step G.1: Write failing unit tests for T1-T9 + T13-T16 (18 total)**

`tests/unit/test_populate_lib_incremental.py`:
- T1: `decide_update_mode(([],[],[]), (set(),[],'ok'))` → mode='skip'
- T2: only ADR changed → mode='adr_only'
- T3: only code changed → mode='code_only'
- T4: both changed → mode='full'
- T5: new ADR detected → mode='adr_only', new in `extra`
- T6: ADR deleted → mode='adr_only', deleted in `extra`
- T7: state=None → caller decides mode='full'
- T8: `RDDF_CODEGRAPH_FINGERPRINT=stale` → caller decides mode='full'
- T9: state.version=1 (mismatch) → caller decides mode='full'
- T13: `git_commit_exists(last_commit)=false` → mode='full' + stderr warning
- T14: rebase `last_commit..HEAD` valid → exit 0
- T15: cherry-pick → exit 0 + state rewritten
- T16: merge commit → code_only (conservative)
- T17: state missing in worktree → mode='full'
- T18: state mismatch codebase_commit → mode='full' (auto reset)
- + 3 boundary tests for edge cases (empty reverse_index, duplicate symbols, etc.)

- [ ] **Step G.2: Verify tests fail**

```bash
cd /workspace/project/rdd-workflow
python3 -m pytest tests/unit/test_populate_lib_incremental.py -v --tb=short
```
Expected: 18 fail.

- [ ] **Step G.3: Implement decision matrix logic in `decide_update_mode`**

If implementation is partial, expand it. Reference `tasks.md` G.1 and design.md §4.

- [ ] **Step G.4: Verify tests pass**

```bash
python3 -m pytest tests/unit/test_populate_lib_incremental.py -v --tb=short
```
Expected: 18 passed.

- [ ] **Step G.5: Write failing bats tests for T10-T12 + T17-T18 (12 total in integration file)**

Extend `tests/integration/test_roadmap_incremental_update.bats`:
- T10: guide-arch Phase 6 auto-call chain → state.json updated after arch-done
- T11: `--roadmap-update=off` skips entirely
- T12: `--roadmap-update=force` forces full mode
- T17: worktree first run (no state) → mode=full, exit 0
- T18: codebase_commit mismatch → mode=full (auto reset), exit 0
- + 7 integration scenarios: cross-call chain, error paths, env var validation, atomic write

- [ ] **Step G.6: Verify bats tests fail**

```bash
bats tests/integration/test_roadmap_incremental_update.bats
```
Expected: 12 new tests fail.

- [ ] **Step G.7: Implement integration scenarios**

Wire up the actual cross-call chain in sh wrapper, ensure error handling, atomic write verification, env var precedence.

- [ ] **Step G.8: Verify all tests pass**

```bash
cd /workspace/project/rdd-workflow
bats tests/integration/test_roadmap_incremental_update.bats
python3 -m pytest tests/unit/test_populate_lib_incremental.py tests/unit/test_adr_catalog.py -v
```
Expected: ≥12 bats + ≥18 pytest all pass.

- [ ] **Step G.9: Defer commit**

---

### Task H: Documentation updates — TDD-light (manual verification)

**Files:** `AGENTS.md` (MODIFY), `docs/proposal-suggestions-format.md` (MODIFY), `README.md` (MODIFY)

- [ ] **Step H.1: AGENTS.md "常见陷阱" — add 3 entries**

Locate "## 常见陷阱" section (line ~370). Append after existing 21 entries:

```markdown
22. **roadmap 增量 state 隔离**: 切分支/切 worktree 后第一次 arch-done 自动 fallback full (per-worktree `.rddf/state/` 隔离; state 绑 codebase_commit)
23. **codegraph signal 必须 env-var 注入**: Python subprocess 上下文无法访问 MCP session — populate_lib 内部**禁止**调 MCP; agent 侧通过 `RDDF_CODEGRAPH_FINGERPRINT` env var 注入 signal
24. **reset roadmap 增量 state**: `rm .rddf/state/.populate-state.json` (无 baseline → 下次 full); 用于分支切换残留、codegraph 索引陈旧、人工强制全量
```

- [ ] **Step H.2: `docs/proposal-suggestions-format.md` — add v2 schema example**

Add a new section after v1 example:
```markdown
### v2 Schema Example (populate-state.json)

\`\`\`json
{
  "version": 2,
  "generated_at": "2026-08-21T17:30:00Z",
  "codebase_commit": "9536da9",
  "codegraph_fingerprint": null,
  "adrs": {
    "ADR-0001": {"file_path": "docs/adr/ADR-0001-...", "file_hash": "abc...", "title": "...", "status": "已采纳"}
  },
  "reverse_index": {"populate_lib": ["ADR-0001"]},
  "phases": {"phase-1": {"fragment_path": ".rddf/roadmap/phases/phase-1.md", "last_generated_at": "..."}}
}
\`\`\`
```

- [ ] **Step H.3: `README.md` "v2.2 新特性" — add roadmap incremental section**

After existing v2.2 features:
```markdown
### Roadmap Incremental Update (v2.2+)

`guide-arch` Phase 6 自动调用 `roadmap_incremental_update.sh`,基于 git HEAD + ADR file hash + reverse index 三源判定增量更新模式:
- skip (零变更) — `< 0.1s`
- adr_only (仅 ADR 改) — `< 1s`,仅重写受影响 phase fragment
- code_only (仅代码改) — `< 1.5s`,仅重验证受影响 ADR
- full (两方皆改 / 无 baseline / 陈旧) — `~4s`

Reset 命令: `rm .rddf/state/.populate-state.json`
```

- [ ] **Step H.4: Verify no broken markdown**

```bash
cd /workspace/project/rdd-workflow
grep -c "^## " AGENTS.md
grep -c "^## " docs/proposal-suggestions-format.md
grep -c "^## " README.md
```
Expected: counts consistent with previous values (heading hierarchy preserved).

- [ ] **Step H.5: Defer commit**

---

### Task I: Schema registration + regression baseline — TDD

**Files:** `tests/unit/test_schema_version_field.py` (already updated in B.3, verify here)

- [ ] **Step I.1: Verify populate_state_schema registered (21 schemas total)**

```bash
cd /workspace/project/rdd-workflow
python3 -m pytest tests/unit/test_schema_version_field.py -v --tb=short
```
Expected: pass with 21 schemas (was 20).

- [ ] **Step I.2: Run full pytest suite to confirm no regressions**

```bash
cd /workspace/project/rdd-workflow
python3 -m pytest tests/unit/ tests/integration/ -q --tb=short
```
Expected: baseline 2018 passed + the 18 new tests in test_populate_lib_incremental.py pass. Total ~2040+ pass; pre-existing 4 failures unchanged.

- [ ] **Step I.3: Run smoke + bats suite**

```bash
cd /workspace/project/rdd-workflow
bats tests/smoke.bats
```
Expected: 7 smoke tests pass.

- [ ] **Step I.4: Defer commit**

---

### Task J: Archive pre-flight (full regression gate) — MANDATORY

**Files:** none (verification only)

- [ ] **Step J.1: Run `./test.sh --full --regression`**

```bash
cd /workspace/project/rdd-workflow
./test.sh --full --regression
```
Expected: full suite pass. **0 new failures** vs `tests/KNOWN_FAILURES.txt` baseline (4 pre-existing unrelated failures allowed).

- [ ] **Step J.2: Performance benchmark**

```bash
cd /workspace/project/rdd-workflow
# T1 (zero-change skip): expect < 0.1s
time RDDF_PROJECT_ROOT=. RDDF_CODEBASE_COMMIT="$(git rev-parse HEAD)" \
  bash skills/guide-arch/scripts/roadmap_incremental_update.sh 2>&1
# Second run should be < 0.1s (skip mode)

# T2 (ADR only): expect < 1s — modify ADR-0001 one line, run again

# T3 (code only): expect < 1.5s — modify skills/guide/SKILL.md, run again

# T13/T17/T18 (full fallback): expect < 4s
```
Expected: all within stated budgets.

- [ ] **Step J.3: Manual reset verification**

```bash
cd /workspace/project/rdd-workflow
rm .rddf/state/.populate-state.json
RDDF_PROJECT_ROOT=. RDDF_CODEBASE_COMMIT="$(git rev-parse HEAD)" \
  bash skills/guide-arch/scripts/roadmap_incremental_update.sh 2>&1 | grep -i "Mode: full"
```
Expected: stderr shows `Mode: full | Reason: no baseline` + exit 0.

- [ ] **Step J.4: Worktree commit (per AGENTS.md Worktree Commit Flow)**

```bash
cd /workspace/project/rdd-workflow
git add -A
git status --short   # confirm all changes staged
git commit -m "feat(guide-arch): embed populate-roadmap into Phase 6 + 4-mode incremental

- New: skills/_lib/adr_catalog.py (shared ADR scanner, ADR-0021)
- New: skills/_lib/schemas/populate_state_schema.json (v2)
- New: skills/guide-arch/scripts/roadmap_incremental_update.{sh,py,env.py} (3-file env-var split)
- Modify: populate_lib.py (7 new public functions, catalog_sources wrapper)
- Modify: populate-roadmap-from-arch (v1.2 deprecation + thin wrapper)
- Modify: guide-arch/SKILL.md (Phase 6 internal Roadmap Sync step)
- Tests: 18 unit + 12 bats covering T1-T18 scenarios
- Docs: AGENTS.md traps + proposal-suggestions-format.md v2 + README v2.2

Closes: move-populate-roadmap-into-guide-arch"
git log -1 --oneline
```
Expected: 1 commit on `openspec/move-populate-roadmap-into-guide-arch` branch.

- [ ] **Step J.5: Verify commit landed**

```bash
cd /workspace/project/rdd-workflow
git log --oneline -3
git status
```
Expected: 1 commit ahead of `master`; working tree clean.

---

## Acceptance Criteria

- [ ] `skills/_lib/adr_catalog.py` exists; `populate_lib.py::catalog_sources()` is a wrapper
- [ ] `skills/_lib/schemas/populate_state_schema.json` v2 exists; version const=2
- [ ] `populate_lib.py` exports 7 new public functions in `__all__`
- [ ] `skills/guide-arch/scripts/roadmap_incremental_update.{sh,py,env.py}` exist; bats tests pass
- [ ] `guide-arch/SKILL.md` Phase 6 contains internal "Roadmap Sync" step (not Step 5.5 / Phase 5.5 / Phase 6.5)
- [ ] `guide-arch/SKILL.md` frontmatter `role.boundaries.owns` includes `.rddf/state/.populate-state.json` and `.rddf/roadmap/phases/*.md` (ADR-0028)
- [ ] `populate-roadmap-from-arch/SKILL.md` frontmatter `version: 1.2` + `evolved-from: populate-roadmap-from-arch` + deprecation banner + troubleshooting reset command
- [ ] `populate-roadmap-from-arch/scripts/populate.sh` is a thin wrapper
- [ ] `tests/unit/test_populate_lib_incremental.py` has ≥18 tests covering T1-T9 + T13-T16
- [ ] `tests/integration/test_roadmap_incremental_update.bats` has ≥12 @test
- [ ] `tests/unit/test_schema_version_field.py` lists 21 schemas (20 → 21)
- [ ] All existing tests pass (baseline 2018 + new ~30 = ~2048; 4 pre-existing failures unchanged)
- [ ] T1 (zero-change) benchmark: `< 0.1s`
- [ ] T13/T17/T18 benchmark: `< 4s` (full fallback)
- [ ] AGENTS.md "常见陷阱" has 24 entries (was 21)
- [ ] `docs/proposal-suggestions-format.md` has v2 schema example
- [ ] `README.md` "v2.2 新特性" has roadmap incremental section
- [ ] Worktree branch has 1+ commits (required for archive gate)
- [ ] `./test.sh --full --regression` returns 0 new failures

## Commit History Expected

```
9536da9 (master base) chore(proposal-approved): ... (pre-existing)
feat(guide-arch): embed populate-roadmap into Phase 6 + 4-mode incremental
```

The single commit aggregates A-J work per AGENTS.md "Worktree Commit Flow" v2.0.5+ rule.
