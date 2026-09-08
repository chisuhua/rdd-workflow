# rdd-builder e2e 测试场景 spec

> **日期**: 2026-09-08
> **所属**: `2026-09-08-e2e-test-plan-design.md` v1
> **覆盖 skill**: `rdd-builder`（per spec §3.4，6-phase 内部状态机 P0/P1/P1.5/P2/P2.5/P3）
> **scenario 数**: 12（B-E1..B-E12）

## 0. 通用约定

详见 `2026-09-08-rdd-quick-e2e-scenarios.md` §0 通用约定字段定义。本 spec 复用。

**rdd-builder 专属约定**：
- 6 个 phase 脚本入口：`skills/rdd-builder/scripts/phase{0,1,1_5,2,2_5,3}_*.sh`
- 非交互 flag：每个 phase 脚本需支持 `--auto-approve` / `--no-confirm`（per 设计 §3.2，writing-plans 阶段实施）
- handoff 契约：`.rddf/state/builder/<name>.json` v1 schema
- worktree 路径：`.rddf/wt/<name>/`
- 默认分支：`find_default_branch()` 动态检测

## B-E1: P0 approval happy → D3 spec-delta 落盘

| 字段 | 内容 |
|------|------|
| 入口 | A 层：`bash skills/rdd-builder/scripts/phase0_approval.sh "e2e-b1" --auto-approve`；C 层：agent prompt 走 P0 |
| 预期产物 | `openspec/changes/e2e-b1/specs/e2e-b1/spec.md` 存在；段头 `## ADDED Requirements`（per D3 协同 + openspec v1.4 强制） |
| 必清状态 | `openspec/changes/e2e-b1/` 仅 spec.md（无 archive move）；iteration.json `e2e-b1.status="proposed"` |
| AC 断言 | spec.md 段头匹配 `^## ADDED Requirements$`；含 ≥1 `### Requirement: <name>` 段；proposal.md 段头英文 D2 输出 |
| 隔离规则 | `setup_fake_project` 含 git init + openspec init；teardown 全清 |
| 备注 | 现有 `test_rdd_builder_phases.bats` 测脚本存在；本 case 测 D3 真落盘 + spec.md schema 合规 |

## B-E2: P0 reject → exit 1 + planner-feedback 写入

| 字段 | 内容 |
|------|------|
| 入口 | agent prompt 走 P0；故意传 broken proposal（含 1 个矛盾 AC + 1 个空 capability） |
| 预期产物 | exit code 1；`.rddf/state/.planner-feedback.json` 含 `change=e2e-b2, kind=reject, reason=<具体>` |
| 必清状态 | `openspec/changes/e2e-b2/` 仅有 proposal.md（无 spec.md）；feedback json 含 reject 行 |
| AC 断言 | phase0 exit 1；feedback json 数组含 `e2e-b2`；reason 字段非空 |
| 隔离规则 | 同 B-E1 |
| 备注 | per spec §3.4 P0 reject exit code 1；与 archive 的 exit code 5（review revise）区分 |

## B-E3: P1 plan gen → TDD 5 步 plan 文件

| 字段 | 内容 |
|------|------|
| 入口 | A 层：`bash skills/rdd-builder/scripts/phase1_plan.sh "e2e-b3" --auto-approve`；C 层：agent prompt 走 P1 |
| 预期产物 | `.rddf/plans/e2e-b3.md` 存在；含 5 TDD marker + `## Acceptance` ≥1 AC |
| 必清状态 | `openspec/changes/e2e-b3/` 不动（plan 写 `.rddf/plans/`，per docs/superpowers/specs/2026-08-05-guide-ship-execution-contract.md） |
| AC 断言 | plan 含 5 step 标题 + ≥1 AC checkbox；与 `rdd-workflow-writing-plans` 输出格式一致 |
| 隔离规则 | 同 B-E1 |
| 备注 | 现有契约测试只测"脚本存在"；本 case 测 plan 真生成 + 格式合规 |

