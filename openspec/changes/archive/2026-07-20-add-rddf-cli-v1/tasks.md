# add-rddf-cli-v1 — Tasks

## Overview
- **Test framework**: pytest (unit tests)
- **Test location**: `tests/unit/`

## Tasks

### 1. Create `skills/_lib/state_reader.py` — Shared data layer

- [ ] Write `read_arch_handoff(project_root)` → dict|None
- [ ] Write `read_plan_handoff(project_root)` → dict|None
- [ ] Write `read_iteration(project_root)` → dict|None (via `_read_unlocked`)
- [ ] Write `read_sessions(project_root)` → list[dict]|None
- [ ] Write `read_roadmap_state(project_root)` → dict|None
- [ ] Write `read_proposal_suggestions(project_root)` → list[dict]|None
- [ ] Write `list_worktrees()` → list[WorktreeEntry] (subprocess, timeout=10)
- [ ] Write `list_change_dirs(project_root)` → list[str]

### 2. Create `skills/_lib/dashboard/renderer.py` — Dashboard output

- [ ] Implement terminal output: 7 sections with box-drawing + emoji
- [ ] Implement JSON output mode (`--json`)
- [ ] Implement plain ASCII output mode (`--plain`)
- [ ] Implement `isatty()` auto-degrade detection

### 3. Create `skills/_lib/dashboard/__init__.py` — Dashboard orchestrator

- [ ] Define `DashboardData` dataclass and related types
- [ ] Implement `collect(project_root)` composing state_reader functions

### 4. Create `skills/_lib/cli/__init__.py` + `__main__.py` — CLI entry

- [ ] Subcommand routing table (dashboard / status / sessions)
- [ ] Worktree-safe project root resolution (`--git-common-dir`)
- [ ] Worktree detection + auto-redirect
- [ ] Non-rdd-workflow project detection
- [ ] Help command

### 5. Create `skills/_lib/cli/dashboard_cmd.py` — Dashboard handler

- [ ] Parse `--json` / `--plain` flags
- [ ] Delegate to `dashboard.collect()` → `dashboard.render()`

### 6. Create `skills/_lib/cli/status_cmd.py` — Status handler

- [ ] Mode A: change overview table (reuse `status/scripts/`)
- [ ] Mode E: iteration view (reuse `iteration/render.py::print_view`)

### 7. Create `skills/_lib/cli/sessions_cmd.py` — Sessions handler

- [ ] `list`: all sessions table
- [ ] `show <id>`: single session detail
- [ ] `current`: current binding

### 8. Create `skills/cli/rddf.sh` — Bash wrapper

- [ ] PYTHONPATH auto-resolution from BASH_SOURCE
- [ ] Project root detection
- [ ] Forward to `python3 -m skills._lib.cli`

### 9. Write tests

- [ ] `tests/unit/test_state_reader.py` — 8 data source reads, error handling
- [ ] `tests/unit/test_dashboard_renderer.py` — Terminal/JSON/plain, isatty, empty data
- [ ] `tests/unit/test_cli_routing.py` — Subcommand routing, unknown subcommand, error paths