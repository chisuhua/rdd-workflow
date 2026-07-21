# rddf CLI — Design Spec

**Date:** 2026-07-20
**Status:** Ready for Implementation (Oracle-reviewed ×2)
**Scope:** Add `rddf` unified CLI to spec-workflow for terminal-accessible project state visibility
**Target:** `master`

---

## 1. Background

spec-workflow v2.0 has 13 AI skills, all accessed via `skill_use("xxx")` in AI conversations.
Users cannot check project state from a terminal without AI assistance. This spec adds a
`python3 -m skills._lib.cli` entry point with subcommands for deterministic, read-heavy operations.

### What stays as AI skills (NOT CLI-ized)

| Skill | Reason |
|-------|--------|
| `guide-arch` / `guide-plan` / `guide-ship` | Stateful interactive state machines |
| `execute` | Requires AI code generation |
| `propose` | Requires code scanning + AI analysis |
| `deps` | Requires subagent semantic analysis |
| `spec-workflow/writing-plans` | Requires AI plan generation |

## 2. CLI Tree

```
rddf
├── dashboard                    # v1: 统一仪表盘，7 section
│   ├── (default)                #   终端彩色输出
│   ├── --json                   #   JSON（脚本/CI）
│   └── --plain                  #   ASCII（CI 人类阅读）
│
├── status                       # v1: Change 状态
│   ├── (default)                #   全局概览表 (Mode A)
│   └── --iteration              #   迭代视图 (Mode E)
│
├── sessions                     # v1: Session 管理（只读）
│   ├── (default)                #   List all
│   ├── show <id>                #   详情
│   └── current                  #   当前绑定
│
├── status <name>                # v2: 单 change 详情 (Mode B)
├── status --roadmap             # v2: 路线图状态 (Mode D)
│
├── feature                      # v2: Feature 管理
│   ├── (default)                #   Summary table
│   ├── graph                    #   Mermaid 依赖图
│   ├── status <name>            #   单 feature 详情
│   └── order                    #   Wave 执行顺序
│
├── sessions resume <id>         # v2: 写操作（需 --owner）
├── sessions abandon <id>        # v2: 写操作（需 --yes）
├── sessions gc                  # v2: 心跳 GC（独立子命令）
│
├── guide                        # v3: 推荐器（修复后）
├── roadmap init/validate        # v3: Roadmap 管理
│
└── help
```

### Phased Rollout

| Phase | Subcommands | Key Constraint |
|-------|------------|----------------|
| **v1** | `dashboard`, `status` (A+E), `sessions` (list/show/current) | 严格只读，共享 `_lib/state_reader.py` |
| **v2** | `status` (B+D), `feature` (4), `sessions` (resume/abandon/gc) | 写入有安全条件（--owner/--yes/gc 拆分） |
| **v3** | `guide`, `roadmap` (init/validate) | 需先修复 scan_session_binding bug + 剥离 heartbeat GC |

## 3. Non-Goals

- No `package.json` `bin` field — project distributed via `npx skills add` (file copy).
- No new state files or schema changes.
- No interactive TUI.
- No mutations in v1 (all writes deferred to v2 with safety gates).

## 4. Architecture

### 4.1 Package Structure

```
skills/_lib/
├── state_reader.py              # 🆕 共享数据层：细粒度只读函数
│                                  #   read_arch_handoff(), read_iteration(),
│                                  #   read_sessions(), list_worktrees(), etc.
│
├── cli/
│   ├── __init__.py              # 子命令路由表
│   ├── __main__.py              # 唯一 CLI 入口: python3 -m skills._lib.cli
│   ├── dashboard_cmd.py         # dashboard 子命令 handler
│   ├── status_cmd.py            # status 子命令 handler
│   └── sessions_cmd.py          # sessions 子命令 handler
│
├── dashboard/
│   ├── __init__.py              # export DashboardData, collect(), render()
│   └── renderer.py              # 终端 / JSON / plain 渲染（内部组合 state_reader）
│
skills/cli/
└── rddf.sh                      # 可选 bash wrapper（自动 PYTHONPATH + root 解析）
```

### 4.2 Shared Data Layer: `skills/_lib/state_reader.py`

**设计原则**：暴露细粒度函数，不暴露单一 `collect() -> DashboardData`。各子命令按需调用。

```python
# All functions are read-only. Never writes to any state file.
# Iteration uses iteration.store._read_unlocked() (not load() — avoids backup writes).

read_arch_handoff(project_root: str) -> dict | None
read_plan_handoff(project_root: str) -> dict | None
read_iteration(project_root: str) -> dict | None      # via _read_unlocked
read_sessions(project_root: str) -> list[dict] | None
read_roadmap_state(project_root: str) -> dict | None
read_proposal_suggestions(project_root: str) -> list[dict] | None
list_worktrees() -> list[WorktreeEntry]               # via subprocess(..., timeout=10)
list_change_dirs(project_root: str) -> list[str]      # non-archive dirs
```

`dashboard/__init__.py` 内部组合这些函数构造 `DashboardData`。`status_cmd.py` / `sessions_cmd.py` 同样按需调用。**无反向耦合**。

### 4.3 Single CLI Entry Point

只有一个入口：

```bash
python3 -m skills._lib.cli <subcommand> [args...]
python3 -m skills._lib.cli dashboard --json
python3 -m skills._lib.cli status
python3 -m skills._lib.cli sessions list
```