## B-E4: P1.5 deps 分析 + execution_mode 决策

| 字段 | 内容 |
|------|------|
| 入口 | 接 B-E3；`bash skills/rdd-builder/scripts/phase1_5_deps.sh "e2e-b4" --auto-approve` |
| 预期产物 | `.rddf/state/deps-analysis.json` 写入；`.rddf/state/.plan-handoff.json::execution_mode_decisions` 含决策；`.rddf/state/deps-output.md` 人类可读报告 |
| 必清状态 | handoff json `schema=plan-handoff-v1`；mode ∈ {lightweight, worktree} |
| AC 断言 | deps-analysis.json 合 schema v2.0.1；mode 决策字段非空且 ∈ 合法 enum |
| 隔离规则 | 同 B-E1 |
| 备注 | per ADR-0024 deps-driven execution mode 决策 |

## B-E5: P1.5 风险关键词 → worktree 模式

| 字段 | 内容 |
|------|------|
| 入口 | 接 B-E4；proposal.md 含 `keywords: [refactor, migration, multi-file]` |
| 预期产物 | handoff json `execution_mode_decisions[0].mode="worktree"`，reason 字段含 "risk keyword" |
| 必清状态 | `.rddf/wt/` 不变（决策产生但未执行） |
| AC 断言 | mode="worktree"；reason 字符串含 "refactor" 或 "risk" |
| 隔离规则 | 同 B-E1 |
| 备注 | 验证 ADR-0024 风险关键词分流规则 |

## B-E6: P2 lightweight 模式 → 主仓 commit

| 字段 | 内容 |
|------|------|
| 入口 | 接 B-E4 + 强制 mode=lightweight；agent prompt 走 P2 |
| 预期产物 | `$FAKE_ROOT/` 含 1 git commit（"feat(e2e-b6): ..."）；无 `.rddf/wt/e2e-b6/` |
| 必清状态 | commit count == 1；worktree 路径不存在 |
| AC 断言 | `git log -1` message 匹配 `^(feat|fix|refactor)\(e2e-b6\)`；`.rddf/wt/e2e-b6/` 不存在 |
| 隔离规则 | 同 B-E1 |
| 备注 | per AGENTS.md "Worktree Commit Flow" 第 2 步：轻量模式在主仓聚合 commit |

## B-E7: P2 worktree 模式 → 隔离 commit

| 字段 | 内容 |
|------|------|
| 入口 | 接 B-E5（mode=worktree）；agent prompt 走 P2 |
| 预期产物 | `.rddf/wt/e2e-b7/` 存在；`branch=openspec/e2e-b7` 含 ≥1 commit；主仓不增 commit |
| 必清状态 | worktree HEAD 领先主仓 ≥1 commit；branch 与主仓 `find_default_branch()` 关系明确 |
| AC 断言 | `git -C .rddf/wt/e2e-b7 log -1` 含 "e2e-b7"；`git log` 主仓未变 |
| 隔离规则 | 同 B-E1 |
| 备注 | 验证 worktree 模式机械正确性；与 B-E6 互补 |

## B-E8: P2.5 review 4-option dispatch

| 字段 | 内容 |
|------|------|
| 入口 | 接 B-E6 / B-E7；agent 选择 "merge" 选项 |
| 预期产物 | `_lib/review_action.sh::handle_review_action` 被调；branch 合 `find_default_branch()`；iteration.json `e2e-b8.status="reviewed"` |
| 必清状态 | review action 走通；branch 仍在（待 P3 清理） |
| AC 断言 | `handle_review_action` 4-option 中选 "merge"；主仓 HEAD 变化；status="reviewed" |
| 隔离规则 | 同 B-E1 |
| 备注 | 4-option dispatch per `skills/_lib/ship_review.sh` 提取文档 |

## B-E9: P3 archive happy path

