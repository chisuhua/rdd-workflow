# auto-archive-iteration-and-commit — Implementation Tasks

## Implementation Tasks

- [x] Task 1: `archive_change_smart.sh` 一键完成 detect mode + archive + iteration sync + commit archive moves + branch cleanup
- [x] Task 2: iteration.json 自动 `status=archived` + `tasks_done=tasks_total`
- [x] Task 3: archive moves 自动 commit (subject: `archive(<name>): archive completed`)
- [x] Task 4: 6 个 bats test 全部通过
- [x] Task 5: AI agent 调用此 helper 后不需任何 follow-up 操作
- [x] Task 6: `bash tests/scripts/report_regression.sh` 不增加新 failure