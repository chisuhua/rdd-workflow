# add-rddf-cli-v1 — Design

Based on spec: `docs/superpowers/specs/2026-07-20-dashboard-design.md` (Oracle-reviewed ×2)

## Architecture

```
skills/_lib/
├── state_reader.py              # Shared read-only data layer (8 functions)
├── cli/
│   ├── __init__.py              # Subcommand routing table
│   ├── __main__.py              # Single CLI entry point
│   ├── dashboard_cmd.py         # Dashboard subcommand handler
│   ├── status_cmd.py            # Status subcommand handler (Mode A+E)
│   └── sessions_cmd.py          # Sessions subcommand handler (list/show/current)
├── dashboard/
│   ├── __init__.py              # DashboardData + collect() orchestrator
│   └── renderer.py              # Terminal / JSON / plain rendering

skills/cli/
└── rddf.sh                      # Bash wrapper (PYTHONPATH + root resolution)
```

## Key Design Decisions

### 1. `state_reader.py` — Fine-grained shared data layer

Exposes individual read functions instead of a monolithic `collect() -> DashboardData`:
- `read_arch_handoff()`, `read_plan_handoff()`, `read_iteration()`, `read_sessions()`, etc.
- Each CLI subcommand imports only what it needs — no reverse coupling.

### 2. Worktree-safe project root

`cli/__main__.py` uses `git rev-parse --git-common-dir` (not `--show-toplevel`).
When run inside a worktree, auto-redirects to the main repo path with an info message.

### 3. Strictly read-only in v1

- Uses `iteration.store._read_unlocked()` — never triggers `_backup_corrupt_file()`.
- Sessions subcommand only exposes `list`/`show`/`current` (write ops deferred to v2).
- All write operations (`resume`, `abandon`, `gc`) require `--owner`/`--yes` safety gates in v2.

### 4. Single entry point

Only `python3 -m skills._lib.cli`. `dashboard/` is a pure library package, not independently executable.

### 5. Terminal auto-degrade

`renderer.py` checks `os.isatty()`: TTY → colored + emoji; non-TTY → plain ASCII automatically.

## Data Flow

```
python3 -m skills._lib.cli dashboard
  → cli/__main__.py: resolve project root (--git-common-dir)
  → cli/dashboard_cmd.py: call dashboard/__init__.py::collect()
    → skills/_lib/state_reader.py: read 8 data sources
  → dashboard/renderer.py: format → stdout
```

## v1 Subcommands

| Command | Description | Source |
|---------|-------------|--------|
| `rddf dashboard` | 7-section project dashboard | `dashboard/renderer.py` |
| `rddf dashboard --json` | JSON output for CI | `dashboard/renderer.py` |
| `rddf dashboard --plain` | ASCII output | `dashboard/renderer.py` |
| `rddf status` | Change overview (Mode A) | `status_cmd.py` → `status/scripts/` |
| `rddf status --iteration` | Sprint view (Mode E) | `iteration/render.py::print_view` |
| `rddf sessions` | List all rddf-sessions | `sessions_cmd.py` → `RddfSessionCoordinator` |
| `rddf sessions show <id>` | Session detail | `sessions_cmd.py` |
| `rddf sessions current` | Current binding | `sessions_cmd.py` |

## Error Handling

- No `.rddf/state/` → short-circuit with info message
- Corrupt JSON → returns None (no backup file written)
- In worktree → auto-redirect to main repo
- Concurrent write → retry once on `JSONDecodeError`
- subprocess timeout → 10s timeout on `git worktree list`