| 字段 | 内容 |
|------|------|
| 入口 | 接 B-E8（merge 完）；`bash skills/rdd-builder/scripts/phase3_archive.sh "e2e-b9" --auto-approve` |
| 预期产物 | `openspec/changes/e2e-b9/` 移至 `openspec/changes/archive/<date>-e2e-b9/`；iteration.json `status="archived"` + `archived_at` + `archive_commit_sha` |
| 必清状态 | active change 目录消失；specs 落 `openspec/specs/e2e-b9/spec.md` |
| AC 断言 | `openspec/changes/e2e-b9/` 不存在；archive 目录含 e2e-b9；iteration 3 字段齐全 |
| 隔离规则 | 同 B-E1 |
| 备注 | per spec §3.4 P3 archive 终态；与现有 `test_full_workflow_e2e.bats` 3/7 case 重复但更深 |

## B-E10: P3 archive gate 阻断 — 0 commits

| 字段 | 内容 |
|------|------|
| 入口 | 接 B-E8 但故意不让 P2 commit（mock agent skip TDD step 5） |
| 预期产物 | phase3 exit code 1；stderr 含 "0 new commits" 或 "check_worktree_commits" 错误 |
| 必清状态 | `openspec/changes/e2e-b10/` 仍在 active（未 archive） |
| AC 断言 | exit 1；stderr 匹配 0 commits 错误模板；active dir 存在 |
| 隔离规则 | 同 B-E1 |
| 备注 | per AGENTS.md "Worktree Commit Flow" 第 2 步 + `_lib/archive.sh::check_worktree_commits` |

## B-E11: P3 → P1 verifier 失败回环

| 字段 | 内容 |
|------|------|
| 入口 | 接 B-E9 但故意让 AC 验证 fail（plan 写 AC 真实不通过） |
| 预期产物 | phase3 exit code 4（verifier halt per spec §3.4）；`.plan-handoff.json` 含 `back_routing_trail` 指向 P1 |
| 必清状态 | change 不 archive；retry_count=1；next_phase="phase-1" |
| AC 断言 | exit 4；handoff trail 含 "phase-1"；`retry_count < RDDF_BUILDER_MAX_RETRIES=3` |
| 隔离规则 | 同 B-E1 |
| 备注 | per spec §3.4 P3 → P1 重路由 + max 3 retry；verifier 失败回环核心机制 |

## B-E12: 隔离契约 — 不污染 rdd-quick 路径

| 字段 | 内容 |
|------|------|
| 入口 | 真跑 B-E1..B-E11 后，扫 `$FAKE_ROOT/.rddf/plans/quick-*.md` |
| 预期产物 | 11 个 scenario 全部无 `quick-*.md` 产出 |
| 必清状态 | `.rddf/plans/` 仅含 `<name>.md`，无 `quick-<name>.md` |
| AC 断言 | `find .rddf/plans -name "quick-*" -type f` 输出为空 |
| 隔离规则 | meta-测试 |
| 备注 | 双向零污染：本 spec 不污染 rdd-quick 路径；rdd-quick spec（Q-E8）反向验证 |

## 覆盖矩阵

| builder 内部 phase | 覆盖 scenarios |
|--------------------|----------------|
| P0 approval | B-E1, B-E2 |
| P1 plan | B-E3 |
| P1.5 deps + exec_mode | B-E4, B-E5 |
| P2 execute | B-E6, B-E7 |
| P2.5 review | B-E8 |
| P3 archive | B-E9, B-E10 |
| Verifier 回环 | B-E11 |
| 隔离契约 | B-E12 |

## 与现有 26 cases 的关系

- `tests/unit/test_builder_*.py`（9）：保留，单元层
- `tests/integration/test_rdd_builder_phases.bats`（19）：保留，契约/结构层
- `tests/integration/test_full_workflow_e2e.bats`（7）：保留，但 #3/7 需重构去掉 env-var shim（让 invoke_builder_phases 真调 phase 脚本）
- `tests/e2e/agent/test_rdd_builder_e2e.bats`（12，本 spec）：新增，prose UX 真 e2e

总计 38 cases 覆盖 rdd-builder（26 旧 + 12 新），分层无重叠。
