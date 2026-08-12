# Tasks: add-post-flow-analysis

## 1. Classifier 核心（`_lib/post_flow_analysis.py`）— TDD 先行

- [ ] 1.1 写 failing test: `PhaseOutcome` dataclass 接受 phase/exit_code/stderr/stdout_tail/traceback
- [ ] 1.2 写 failing test: `classify_phase_outcome` exit_code=0 → OK 不报告
- [ ] 1.3 写 failing test: exit_code=2 + stderr 含 "unrecognized arguments" → usage-error (U1)
- [ ] 1.4 写 failing test: exit_code=2 + stderr 含 "missing required flag" → usage-error (U4)
- [ ] 1.5 写 failing test: stderr 含 "command not found" + 缺 `gh` → environment-error (E1)
- [ ] 1.6 写 failing test: stderr 含 "Permission denied" + path 在项目外 → environment-error (E2)
- [ ] 1.7 写 failing test: stderr 含 "No space left on device" → environment-error (E4)
- [ ] 1.8 写 failing test: stderr 含 Traceback + 帧在 `_lib/` → flow-bug (F1, fine-grained: phase-crash)
- [ ] 1.9 写 failing test: stderr 含 "invalid state" → flow-bug (F3)
- [ ] 1.10 写 failing test: exit_code=1 + stderr 空 + 任何 U/E 都不匹配 → DEFAULT-FAIL-OPEN → flow-bug
- [ ] 1.11 写 failing test: exit_code=130 (SIGINT) → 不分类、不报告
- [ ] 1.12 写 failing test: exit_code=143 (SIGTERM) → 不分类、不报告
- [ ] 1.13 写 failing test: stderr 含 Traceback 但帧全在 stdlib/argparse → usage, 不 flow
- [ ] 1.14 写 failing test: stderr 含 "状态机" → flow-bug (F3 中文版)
- [ ] 1.15 写 failing test: `report_flow_bug` 调 `detect_issue` + `write_issue_file` + 条件 L2
- [ ] 1.16 实现 `_lib/post_flow_analysis.py`（含 `PhaseOutcome` / `Classification` dataclass + `classify_phase_outcome` + `report_flow_bug` + pattern 表）
- [ ] 1.17 跑测试，验证 15/15 pass

## 2. Script 平面 bash trap

- [ ] 2.1 写 failing bats test: 触发 ERR trap，验证 python3 classifier 被调用
- [ ] 2.2 写 failing bats test: trap 失败 (`|| true`)，不阻断 phase
- [ ] 2.3 写 failing bats test: 显式 `run_with_analysis` 包装 helper，验证 stderr 文件传递
- [ ] 2.4 写 failing bats test: 缺 `gh` 时 → environment-error，不写 issue
- [ ] 2.5 写 failing bats test: Traceback in `_lib/` → phase-crash，写 issue
- [ ] 2.6 写 failing bats test: exit 130 → 不分类
- [ ] 2.7 实现 `skills/_lib/post_flow_wrap.sh`（含 `post_flow_on_err()` + `run_with_analysis`）
- [ ] 2.8 跑测试，验证 6/6 pass

## 3. 接入 4 个 phase entry 脚本

- [ ] 3.1 修改 `skills/guide-arch/scripts/arch_env_check.sh`：加 1 行 `export RDDF_PHASE="guide-arch"` + 1 行 trap
- [ ] 3.2 修改 `skills/guide-plan/scripts/plan_intake.sh`：加 RDDF_PHASE=guide-plan + trap
- [ ] 3.3 修改 `skills/guide-ship/scripts/ship_plan.sh`：加 RDDF_PHASE=guide-ship + trap
- [ ] 3.4 修改 `skills/execute/scripts/execute_entry.sh`（如不存在则创建）：加 RDDF_PHASE=execute + trap
- [ ] 3.5 跑现有 phase 测试，验证 trap 不破坏 phase 行为

## 4. CLI handlers

- [ ] 4.1 新建 `_lib/cli/report_issue_cmd.py`：`report_issue_cmd(description, category, phase)` → 调 `detect_issue` + `write_issue_file` + 可选 L2
- [ ] 4.2 新建 `_lib/cli/issue_cmd.py`：实现 `issue_submit_cmd` / `issue_list_cmd` / `issue_show_cmd`
- [ ] 4.3 修改 `_lib/cli/__init__.py` 路由表：注册 `report-issue` / `issue` 子命令
- [ ] 4.4 写 failing test: `rddf report-issue "foo"` 调 `report_issue_cmd("foo")`
- [ ] 4.5 写 failing test: `rddf issue submit <file>` 提交
- [ ] 4.6 写 failing test: `rddf issue list` 列出
- [ ] 4.7 写 failing test: `rddf issue show <hash>` 显示
- [ ] 4.8 跑测试，验证 4/4 pass

## 5. Agent 平面 SKILL.md 指令

- [ ] 5.1 修改 `skills/guide-arch/SKILL.md`：加 "Phase Exit — Post-Flow Analysis" 段
- [ ] 5.2 修改 `skills/guide-plan/SKILL.md`：加同段
- [ ] 5.3 修改 `skills/guide-ship/SKILL.md`：加同段
- [ ] 5.4 修改 `skills/execute/SKILL.md`：加同段
- [ ] 5.5 内容：说明 4 类 reportable + 2 类不报告 + manual 命令

## 6. rdd-doctor 边界回归测试

- [ ] 6.1 写 `tests/unit/test_doctor_no_issue_write.py`：mock rdd-doctor，验证不调 reporter
- [ ] 6.2 写 bats test: 真实跑 rdd-doctor，验证 `.rddf/issues/` 计数不变
- [ ] 6.3 跑测试，验证通过

## 7. 集成验证

- [ ] 7.1 跑 `./test.sh --unit` 全部通过（≥24 new cases + baseline 1436）
- [ ] 7.2 跑 `./test.sh --integration` 全部通过
- [ ] 7.3 跑 `openspec validate add-post-flow-analysis --type change --json` 0 errors
- [ ] 7.4 手动 verify：模拟 trigger，验证 issue file 出现在 `.rddf/issues/`
- [ ] 7.5 手动 verify：两个 canary（archive_change 零 commits + rddf validate --bogus-flag）

## 8. Commit + archive

- [ ] 8.1 `git add _lib/post_flow_analysis.py skills/_lib/post_flow_wrap.sh _lib/cli/ tests/unit/test_post_flow_analysis.py tests/integration/test_post_flow_wrap.bats tests/unit/test_doctor_no_issue_write.py tests/unit/test_cli_reporter.py skills/guide-arch/scripts/ skills/guide-plan/scripts/ skills/guide-ship/scripts/ skills/guide-arch/SKILL.md skills/guide-plan/SKILL.md skills/guide-ship/SKILL.md skills/execute/SKILL.md`
- [ ] 8.2 `git commit -m "feat(reporter): add post-flow-analysis classifier + two-plane trigger

Implements ADR-0027 §1.0-1.2:
- Classifier: _lib/post_flow_analysis.py with 3-way judgment (usage→env→flow-bug)
- Script plane: bash trap post_flow_wrap.sh wired into 4 phase entry scripts
- Agent plane: 'Phase Exit' section in 4 SKILL.md files (manual rddf report-issue)
- CLI: rddf report-issue + rddf issue {submit,list,show}
- rdd-doctor boundary regression test (doctor never writes to .rddf/issues/)

TDD: ≥24 new test cases, 0 regression."`
- [ ] 8.3 `openspec archive add-post-flow-analysis --yes`
