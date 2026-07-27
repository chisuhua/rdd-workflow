# fix-ship-lightweight-wt-path-pollution — Design

## Root Cause

`setup_execution_workspace()` echoes status messages + git checkout output to stdout. Caller `WT_PATH=$(setup_execution_workspace ...)` captures all → WT_PATH becomes multi-line garbage.

## Fix (2 lines)

Line 224: Suppress git checkout stdout
```bash
git -C "$project_root" checkout "openspec/$change_name" >/dev/null 2>&1
```

Line 228: Redirect status to stderr
```bash
echo "⚡ 轻量模式: 已切换到 openspec/$change_name, 跳过 worktree" >&2
```

After fix, stdout = only path (matching worktree mode line 221 behavior).