`cli/__main__.py` 职责：
1. Worktree-safe project root（`git rev-parse --git-common-dir`）
2. 检测 worktree 内运行 → `ℹ️  running from worktree, reading state from <main_repo>`
3. 检测非 spec-workflow 项目 → `ℹ️  not a spec-workflow project (no .rddf/state/)`
4. 子命令路由 → 委托给 `_cmd.py`

**不保留** `dashboard/__main__.py`。`dashboard/` 是纯库。

### 4.4 PYTHONPATH Setup

INSTALL 将 skills 安装到 `.opencode/skills/spec-workflow/skills/`。
`python3 -m skills._lib.cli` 需要 skills 包的**父目录**在 `PYTHONPATH` 上（`import skills._lib.cli` 从这个目录解析）。

```bash
# 手动调用（调试用）
PYTHONPATH="$HOME/.agents/skills/spec-workflow" python3 -m skills._lib.cli dashboard

# 或通过 bash wrapper（推荐）
./rddf dashboard    # wrapper 从 BASH_SOURCE 自推导 PYTHONPATH
```

`skills/cli/rddf.sh` wrapper：
- 从 `BASH_SOURCE` 推导 `PACKAGE_DIR`（spec-workflow 根目录）
- 设置 `PYTHONPATH="$PACKAGE_DIR"`
- 解析 project root（`git rev-parse --git-common-dir`）
- 转发到 `python3 -m skills._lib.cli "$@"`

### 4.5 Terminal Output Auto-degrade

`renderer.py` 检测 `os.isatty(sys.stdout.fileno())`：
- TTY → 彩色 + emoji + box-drawing
- 非 TTY → 自动降级为 plain（等效 `--plain`）

`--plain` flag 可用于显式覆盖。

## 5. Error Handling

| Scenario | Behavior |
|----------|----------|
| No `.rddf/state/` | Short-circuit: `ℹ️ not a spec-workflow project` |
| Missing iteration.json | `_read_unlocked()` returns None → section shows N/A |
| Corrupt iteration.json | Returns None (no `_backup_corrupt_file`) |
| Corrupt sessions.json | Section shows warning + "(unreadable)" |
| In worktree | Auto-redirect to main repo + info line |
| Not in git repo | Worktree/change sections show "(not a git repo)" |
| Concurrent write to iteration.json | `json.JSONDecodeError` → retry once |
| subprocess timeout (git worktree list) | `timeout=10` → empty list |
| Any individual file failure | Other sections render normally |

## 6. v2 Safety Conditions (Write Operations)

### `rddf sessions resume <id>`

```
Required: --owner <opencode_session_id>
Optional: --force (skip conflict detection)

1. If --owner not provided: ❌ "Error: --owner required"
2. Call RddfSessionCoordinator.detect_conflict()
3. If conflict and no --force: ❌ "Conflict: another session owns..."
4. If no conflict or --force: transfer ownership + refresh heartbeat
```

### `rddf sessions abandon <id>`

```
Required: --yes (confirmation gate)

1. If --yes not provided: interactive "Abandon session <id>? [y/N]"
2. Abandon is terminal (cannot undo)
```

### `rddf sessions gc`

```
New subcommand (extracted from check_heartbeat_timeouts):

1. Scans all sessions, marks timed-out active → orphaned
2. Reports: "Marked N sessions as orphaned"
3. Deterministic, no interactive prompts
```

> `rddf sessions list` is strictly read-only — GC is a separate subcommand.

## 7. Testing

```
tests/unit/test_state_reader.py        # 细粒度读取函数
tests/unit/test_dashboard_renderer.py  # 渲染输出
tests/unit/test_cli_routing.py         # 子命令路由
```

| Category | Cases |
|----------|-------|
| state_reader | 8 files present/absent/corrupt, worktree-safe root, PYTHONPATH resolve |
| dashboard renderer | terminal / JSON / plain / isatty auto-degrade / empty data |
| CLI routing | `rddf dashboard` / `rddf status` / `rddf sessions list` / unknown subcmd |
| error handling | concurrent read retry / subprocess timeout / corrupt JSON / non-git |
| regression | `_read_unlocked` doesn't write backup files |

## 8. Implementation

### Change 1: `add-rddf-cli-v1` (this change)

1. Create `skills/_lib/state_reader.py` — 8 read functions
2. Create `skills/_lib/cli/` — `__init__.py`, `__main__.py`
3. Create `skills/_lib/cli/dashboard_cmd.py` — delegate to dashboard renderer
4. Create `skills/_lib/cli/status_cmd.py` — Mode A + Mode E (reuse `iteration/render.py::print_view`)
5. Create `skills/_lib/cli/sessions_cmd.py` — list/show/current (reuse `RddfSessionCoordinator`)
6. Create `skills/_lib/dashboard/` — `__init__.py`, `renderer.py` (composes state_reader)
7. Create `skills/cli/rddf.sh` — bash wrapper
8. Tests: `test_state_reader.py`, `test_dashboard_renderer.py`, `test_cli_routing.py`

### Change 2: `add-rddf-cli-v2` (future)

- `feature_cmd.py` (4 subcommands)
- `sessions` write ops (resume/abandon/gc)
- `status --roadmap` (Mode D), `status <name>` (Mode B)

### Change 3: `add-rddf-cli-v3` (future)

- `guide_cmd.py` (after fixing scan_session_binding + extracting heartbeat GC)
- `roadmap_cmd.py` (init/validate)

### Prerequisite (separate): `fix-scan-state-binding`

- Fix `scan-state.sh` line 231-233 syntax bug (broken double quotes)
- Extract `check_heartbeat_timeouts()` from `scan_session_binding`