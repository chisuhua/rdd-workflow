## Why

spec-workflow v2.0 has 13 AI skills, all accessed via `skill_use("xxx")` in AI conversations.
Users cannot check project state from a terminal without AI assistance. 

We need a unified CLI (`python3 -m skills._lib.cli`) that aggregates all deterministic,
read-heavy operations into terminal-accessible subcommands, starting with `dashboard`, 
`status`, and `sessions` in v1.

## What Changes

This change creates the `rddf` CLI framework with three v1 subcommands:

**New files:**
- `skills/_lib/state_reader.py` — Shared read-only data layer (8 functions reading from `.rddf/state/` + git)
- `skills/_lib/cli/__init__.py` — Subcommand routing table
- `skills/_lib/cli/__main__.py` — Single CLI entry point with worktree-safe root resolution
- `skills/_lib/cli/dashboard_cmd.py` — Dashboard subcommand handler
- `skills/_lib/cli/status_cmd.py` — Status subcommand handler (Mode A + Mode E)
- `skills/_lib/cli/sessions_cmd.py` — Sessions subcommand handler (list/show/current)
- `skills/_lib/dashboard/__init__.py` — Dashboard data collection + orchestration
- `skills/_lib/dashboard/renderer.py` — Terminal / JSON / plain rendering
- `skills/cli/rddf.sh` — Bash wrapper for PYTHONPATH auto-resolution

**Tests:**
- `tests/unit/test_state_reader.py` — 8 data source reads, error handling
- `tests/unit/test_dashboard_renderer.py` — Terminal / JSON / plain output, isatty detection
- `tests/unit/test_cli_routing.py` — Subcommand routing, unknown command, error paths

**Key design decisions (Oracle-reviewed x2):**
- Uses `iteration.store._read_unlocked()` (not `load()`) to avoid backup-file writes on corrupt data
- Uses `git rev-parse --git-common-dir` for worktree-safe project root resolution
- Single entry point at `cli/__main__.py` (no `dashboard/__main__.py`)
- Shared data layer exposed as fine-grained functions in `state_reader.py` to prevent reverse coupling
- Terminal output auto-degrades to plain ASCII when not a TTY