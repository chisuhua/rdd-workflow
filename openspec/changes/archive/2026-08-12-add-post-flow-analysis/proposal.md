# add-post-flow-analysis

> **优先级**: P0
> **来源**: ADR-0027 §1 实施（post-flow-analysis 三段式判定 + 两平面架构）
> **前置依赖**: `add-issue-reporter`（必须先合并）
> **关联**: `docs/adr/ADR-0027-continuous-evolution-feedback-loop.md` §1.0 §1.1 §1.2

## Why

ADR-0027 §1 在 Oracle 复核时被发现有架构缺陷：phase 不是统一可执行进程，存在 **script 平面**（execute + per-skill bash 脚本，真实 exit_code/stderr/traceback）和 **agent 平面**（guide-arch/plan/ship SKILL.md，agent 逐轮执行无进程边界）两种根本不同的运行时形态。

当前 ADR §1 文字只覆盖了 script 平面（"phase exit_code != 0"），对 guide-arch/plan/ship 是空头支票 — 没有任何代码路径会调用 classifier。

Oracle 设计的解法（NEEDS-ITERATION，详见 ADR §1 修正后的 §1.0-1.2）：

1. **Script 平面**：bash trap `ERR` 包装器（`skills/_lib/post_flow_wrap.sh`）捕获 exit_code + stderr 文件，调用 `python3 -m _lib.post_flow_analysis`
2. **Agent 平面**：4 个 phase SKILL.md 各加 "Phase Exit" 段，指令 agent 异常结束时调 `rddf report-issue`（agent 自分类，绕开 classifier）
3. **两平面共用** `_lib/post_flow_analysis.classify_phase_outcome` 三段式判定（usage → env → flow-bug，fail-open 默认 flow-bug）

不实施本 change 则 ADR-0027 §1 是空头支票，4 个 phase 中 3 个永远不会被 classifier 处理。

## What Changes

**In Scope**:

- **`_lib/post_flow_analysis.py`** 新建：导出 `classify_phase_outcome(phase, outcome) -> Classification` + `report_flow_bug(classification, project_root, config) -> Path | None` + `analyze_and_report(...)` 便利组合；定义 `PhaseOutcome` 和 `Classification` dataclass；pattern 表（USAGE_PATTERNS / ENV_PATTERNS / FLOW_PATTERNS）。
- **`skills/_lib/post_flow_wrap.sh`** 新建：导出 `post_flow_on_err()`（trap ERR handler） + `run_with_analysis <phase> <cmd...>`（显式包装）；失败时调 `python3 -m _lib.post_flow_analysis --phase X --exit-code N --stderr-file F`；`|| true` 失败容忍。
- **改造 4 个 phase entry 脚本**（1 行 trap + 1 行 export each）：
  - `skills/guide-arch/scripts/arch_env_check.sh`
  - `skills/guide-plan/scripts/plan_intake.sh`
  - `skills/guide-ship/scripts/ship_plan.sh`
  - `skills/execute/scripts/execute_entry.sh`（如不存在则创建）
- **新增 CLI handlers**（`rddf report-issue` + `rddf issue submit/list/show`）：
  - `_lib/cli/report_issue_cmd.py`（manual 类别，绕开 classifier）
  - `_lib/cli/issue_cmd.py`（submit/list/show）
  - 修改 `_lib/cli/__init__.py` 路由表注册
- **改造 4 个 phase SKILL.md**（Agent 平面指令）：每个增加 "Phase Exit — Post-Flow Analysis" 段，说明何时调 `rddf report-issue`。
- **rdd-doctor 边界回归测试**：`tests/unit/test_doctor_no_issue_write.py` 验证 rdd-doctor 跑完不写 `.rddf/issues/`（结构隔离保证）。
- **单元测试**：`tests/unit/test_post_flow_analysis.py` ≥15 cases（每类 ≥3 + 边界）。
- **集成测试**：`tests/integration/test_post_flow_wrap.bats` ≥6 cases（含两个 canary：archive_change 零 commits + rddf validate --bogus-flag）。

**Out of Scope**:

- gate 自身实现（ADR-0007/0018/0019 范围）
- rdd-doctor 改造
- 5 段流之外的扩展（如 declarative flow DSL）
- ADR-0017 冲突解决器扩展
- bats 之外的集成测试格式

### 关键场景

