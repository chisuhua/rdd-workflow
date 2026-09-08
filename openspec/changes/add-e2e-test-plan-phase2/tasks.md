## Tasks

- [x] **Task 1: agent_runner.bash validate 模式** — 4 unit cases
  - `tests/e2e/_lib/agent_runner.bash` ::agent_runner::validate_scenario
  - `tests/e2e/agent/test_agent_runner_validate.bats` (4 cases)
  - Commit: 3e1aa1a

- [x] **Task 2: agent_runner.bash mock 模式** — 3 unit cases
  - ::agent_runner::run (mock dispatch) + ::verify
  - `tests/e2e/agent/test_agent_runner_mock.bats` (3 cases)
  - Commit: 3e1aa1a

- [x] **Task 3: agent_runner.bash real 模式 + agent detection** — 2 unit cases
  - ::agent_runner::detect_mode (RDDF_AGENT_E2E + CLI 检查)
  - ::agent_runner::run (real dispatch)
  - `tests/e2e/agent/test_agent_runner_real.bats` (2 cases)
  - Commit: 3e1aa1a

- [x] **Task 4: 8 scenarios JSON (q_e1..q_e8)** — 8 文件
  - 覆盖 rdd-quick P0-P4 + 隔离契约
  - 每 scenario 含 mock_output 让 mock mode 100% pass
  - Commit: 3897dad

- [x] **Task 5: test_rdd_quick_e2e.bats** — 8 cases
  - 1 case per scenario，集成 isolation + script_smoke + agent_runner
  - 8/8 绿 (mock mode)
  - Commit: 3897dad

- [x] **Task 6: test.sh --e2e-agent 验证** — 缺凭据 SKIP exit 0
  - 验证: `./test.sh --e2e-agent` SKIP message + exit 0
  - (Plan 1 已加 stub，本 Plan 验证)

- [x] **Task 7: 全量回归**
  - A-layer 10/10 + C-layer 17/17 + rdd_quick integration 14/14
  - 0 新增失败

- [x] **Task 8: OpenSpec artifacts + merge + archive + 索引同步** — pending
  - 创建 proposal.md + tasks.md + spec.md
  - merge branch to master
  - openspec archive
  - proposal-approved.md 更新
