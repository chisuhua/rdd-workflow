# improve-commit-scope-discipline — Implementation Tasks

## Implementation Tasks

- [x] Task 1: 新增 `git_safety_check.sh` helper 在 `skills/guide-ship/scripts/`
- [x] Task 2: `git_safety_check.sh` 检查 pre-existing tracked dirty (默认 WARNING, exit 0)
- [x] Task 3: 提供 `STRICT_COMMIT_SCOPE=yes` env var 升级为 block (exit 1)
- [x] Task 4: 提供 `--strict` CLI flag 等价于 STRICT_COMMIT_SCOPE=yes
- [x] Task 5: 不阻止 commit (WARNING 级, user 可选继续)
- [x] Task 6: 不破坏现有正常 ship flow (完全干净或仅 untracked → exit 0 PASS)
- [x] Task 7: 新增 bats 测试 `test_git_safety_check.bats` (6 cases, all pass)
