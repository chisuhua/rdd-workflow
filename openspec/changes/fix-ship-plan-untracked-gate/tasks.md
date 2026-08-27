# fix-ship-plan-untracked-gate — Implementation Tasks

## Implementation Tasks

- [x] Task 1: `check_artifacts_committed` 改用 porcelain XY prefix 区分 tracked vs untracked
- [x] Task 2: 仍阻塞 tracked 文件 modification / deletion (verified: exit 1, stderr 明确指出)
- [x] Task 3: 不阻塞 untracked 文件 (verified: exit 0, stderr 提示 informational)
- [x] Task 4: 提供 `--strict-untracked` positional arg + `STRICT_UNTRACKED=yes` env var 兼容极端场景
- [x] Task 5: stderr 输出明确区分 "tracked dirty" vs "untracked addition"
- [x] Task 6: 新增 bats test `test_check_artifacts_untracked_gate.bats` (7 cases, all pass)