- GIVEN script 平面 trap 触发, WHEN helper exit_code=1 + stderr 含 `Traceback` + 帧在 `_lib/`, THEN classifier → `flow-bug` + 写 `.rddf/issues/phase-crash-<hash>.md`
- GIVEN argparse 拒绝, WHEN exit_code=2 + stderr 含 `unrecognized arguments`, THEN classifier → `usage-error` + UI 提示 + **不**写 issue 文件
- GIVEN 缺 `gh` CLI, WHEN subprocess FileNotFoundError, THEN classifier → `environment-error` + 提示 + **不**写 issue 文件
- GIVEN 任何未匹配失败, WHEN 非 exit 130/143, THEN DEFAULT-FAIL-OPEN → `flow-bug` + 写 issue
- GIVEN exit 130/143 (SIGINT/SIGTERM), THEN 不分类、不上报（用户主动取消）
- GIVEN agent 平面 phase 异常结束, WHEN SKILL.md 指令 agent 调 `rddf report-issue --category flow-bug`, THEN 绕开 classifier 直接写 issue
- GIVEN 同一 incident 被 script trap + agent 手动 report 触发两次, THEN dedup_hash 相同 → 同文件名 → 幂等覆盖

## Capabilities

### 1. Classifier 核心（`_lib/post_flow_analysis.py`）

- MUST 导出 `PhaseOutcome` / `Classification` dataclass
- MUST `classify_phase_outcome` 三段式判定（U → E → F）
- MUST exit_code ∈ {130, 143} 早退不分类
- MUST DEFAULT-FAIL-OPEN: 任何未匹配 → `flow-bug`
- MUST F1（Traceback in `_lib/`）→ fine-grained `phase-crash`
- MUST F4-gate → fine-grained `gate-failure`
- MUST `report_flow_bug` 调 `detect_issue` + `write_issue_file` + 可选 L2
- MUST 复用 `_lib/issue_reporter.py::is_ci_environment` + config namespace 做 L2 gate
- MUST ≥15 unit tests 覆盖每类 ≥3 + 边界

### 2. Script 平面 trap（`skills/_lib/post_flow_wrap.sh`）

- MUST bash 函数 `post_flow_on_err()` 接 exit_code + phase 名
- MUST 调 `python3 -m _lib.post_flow_analysis --phase X --exit-code N --stderr-file F`
- MUST 整个 trap 用 `|| true` 包裹（不阻断 phase 主体）
- MUST 4 个 phase entry 脚本各加 1 行 `trap` + 1 行 `export RDDF_PHASE`
- MUST ≥6 bats 集成测试

### 3. CLI handlers

- MUST `rddf report-issue "<desc>"` 接受描述作为 argv，调 `detect_issue("manual", ...)` + `write_issue_file`
- MUST `rddf issue submit <file>` 提交指定 issue 文件（manual bypass）
- MUST `rddf issue list [--state open|closed|all]` 列出本地 issues
- MUST `rddf issue show <hash>` 显示本地 issue body
- MUST ≥3 unit tests

### 4. Agent 平面 SKILL.md 指令

- MUST 4 个 phase SKILL.md（guide-arch / guide-plan / guide-ship / execute）各加 "Phase Exit — Post-Flow Analysis" 段
- MUST 段说明 4 类 reportable 类别 + 2 类不报告类别 + manual 调 `rddf report-issue` 的命令

### 5. rdd-doctor 边界回归

- MUST `tests/unit/test_doctor_no_issue_write.py` 验证 rdd-doctor 跑完后 `.rddf/issues/` 计数不变
- MUST 防止未来 rdd-doctor 改造时意外接入 reporter

## Impact

- 影响文件：
  - 新增: `_lib/post_flow_analysis.py`（~180 行）
  - 新增: `skills/_lib/post_flow_wrap.sh`（~40 行）
  - 新增: `_lib/cli/report_issue_cmd.py`（~40 行）
  - 新增: `_lib/cli/issue_cmd.py`（~60 行）
  - 修改: 4 个 phase entry 脚本（各 2 行）
  - 修改: 4 个 phase SKILL.md（各 ~10 行）
  - 修改: `_lib/cli/__init__.py`（+10 行路由表）
  - 新增: `tests/unit/test_post_flow_analysis.py`（~200 行）
  - 新增: `tests/integration/test_post_flow_wrap.bats`（~150 行）
  - 新增: `tests/unit/test_doctor_no_issue_write.py`（~40 行）
  - 新增: `tests/unit/test_cli_reporter.py`（~80 行）
- 兼容性：所有现有 phase 行为不变（trap 用 `|| true` 包裹）
- 风险：低 — 纯增量功能 + 失败容忍设计

## Acceptance

- 单元测试 + 集成测试全部通过（≥24 cases new）
- 现有 phase 行为不变（trap 不阻断）
- rdd-doctor 边界保持（不写 `.rddf/issues/`）
- 两平面都有入口（script trap + agent manual）
- `openspec validate add-post-flow-analysis --type change --json` 0 errors
- commit message: `feat(reporter): add post-flow-analysis classifier + two-plane trigger`
