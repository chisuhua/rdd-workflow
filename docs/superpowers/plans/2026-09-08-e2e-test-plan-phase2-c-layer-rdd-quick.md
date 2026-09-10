# Plan 2: C 层基础设施 + rdd-quick 试点

> **日期**: 2026-09-08
> **所属**: `2026-09-08-e2e-test-plan-design.md` §9 Phase 2
> **目标**: 实施 agent_runner.bash 框架 + 8 个 rdd-quick C-layer scenarios + 8 test cases
> **承接**: Plan 1（已落 3 helpers + 10 A-layer cases + 6 phase flags + test.sh 3 modes）

## 1. 背景

Plan 1 已落 A-layer（CI 必跑，10 cases）。A-layer 验证 phase 脚本的机械正确性，但 prose UX（agent 真读 SKILL.md 走状态机）未覆盖。

本 Plan 引入 C-layer 框架：agent_runner.bash 调度 + 8 scenarios（rdd-quick P0-P4 全链路）+ 8 bats cases。验证 prose UX 真跑通 rdd-quick，再 Plan 3 推广到 4 skill。

## 2. 关键决策

### 2.1 agent_runner.bash 三模式

| Mode | 触发 | 行为 | CI 是否必跑 |
|------|------|------|------------|
| `validate` | 默认 | 仅校验 scenarios/*.json + golden 字段齐全 | ✅ |
| `mock` | `AGENT_RUNNER_MODE=mock` 或无 agent CLI | 用 scenario JSON 内置的 `mock_output` 段 | ✅ |
| `real` | `RDDF_AGENT_E2E=1` + `which opencode` 命中 | 调 `opencode --prompt "..."` 真跑 | ⚠️ nightly |

**C-layer 8 cases 在 CI 通过 validate+mock 模式"全绿"；nightly 跑 real 模式做 prose drift 真实检测。**

### 2.2 Scenario JSON Schema

每 scenario 含：
- `scenario_id` (Q-E1..Q-E8)
- `skill` (rdd-quick / rdd-builder / ...)
- `input`: 调脚本命令 / agent prompt / 环境变量
- `golden_output`: 关键文件存在 + 关键字段值 + stdout 段
- `isolation`: locked_paths 列表
- `mock_output`: mock mode 用的预录输出（每个 case 必填，覆盖 100% 真实响应）

### 2.3 TDD 5 步纪律

每 helper / scenario / bats case 走标准 TDD：
1. Write failing test（先有 bats 红）
2. Verify fail（跑 test 确认 fail 原因）
3. Implement（写最小 helper / scenario）
4. Verify pass（重跑 test 确认绿）
5. Commit（per Plan 1 worktree commit 流程；轻量模式聚合 1 commit）

## 3. 任务清单（Plan 2 共 8 tasks）

### Task 1: agent_runner.bash — validate 模式

**写 test**: `tests/e2e/agent/test_agent_runner_validate.bats` (4 cases)
- T1: validate 模式检测 schema 缺失字段返回非 0
- T2: validate 模式通过合法 scenario 返回 0
- T3: validate 模式返回 SKIP 信号当 scenario 文件不存在
- T4: validate 模式支持 4 必需字段（scenario_id / skill / input / golden_output）

**写 impl**: `tests/e2e/_lib/agent_runner.bash` (~120 行)
- `agent_runner::validate_scenario <scenario.json>`
- `agent_runner::detect_mode` (env-var priority: RDDF_AGENT_E2E > AGENT_RUNNER_MODE > validate)
- `agent_runner::should_skip` (0 = run, 1 = skip)
- `agent_runner::run <scenario.json> <output_dir>` (dispatch by mode)
- `agent_runner::verify <actual_dir> <scenario.json>` (golden_output 比对)

**验证**: 4/4 绿

### Task 2: agent_runner.bash — mock 模式

**写 test**: `tests/e2e/agent/test_agent_runner_mock.bats` (3 cases)
- T5: mock 模式从 scenario.mock_output 读预录 output
- T6: mock 模式 + validate 模式串行：先 validate 后 mock
- T7: mock 模式 exit 0 当 mock_output 匹配 golden_output

**写 impl**: 扩 agent_runner.bash 加 mock dispatch
- `agent_runner::run_mock <scenario.json> <output_dir>` — 复制 mock_output 到 output_dir
- `agent_runner::verify <output_dir> <scenario.json>` — 比对 key fields

**验证**: 3/3 绿

### Task 3: agent_runner.bash — real 模式 + agent detection

**写 test**: `tests/e2e/agent/test_agent_runner_real.bats` (2 cases)
- T8: real 模式 + RDDF_AGENT_E2E=1 + which opencode 失败 → 退化 mock
- T9: real 模式 + RDDF_AGENT_E2E=1 + which opencode 成功 → 调 opencode CLI

**写 impl**: 扩 agent_runner.bash 加 real dispatch
- `agent_runner::detect_agent_cli` — `which opencode || which claude || which codex`
- `agent_runner::run_real <scenario.json> <output_dir>` — `cd <fake_root> && <cli> --prompt <prompt>`

**验证**: 2/2 绿（默认 mock 命中；real 模式用 stub `opencode` 验）

### Task 4: 8 scenarios JSON (q_e1..q_e8)

**写**: `tests/e2e/agent/scenarios/{q_e1,q_e2,q_e3,q_e4,q_e5,q_e6,q_e7,q_e8}.json`

每个 JSON 含：
- scenario_id / skill / input / golden_output / mock_output / isolation
- mock_output 段是关键：用预录数据覆盖 100% 真实响应
- isolation.locked_paths 6 路径（per Plan 1）

**验证**: `agent_runner::validate_scenario` 8/8 通过

### Task 5: test_rdd_quick_e2e.bats — 8 cases

**写**: `tests/e2e/agent/test_rdd_quick_e2e.bats` (8 cases，1 per scenario)

每 case 模板：
```bash
@test "rdd-quick: Q-E1 P0 简单提案 → 脚手架 plan" {
    load_lib isolation
    load_lib script_smoke
    load_lib agent_runner

    local scenario="$BATS_TEST_DIRNAME/scenarios/q_e1.json"
    local fake_root="$BATS_TEST_TMPDIR/fake-project"
    setup_fake_project "$fake_root"
    lock_isolation_paths "$fake_root"

    agent_runner::should_skip && skip "agent runner skipped (validate/mock only)"

    agent_runner::run "$scenario" "$fake_root"
    agent_runner::verify "$fake_root" "$scenario"

    verify_zero_pollution
    teardown_fake_project "$fake_root"
}
```

**验证**: 8/8 绿（CI mock mode；nightly real mode 需 RDDF_AGENT_E2E=1）

### Task 6: test.sh — 扩展 --e2e-agent 模式

**写 impl**: `test.sh` 加 `--e2e-agent` 模式（Plan 1 已加 stub，需实跑）
- 检测 `RDDF_AGENT_E2E=1` env var
- 缺凭据 → SKIP 退出 0（不 fail）
- 有凭据 → 跑 `tests/e2e/agent/`

**验证**: `./test.sh --e2e-agent` 缺凭据时 exit 0 + 显式 SKIP 消息

### Task 7: 全量回归 + baseline sync

- 跑 `./test.sh --full --regression`
- 对比 baseline 6 个失败：1 planner_feedback 5× + 1 test_deps_execution_mode 1×（per Plan 1）
- 新增失败（如有）→ 修或加 KNOWN_FAILURES
- 无新增失败 → 进 Task 8

**验证**: 0 新增失败

### Task 8: OpenSpec artifacts + merge + archive + 索引同步

- `openspec/changes/add-e2e-test-plan-phase2/{proposal,tasks}.md` + `specs/c-layer-agent-runner/spec.md`
- merge branch to master (聚合 1 commit)
- `openspec archive add-e2e-test-plan-phase2 --yes`
- improvement-approved.md 加 add-e2e-test-plan-phase2 entry
- `git branch -d openspec/add-e2e-test-plan-phase2`

**验证**: master log 含 Plan 2 commit + 1 archive commit + 1 index commit

## 4. 验收标准

| # | 验收项 | 测量 |
|---|--------|------|
| AC-1 | agent_runner.bash 三模式 (validate/mock/real) 全实现 | 9 bats case 全绿 |
| AC-2 | 8 scenarios JSON schema 合法 | agent_runner::validate_scenario 8/8 绿 |
| AC-3 | 8 test_rdd_quick_e2e cases 跑通 mock 模式 | 8/8 绿 |
| AC-4 | test.sh --e2e-agent 缺凭据 SKIP exit 0 | 验证 |
| AC-5 | 0 新增回归失败 | ./test.sh --full --regression |
| AC-6 | OpenSpec archive 完成 | openspec/changes/archive/2026-09-08-add-e2e-test-plan-phase2/ 存在 |

## 5. 风险与缓解

| 风险 | 缓解 |
|------|------|
| Mock output 与真实 agent 输出 drift | mock_output 是 baseline，prose drift 由 nightly real mode 抓 |
| Real mode 调 opencode CLI 超时 | 设 60s timeout，失败 fallback mock + log |
| Scenario JSON schema 漂移 | agent_runner::validate_scenario 单一来源 |

## 6. 交付清单

- `tests/e2e/_lib/agent_runner.bash` (~150 行)
- `tests/e2e/agent/scenarios/q_e{1..8}.json` (8 文件)
- `tests/e2e/agent/test_agent_runner_{validate,mock,real}.bats` (3 文件 / 9 cases)
- `tests/e2e/agent/test_rdd_quick_e2e.bats` (1 文件 / 8 cases)
- `test.sh` 扩展 --e2e-agent 实现（Plan 1 仅 stub）
- `openspec/changes/archive/2026-09-08-add-e2e-test-plan-phase2/` (proposal + tasks + spec)
- `improvement-approved.md` 加 entry
- `.rddf/improvements/add-e2e-test-plan-phase2.md`

## 7. 后续 Plan 入口

- **Plan 3**: 4 skill C-layer（rdd-builder/verifier/arch/planner），共 32 cases
- **Plan 4**: CI 集成（.github/workflows/e2e-nightly.yml + README）
- **Plan 5**: 外部 testbed 协同契约（README + chisuhua/rdd-workflow-e2e 联动）
