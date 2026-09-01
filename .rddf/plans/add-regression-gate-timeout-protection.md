# add-regression-gate-timeout-protection Implementation Plan

**Goal**: 回归门 `./test.sh --full --regression` 加 `--max-duration` 超时 + bats 进度透传 + 部分结果保存。

**Approach**: test.sh 新增 `--max-duration=N` flag 用 `timeout` 命令包裹 bats 调用 + bats `--report-formatter tap13` 让 stdout 实时输出。

## Tasks

### Task 1: test.sh 加 --max-duration flag

- [ ] **Step 1**: 修改 test.sh 新增 `--max-duration=N` flag 解析
- [ ] **Step 2**: 用 `timeout` 包裹 bats 调用,超时保存 partial 结果
- [ ] **Step 3**: 跑 `./test.sh --help` 验证 flag 解析
- [ ] **Step 4**: 跑 `./test.sh --max-duration=5 --unit` 验证 5s 超时(会 fail 因为时间太短但 graceful)
- [ ] **Step 5**: Defer commit

### Task 2: 文档 + tasks + commit + archive
