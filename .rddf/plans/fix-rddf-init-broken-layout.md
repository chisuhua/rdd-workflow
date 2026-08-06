# fix-rddf-init-broken-layout Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use skill_use("execute") to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Flatten the shared Python package layout from `skills/_lib/` to top-level `_lib/`, fix two `rddf init` path bugs, and preserve all existing CLI behavior and backward imports.

**Architecture:** Use `git mv` to move `skills/_lib/` to `_lib/` while preserving git history. Add a thin `skills/_lib/__init__.py` shim that re-exports from `_lib` so existing `from skills._lib import X` code keeps working. Fix `__main__.py:154` to use `os.environ.setdefault` so `RDDF_PROJECT_ROOT` is honored. Fix `init_cmd.py` source paths to point at the new top-level `_lib/`. Update `install.sh`, `pyrightconfig.json`, and `pyproject.toml` paths. Add `tests/integration/test_init_smoke.bats` and a Python unit test for the setdefault change. Run full regression suite (pytest + bats) and PTX-EMU subcommand snapshots.

**Tech Stack:** Python 3.11+, bash, git, bats-core, pytest, openspec CLI.

---

## File Structure

### Production Code

| File | Responsibility |
|---|---|
| `_lib/` (moved from `skills/_lib/`) | Shared Python modules, CLI subcommands, and schemas in new top-level location |
| `skills/_lib/__init__.py` | Backward-compat shim re-exporting `_lib` symbols |
| `skills/_lib/<subdir>/__init__.py` | Per-directory backward-compat re-export shims |
| `skills/_lib/cli/__main__.py` | CLI entry; fix `RDDF_PROJECT_ROOT` setdefault |
| `skills/_lib/cli/init_cmd.py` | Init command; fix `_INSTALL_SOURCES` paths |
| `install.sh` | Update PYTHONPATH from `skills/_lib` to `_lib` |
| `pyrightconfig.json` | Update `_lib` paths |
| `pyproject.toml` | Update `_lib` paths |

### Tests

| File | Responsibility |
|---|---|
| `tests/integration/test_init_smoke.bats` | Regression smoke tests for `rddf init` scenarios |
| `tests/unit/test_main_setdefault.py` | Unit test for `__main__.py` setdefault semantics |

---

### Task 1: Move `skills/_lib/` to top-level `_lib/` and create backward-compat shims

**Files:**
- Create: `_lib/` (via `git mv skills/_lib _lib`)
- Create: `skills/_lib/__init__.py`
- Create: `skills/_lib/<subdir>/__init__.py` for each former subdirectory
- Test: `tests/integration/test_init_smoke.bats` (Scenario 3 backward-compat)

- [ ] **Step 1: Verify pre-condition**

Run: `git status --short`
Expected: empty working tree (no uncommitted changes).

- [ ] **Step 2: Execute the move**

Run: `git mv skills/_lib _lib`
Expected: `git status` shows rename of `skills/_lib/` → `_lib/` with no staged modifications.

- [ ] **Step 3: Create backward-compat shim at `skills/_lib/__init__.py`**

Write:
```python
# Backward-compat shim for old import path.
# Re-export everything from the new top-level _lib package.
from _lib import *  # noqa: F401,F403
```

- [ ] **Step 4: Create per-subdirectory shims**

For each directory that used to exist under `skills/_lib/` (e.g., `cli`, `core`, `loop`, `iteration`, `schemas`, `schedulers`), create `skills/_lib/<name>/__init__.py` containing:
```python
from _lib.<name> import *  # noqa: F401,F403
```

- [ ] **Step 5: Verify import backward-compat**

Run: `python3 -c "from skills._lib import X"` (use a real exported name from `_lib`)
Expected: import succeeds.

---

### Task 2: Fix `RDDF_PROJECT_ROOT` override in `__main__.py:154`

**Files:**
- Modify: `skills/_lib/cli/__main__.py:154`
- Test: `tests/unit/test_main_setdefault.py`

- [ ] **Step 1: Write the failing test**

Create `tests/unit/test_main_setdefault.py`:
```python
import os
import sys
import importlib.util
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parents[2] / "skills"


def _load_main_module():
    spec = importlib.util.spec_from_file_location(
        "__main__", SKILL_ROOT / "_lib" / "cli" / "__main__.py"
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules["__main__"] = module
    spec.loader.exec_module(module)
    return module


def test_setdefault_preserves_user_rddf_project_root():
    os.environ["RDDF_PROJECT_ROOT"] = "/custom/source"
    module = _load_main_module()
    # __main__ should set default only when env var is missing
    assert os.environ["RDDF_PROJECT_ROOT"] == "/custom/source"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_main_setdefault.py::test_setdefault_preserves_user_rddf_project_root -v`
Expected: FAIL because current code overwrites the env var.

- [ ] **Step 3: Write minimal implementation**

Edit `skills/_lib/cli/__main__.py:154`:
```python
os.environ.setdefault("RDDF_PROJECT_ROOT", project_root)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_main_setdefault.py -v`
Expected: PASS.

- [ ] **Step 5: Defer commit**

Stage changes but do not commit yet. All commits will be aggregated in the archive phase.

---

### Task 3: Fix `init_cmd.py` source paths for new layout

**Files:**
- Modify: `skills/_lib/cli/init_cmd.py` (around line 26 `_INSTALL_SOURCES` and copytree source paths)
- Test: `tests/integration/test_init_smoke.bats`

- [ ] **Step 1: Write the failing test**

