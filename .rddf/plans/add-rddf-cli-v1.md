# add-rddf-cli-v1 Implementation Plan

> **For agentic workers:** Use TDD 5-step structure. Steps use checkbox syntax.

**Goal:** Add unified `rddf` CLI with dashboard, status, sessions subcommands.

**Architecture:** Shared `state_reader.py` data layer → `cli/` subcommand routing → `dashboard/renderer.py` rendering. Single entry at `python3 -m skills._lib.cli`.

**Tech Stack:** Python 3.11+, bash, pytest, jsonschema (existing deps)

---

## File Structure

### Production Code

| File | Responsibility |
|------|---------------|
| `skills/_lib/state_reader.py` | 8 fine-grained read-only functions for state files |
| `skills/_lib/dashboard/__init__.py` | DashboardData dataclass + collect() orchestrator |
| `skills/_lib/dashboard/renderer.py` | Terminal / JSON / plain rendering (3 modes) |
| `skills/_lib/cli/__init__.py` | Subcommand routing table |
| `skills/_lib/cli/__main__.py` | CLI entry: root resolution + routing |
| `skills/_lib/cli/dashboard_cmd.py` | Dashboard subcommand handler |
| `skills/_lib/cli/status_cmd.py` | Status subcommand handler (Mode A + E) |
| `skills/_lib/cli/sessions_cmd.py` | Sessions subcommand handler (list/show/current) |
| `skills/cli/rddf.sh` | Bash wrapper for PYTHONPATH + root resolution |

### Tests

| File | Responsibility |
|------|---------------|
| `tests/unit/test_state_reader.py` | 8 data source reads + error handling |
| `tests/unit/test_dashboard_renderer.py` | Terminal/JSON/plain output + isatty |
| `tests/unit/test_cli_routing.py` | Subcommand routing + errors |

---

### Task 1: Create `skills/_lib/state_reader.py`

**Files:** Create: `skills/_lib/state_reader.py`

- [ ] **Step 1: Write the failing test**
```python
# tests/unit/test_state_reader.py
import pytest
from skills._lib.state_reader import read_arch_handoff, read_iteration

def test_read_arch_handoff_present(tmp_path):
    (tmp_path / ".rddf/state").mkdir(parents=True)
    (tmp_path / ".rddf/state/.arch-handoff.json").write_text('{"adr_count": 22}')
    result = read_arch_handoff(str(tmp_path))
    assert result["adr_count"] == 22

def test_read_arch_handoff_missing(tmp_path):
    result = read_arch_handoff(str(tmp_path))
    assert result is None

def test_read_iteration_uses_read_unlocked(tmp_path):
    (tmp_path / ".rddf/state").mkdir(parents=True)
    (tmp_path / ".rddf/state/iteration.json").write_text('{"version": 4, "changes": []}')
    result = read_iteration(str(tmp_path))
    assert result is not None
    assert result["version"] == 4
```

- [ ] **Step 2: Run test to verify it fails**
Run: `pytest tests/unit/test_state_reader.py -v`
Expected: FAIL with ImportError

- [ ] **Step 3: Write minimal implementation**
```python
# skills/_lib/state_reader.py
import json, os, subprocess

def _json_load(path): ...
def read_arch_handoff(pr): ...
def read_plan_handoff(pr): ...
def read_iteration(pr): ...  # uses iteration.store._read_unlocked
def read_sessions(pr): ...
def read_roadmap_state(pr): ...
def read_proposal_suggestions(pr): ...
def list_worktrees(): ...
def list_change_dirs(pr): ...
```

- [ ] **Step 4: Run test to verify it passes**
- [ ] **Step 5: Commit**

...

### Task 2-8: аналогично

(See tasks.md for full breakdown)
