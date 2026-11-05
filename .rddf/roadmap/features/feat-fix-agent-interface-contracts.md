---
id: feat-fix-agent-interface-contracts
kind: feature
status: done
phase_refs: [phase-4]
主题: 对外契约修复（v4 handoff 识别 / owns 可机读 / design.md 归属 / P2 commit gate 删除 / status 暴露 builder phase）
---

## 概述

2026-11-03 的跨仓协作审计发现：opencode 侧 build agent 的角色矩阵已按「自足内核 + rdd-workflow 可选增强层」重构，但增强层的三个接入点——**阶段判定**、**工件归属判定**、**调用可行性判定**——在 rdd-workflow 这一侧各有缺陷。

本 feature 跟踪 5 项接口修复，按用户指定批次分三组：

| 批次 | 提案 | 内容 | 影响面 |
|---|---|---|---|
| 批 1 | #1 `scan-state` v4 handoff | `.planner-handoff.json` 识别 + planner 推荐值修正 + v3 fallback | `skills/guide/scripts/scan-state.sh` |
| 批 1 | #3 `design.md` 归属 | 从 `rdd-builder.owns` 移除（P1 实际不生成） | `skills/rdd-builder/SKILL.md`（1 行） |
| 批 2 | #2 owns 可机读 | 10 处括号注释去除 + schema `pattern` 校验 | 5 个 SKILL.md + schema |
| 批 2 | #5 status 暴露 phase | 总览表 `BUILDER` 列 + 详情 `Builder phase:` | `_lib/cli/status_cmd.py` |
| 批 3 | #4 **删除** P2 COMMIT GATE | 移除整仓 `git status` 检查（不引入新环境变量）；补 3 处既有缺陷 + worktree 未提交产物带出 | `phase2_execute.sh` |

## 动机证据

| Gap | 证据 |
|---|---|
| #1 | `scan-state.sh:118-119` 读 v3 文件名；v4 只有 `rdd-planner` 写 `.planner-handoff.json` |
| #2 | `grep -rn '^\s*-\s*"[^"]*("' skills/*/SKILL.md` = 10 行 |
| #3 | `grep -n design skills/rdd-builder/scripts/phase1_plan.sh` 无输出 |
| #4 | `phase2_execute.sh:24` 用 `git status --porcelain`（整仓） |
| #5 | `_lib/cli/status_cmd.py::_mode_a` 只渲染 4 列 |

## 不做什么

- 不改阶段语义与 handoff 契约
- 不给 skill 前置条件加结构化字段（另案）
- 不改 `rddf doctor` 的 gitignore 覆盖范围（另案）
- 不删除 v3 handoff 支持（仅降级为 fallback）

## 验收

见 `openspec/changes/fix-agent-interface-contracts/proposal.md` 的 20 条 AC + `specs/` 下两组 delta。

**验收结论（2026-11-05）**：20/20 AC pass，证据见 `.rddf/reviews/fix-agent-interface-contracts-verify.md`。

## 实施批次（2026-11-03）

| 批次 | 内容 | 验证 |
|---|---|---|
| commit 1 | #1 三处阶段判定 + #5 `BUILDER` 列 | `tests/unit/test_workflow_synthesizer_planner_path.py`(5) + `test_status_builder_column.py`(5) + scan_state bats(8+17) + e2e 48 |
| commit 2 | #2 owns 机读化 + #3 design.md 归属 | `tests/unit/test_skill_role_schema.py`(10) + 7 个 skill frontmatter 全部通过 schema |
| commit 3 | #4 删除 P2 COMMIT GATE（含 EXEC_MODE 探测修复 + worktree 产物带出） | `tests/integration/test_phase2_commit_gate.bats`(8) |

### critic 评审后的修订（2026-11-04）

critic 判定 REJECT（5 BLOCKERS，`mergeable: no` / `scope_exceeded: true`）。5 个 BLOCKER 全部**独立复现确认**后修复，并补 4 个回归用例：

| BLOCKER | 修复 | 回归用例 |
|---|---|---|
| `cp -R` 产物带出（嵌套目录 / src==dst 中止 P2） | 改拷内容 + src==dst 跳过 | `test_phase2_commit_gate.bats` ×2（变异测试确认可捕获） |
| spec delta 声称「三处无条件一致」 | 改为只约束 v4 状态 + v3 例外 scenario | `test_stage_consumers_agreement.py` |
| v3 design-only REASON 回归 | marker 引入 kind 区分 v3-design / v3-plan | `scan_state.bats` + `_lib/test_scan_state.bats` |
| 「损坏 handoff」诊断不可达 | 1c 分支前置到分支 1 之前 | `scan_state.bats`（损坏用例）+ `test_stage_consumers_agreement.py` |
| AC-19 为假（File Map 缺 6 个文件） | File Map 补全 + AC-19 限定作用域 | — |

**验证口径修正**：此前只跑了 pytest unit/integration 与外部 e2e，**从未跑过 bats 套件**（269 个 .bats 文件）；`./test.sh --full --regression` 在 pytest unit 失败后短路，bats 阶段根本没执行。修复后以 `tests/scripts/report_regression.sh`（bats 全量 + KNOWN_FAILURES 基线比对）为准。

实施中发现并修复的两个既有缺陷（本次顺带修，不在原提案范围）：

| 缺陷 | 位置 | 影响 |
|---|---|---|
| `sys.path.insert(0 '...')` 缺逗号 → Python SyntaxError | `phase2_execute.sh` | EXEC_MODE 探测恒失败 → 永远 worktree 模式 |
| `_lib` 解析假设 PROJECT_ROOT 含 `_lib/` | `phase2_execute.sh` | 用户项目里必然失败 → EXEC_MODE 恒为 worktree |

删除 COMMIT GATE 后，worktree 模式必须自行带出未提交产物（`git worktree add` 从 HEAD 建，不含未提交文件），否则 P2 会以 "plan file missing" 失败 —— 已加 carry-over 并锁测试。

## 备注

- ship：commits `ab7c3ac`（阶段判定三处一致）+ `bf07943`（owns 可机读）+ `ac96d9f`（删除 P2 COMMIT GATE）+ `078f341`（fragment 校正为实际落地的决策）
- 验收：`.rddf/reviews/fix-agent-interface-contracts-verify.md`（20/20 AC pass）
- 归档：`2026-11-05-fix-agent-interface-contracts`，verdict cache `passed / archive-ready`
- **2026-11-05 收尾动作**：frontmatter `status: in-progress → done` + 验收段补实际结论 + 补 ship 记录
