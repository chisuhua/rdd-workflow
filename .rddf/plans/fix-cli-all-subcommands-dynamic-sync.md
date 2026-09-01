# fix-cli-all-subcommands-dynamic-sync Implementation Plan

> **For agentic workers:** skill_use("execute")

**Goal:** 消除 `tests/unit/test_cli_all_subcommands.py::ALL_SUBCOMMANDS` 手写 tuple 与 `_lib/cli/` 实际子命令的 drift,新增子命令时自动同步测试,加 whitelist 强制评审新 CLI 命令。

**Architecture:** `ALL_SUBCOMMANDS` 从手写 tuple 改为运行时通过 `_lib.cli.discover_commands()`(或 `_ROUTES.keys()`)动态发现,加 `_lib/cli/WHITELIST` set 强制新命令需人工加入。

**Tech Stack:** Python 3.11+ stdlib (pathlib, importlib), pytest。

## Tasks

### Task 1: 动态 ALL_SUBCOMMANDS + whitelist

- [ ] **Step 1: 写 failing test** `tests/unit/test_cli_all_subcommands.py` 新增 `test_all_subcommands_in_whitelist` 确认 whitelist 包含所有现有命令,5 个新测试覆盖 dynamic / alias / new-cmd-fails-whitelist
- [ ] **Step 2**: 跑测试确认 fail
- [ ] **Step 3**: 重构 `tests/unit/test_cli_all_subcommands.py::ALL_SUBCOMMANDS` 为 `tuple(sorted(discover_commands()))`;加 `WHITELIST` set
- [ ] **Step 4**: 跑所有 CLI 子命令测试 pass
- [ ] **Step 5**: Defer commit

### Task 2: 文档 + commit + archive

- [ ] **Step 1**: `docs/change-quality-guide.md` 加"CLI 子命令白名单"段
- [ ] **Step 2**: `sed -i 's/- \\[ \\]/- [x]/' openspec/changes/fix-cli-all-subcommands-dynamic-sync/tasks.md`
- [ ] **Step 3**: `git add -A && git commit -m "fix(cli): dynamic ALL_SUBCOMMANDS + whitelist"`
- [ ] **Step 4**: `archive_change fix-cli-all-subcommands-dynamic-sync`

## Self-Review
- ✅ 不破坏 `_ROUTES` / `list_commands()` 行为
- ✅ 白名单是 set,新命令需人工加入
