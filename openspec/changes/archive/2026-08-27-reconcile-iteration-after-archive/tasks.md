# reconcile-iteration-after-archive — Implementation Tasks

## Implementation Tasks

- [x] Task 1: `reconcile-iteration.sh` 脚本实现
- [x] Task 2: 3 个 P1 changes 在 iteration.json 中 status='archived',tasks_done=tasks_total
- [x] Task 3: 备份文件存在 `.rddf/state/.before-reconcile/iteration.json.before-reconcile-2026-08-27`
- [x] Task 4: `rddf rdd-verify --dry-run` 不再返回 empty queue (archived 状态自动排除 verify 队列)
- [x] Task 5: 不修改 archive/ 子目录的任何文件
- [x] Task 6: Run `bash tests/scripts/report_regression.sh` to confirm no new failures