Create `tests/integration/test_init_smoke.bats` with Scenario 1:
```bats
@test "init: creates expected 4 files in target" {
  rm -rf /tmp/rddf-init-target
  RDDF_PROJECT_ROOT="$PROJECT_ROOT" run rddf init /tmp/rddf-init-target
  [ "$status" -eq 0 ]
  [ -d /tmp/rddf-init-target/.opencode/skills/rdd-workflow/skills ]
  [ -d /tmp/rddf-init-target/.opencode/skills/rdd-workflow/_lib ]
  [ -f /tmp/rddf-init-target/.opencode/skills/rdd-workflow/package.json ]
  [ -f /tmp/rddf-init-target/.opencode/skills/rdd-workflow/rddf.sh ]
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `bats tests/integration/test_init_smoke.bats`
Expected: FAIL because `_INSTALL_SOURCES` still points to `skills/_lib/` relative to source root.

- [ ] **Step 3: Write minimal implementation**

Edit `skills/_lib/cli/init_cmd.py`:
- Update `_INSTALL_SOURCES` so source paths are relative to the new top-level `_lib/` (e.g., change entries from `skills/_lib` to `_lib` if the source path was previously expected at source root, or adjust the source root resolution).
- Adjust copytree source paths to match.

- [ ] **Step 4: Run test to verify it passes**

Run: `bats tests/integration/test_init_smoke.bats`
Expected: PASS.

- [ ] **Step 5: Defer commit**

Stage changes; do not commit.

---

### Task 4: Update `install.sh`, `pyrightconfig.json`, and `pyproject.toml` paths

**Files:**
- Modify: `install.sh`
- Modify: `pyrightconfig.json`
- Modify: `pyproject.toml`
- Test: `tests/integration/test_init_smoke.bats` (Scenario 2 global install import), `rddf version`

- [ ] **Step 1: Write the failing test**

Add Scenario 2 to `tests/integration/test_init_smoke.bats`:
```bats
@test "init: target can import _lib.cli.init_cmd" {
  rm -rf /tmp/rddf-init-target
  RDDF_PROJECT_ROOT="$PROJECT_ROOT" rddf init /tmp/rddf-init-target
  python3 -c "import sys; sys.path.insert(0,'/tmp/rddf-init-target/.opencode/skills/rdd-workflow'); from _lib.cli import init_cmd"
  [ "$?" -eq 0 ]
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `bats tests/integration/test_init_smoke.bats`
Expected: FAIL if PYTHONPATH or config paths still reference `skills/_lib`.

- [ ] **Step 3: Write minimal implementation**

- Edit `install.sh`: change `${PACKAGE_DIR}/skills/_lib` to `${PACKAGE_DIR}/_lib` in PYTHONPATH setup.
- Edit `pyrightconfig.json`: update any `skills/_lib` paths to `_lib`.
- Edit `pyproject.toml`: update any `skills/_lib` paths to `_lib`.

- [ ] **Step 4: Run test to verify it passes**

Run: `bats tests/integration/test_init_smoke.bats`
Expected: PASS.

- [ ] **Step 5: Defer commit**

Stage changes; do not commit.

---

### Task 5: Run full regression suite and PTX-EMU snapshot checks

**Files:**
- Modify: `CHANGELOG.md` (breaking-change section)
- Modify: `README.md` (Install section paths)
- Modify: `docs/architecture/` (if layout docs reference old path)

- [ ] **Step 1: Write the failing tests (documentation placeholder)**

Update `CHANGELOG.md`:
```markdown
### Breaking — package layout: skills/_lib → _lib
```

- [ ] **Step 2: Verify CHANGELOG presence fails without content**

Run: `grep "skills/_lib → _lib" CHANGELOG.md`
Expected: initially no match (or FAIL if not yet added).

- [ ] **Step 3: Implement documentation and README updates**

- Add breaking-change entry to `CHANGELOG.md`.
- Update `README.md` Install section to reference new `_lib` path where appropriate.
- Update `docs/architecture/` files if they reference `skills/_lib/`.

- [ ] **Step 4: Run full regression tests**

Run: `pytest tests/ -q`
Expected: PASS, 0 failures, no skips.

Run: `bats tests/`
Expected: PASS, 0 failures.

- [ ] **Step 5: Defer commit**

Stage all changes; do not commit.

---

### Task 6: Aggregate commit and archive preparation

**Files:**
- All staged changes from Tasks 1-5
- Test: `openspec validate fix-rddf-init-broken-layout --json`

- [ ] **Step 1: Verify all tasks complete**

Run: `grep -c "^- \[ \]" openspec/changes/fix-rddf-init-broken-layout/tasks.md`
Expected: 0 (all tasks checked).

- [ ] **Step 2: Review staged diff**

Run: `git diff --staged --stat`
Expected: all changes relate to the layout flattening and init fixes.

- [ ] **Step 3: Create aggregate commit**

Run:
```bash
git add -A
git commit -m "fix(init): flatten package layout per fix-rddf-init-broken-layout

- git mv skills/_lib/ -> _lib/
- add skills/_lib backward-compat shim
- use os.environ.setdefault for RDDF_PROJECT_ROOT
- fix init_cmd.py source paths for _lib/
- update install.sh, pyrightconfig.json, pyproject.toml paths
- add tests/integration/test_init_smoke.bats + unit test for setdefault"
```

- [ ] **Step 4: Validate openspec**

Run: `openspec validate fix-rddf-init-broken-layout --json`
Expected: exit 0.

- [ ] **Step 5: Return to guide-ship for archive**

Call `skill_use("guide-ship")` to enter archive phase.
