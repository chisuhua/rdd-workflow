# Tasks for reduce-rdd-workflow-tool-call-friction

> TDD 5 步结构: 写失败测试 → 验证失败 → 实现 → 验证通过 → commit. 遵循 rdd-workflow 通用纪律.

## 1. 创建 `skills/_lib/AGENT_TOOL_USAGE.md`

- [x] **1.1 写失败的内容审查 test**: `test_agent_tool_usage_doc_exists_in_skills_lib` 断言 `skills/_lib/AGENT_TOOL_USAGE.md` 存在且含 3 个决策树段 (edit / write / read-offset)
- [x] **1.2 验证测试 fail**: 跑 pytest 看到 fail
- [x] **1.3 创建文件**:含 edit 决策树(3 行: any-existing → edit; full-rewrite → write; 已存在文件禁止 write)、write 决策树、read-offset 决策树(强调先 Read 确认行数)
- [x] **1.4 验证测试 pass**: pytest 通过
- [x] **1.5 commit**: `docs(_lib): add AGENT_TOOL_USAGE.md with tool selection decision tree`

## 2. 创建 `skills/rdd-workflow-brainstorm/scripts/pre_tool_use_check.sh`

- [x] **2.1 写失败的 bash test** (bats): `test_pre_tool_check_warns_on_stale_string` 模拟 Read 1 小时前文件 + 立即 edit,断言 stderr 含 "STALE-LIKELY" 警告
- [x] **2.2 验证 test fail**
- [x] **2.3 实现脚本** (bash): 接收 tool name + args,触 3 类规则 (stale-string / write-existing-file / hardcoded-read-offset),命中时 stderr 输出 1 行 brief 并 exit 0 (warn-only 不阻断)
- [x] **2.4 验证 test pass**
- [x] **2.5 commit**: `feat(brainstorm): add pre_tool_use_check.sh with 3 stale-pattern heuristics`

## 3. 创建 `tests/integration/test_tool_friction_regression.py`

- [x] **3.1 编写 7 个 test cases**,每个对应一个实测 tool error:
  - `test_edit_oldstring_mismatch_triggers_read_fallback`
  - `test_write_existing_file_triggers_edit_or_read_write`
  - `test_read_hardcoded_offset_triggers_dynamic_offset`
  - `test_edit_after_read_under_5s_no_warning`
  - `test_write_new_file_no_warning`
  - `test_read_with_offset_after_documented_count_no_warning`
  - `test_repeated_identical_tool_call_collapses_to_single_warning` (避免 spam)
- [x] **3.2 验证 7 个 test 初始 fail** (基线: 还没有 fallback 路径时)
- [x] **3.3 在 `pre_tool_use_check.sh` 中实现对应 fallback 提示**(基于 docstring + stderr hint)
- [x] **3.4 验证 7 个 test pass**
- [x] **3.5 commit**: `test(tool-friction): add 7 regression cases for Agent tool-call fallbacks`

## 4. 端到端复测 1 个 5 阶段流程

- [x] **4.1 选取归档的 `phase-1-general-20260829063800` 作为复测样本**(已 archived, 有完整 plan)
- [x] **4.2 跑 `./test.sh --full`**:确认 0 个 tool error 出现
- [x] **4.3 (若有)记录任何剩余 error 到 proposal.md ## Impact 备注**
- [x] **4.4 commit**: `chore(regression): log 5-phase e2e tool error count = N`

## 5. 文档化 + Review

- [x] **5.1 更新 `.rddf/state/iteration.json`**:status proposed → ready_for_review
- [x] **5.2 在 PR description 中 link proposal.md + AC 4 项**
- [x] **5.3 通知 1 名 reviewer**:@chisuhua 或其他 maintainer
