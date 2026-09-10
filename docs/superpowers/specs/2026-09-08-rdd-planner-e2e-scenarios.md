# rdd-planner e2e 测试场景 spec

> **日期**: 2026-09-08
> **所属**: `2026-09-08-e2e-test-plan-design.md` v1
> **覆盖 skill**: `rdd-planner`（per spec §3.3、ADR-0025 design 阶段独立化、ADR-0037/0038/0042 planner lib）
> **scenario 数**: 8（P-E1..P-E8）

## 0. 通用约定

详见 `2026-09-08-rdd-quick-e2e-scenarios.md` §0 通用约定字段定义。本 spec 复用。

**rdd-planner 专属约定**：
- 入口：`skill_use("rdd-planner")` 调 `rdd-planner/SKILL.md` prose 状态机
- handoff 契约：`.rddf/state/.planner-handoff.json` v1 schema（per spec §3.3）
- 入口脚本：`planner_stage_entry.sh`（emit planner-handoff）
- 出口脚本：`planner_stage_exit.sh`（consume arch-handoff + emit planner-handoff）
- 协作文件：`improvement-suggestions.md` / `improvement-approved.md` / `.rddf/roadmap/features/*.md` / `.rddf/improvements/*.md`
- 横切命令（保留向后兼容）：status / sync / feedback / attach / audit / history / advance-sprint
- 状态机阶段：stage entry → intake → propose → review → approve/reject/defer → stage exit

## P-E1: stage entry → planner-handoff 写出

| 字段 | 内容 |
|------|------|
| 入口 | A 层：`bash skills/rdd-planner/scripts/planner_stage_entry.sh`；C 层：agent prompt 走 stage entry |
| 预期产物 | `.rddf/state/.planner-handoff.json` 存在；`schema=planner-handoff-v1` + `version=1` + `owner=rdd-planner` |
| 必清状态 | handoff 5 必填字段齐全：`schema` / `version` / `owner` / `current_sprint` / `created_at` |
| AC 断言 | handoff 合 spec §3.3 v1 schema；`SKIP_PLANNER_HANDOFF` env 跳过路径可重现 |
| 隔离规则 | `setup_fake_project` 含 `.arch-handoff.json` v3 baseline（planner 入口依赖 arch 产物） |
| 备注 | 与 `test_full_workflow_e2e.bats` 2/7 case 重复但更深（planner 单 stage 视角） |

## P-E2: intake → 扫描 5 类源

| 字段 | 内容 |
|------|------|
| 入口 | 接 P-E1；agent prompt：`请扫描当前项目，列出所有可建议的提案` |
| 预期产物 | stdout 含 5 类源建议（ADR gap / code TODO / docs missing / roadmap theme 未覆盖 / cross-repo 机会）；`.rddf/state/.planner-intake.json` 缓存 |
| 必清状态 | intake json `intake_status=scanned` + `sources_scanned` 数组 |
| AC 断言 | ≥3 类源被识别（最低门槛）；intake 文件 5 字段齐全 |
| 隔离规则 | 同 P-E1 |
| 备注 | per `skills/rdd-planner/scripts/plan_intake.sh`（Round A Task 3，Oracle C1 fix）；与 `test_plan_intake.bats` 互补 |

## P-E3: propose → 5 段格式提案落盘

| 字段 | 内容 |
|------|------|
| 入口 | 接 P-E2；agent prompt：`请为 "P-E3 测试提案" 写一份建议提案` |
| 预期产物 | `improvement-suggestions.md` 新增 1 行（per docs/improvement-suggestions-format.md 表格格式）；含 priority / source / date / status |
| 必清状态 | 表格行 schema 正确；status 初始 `pending` |
| AC 断言 | 1 行新 entry；列名匹配 `proposal-suggestions-format.md` 模板 |
| 隔离规则 | 同 P-E1 |
| 备注 | per `_lib/state.sh::write_suggestions` + `proposal-suggestions-format.md` |

## P-E4: brainstorm 流程 → 改进提案

| 字段 | 内容 |
|------|------|
| 入口 | agent prompt：`请用 add-improve + rdd-workflow-brainstorm 走完提案头脑风暴流程` |
| 预期产物 | `.rddf/improvements/<name>.md` 存在；含 5 段（背景/目标/方案/风险/回滚） |
| 必清状态 | `pre_create_brainstorm_check.sh` EXIT=0（HARD-GATE 验证） |
| AC 断言 | 5 段齐全；`bypass-audit` / `HARD-GATE` 关键词在 `add-improve/SKILL.md` 中引用 |
| 隔离规则 | `setup_fake_project` 含 git init + remote（per pre_create_brainstorm_check） |
| 备注 | per `skills/add-improve/SKILL.md` + `rdd-workflow-brainstorm/SKILL.md`；与 `test_add_improve_from_roadmap.bats` 互补 |

## P-E5: approve → 落盘 proposal.md + spec.md (D3)

| 字段 | 内容 |
|------|------|
| 入口 | 接 P-E3 + P-E4；agent prompt：`请批准 "P-E3 测试提案"` |
| 预期产物 | `openspec/changes/<n>/proposal.md` 存在；`openspec/changes/<n>/specs/<n>/spec.md` 存在（D3 协同） |
| 必清状态 | `improvement-suggestions.md` 移除该 entry；`improvement-approved.md` 新增该 entry |
| AC 断言 | 2 个产物文件齐全；表格行迁移正确；spec.md 段头 `## ADDED Requirements` |
| 隔离规则 | 同 P-E1 |
| 备注 | per `skills/guide-design/scripts/approve_proposal.sh`（v2.0.6+ D3 协同）；与 `test_approve_proposal.bats` 互补 |

## P-E6: reject → feedback 写入 + 不落盘 change

| 字段 | 内容 |
|------|------|
| 入口 | 接 P-E3；agent prompt：`请拒绝该提案，理由：scope 过大` |
| 预期产物 | `improvement-suggestions.md` 标记 `status=rejected`（不删除，per proposal-suggestions-format 状态词汇表）；不创建 `openspec/changes/<n>/` |
| 必清状态 | rejected 状态行写入；change 目录不存在 |
| AC 断言 | status 字段非空 ∈ {rejected, deferred}；`openspec/changes/` 不增 |
| 隔离规则 | 同 P-E1 |
| 备注 | 状态词汇 per docs/improvement-suggestions-format.md |

## P-E7: 横切命令 — status / sync / feedback / advance-sprint

| 字段 | 内容 |
|------|------|
| 入口 | agent prompt 依次跑 4 个横切命令：`rddf planner status` / `rddf planner sync` / `rddf planner feedback` / `rddf planner advance-sprint` |
| 预期产物 | 每命令 stdout 含对应段标题（status / sync / feedback / advance-sprint）；不写新 state 文件 |
| 必清状态 | 横切命令仅读，不污染 state |
| AC 断言 | 4 命令 exit 0；stdout 含 4 段标题；`stat .rddf/state/*.json -c %Y` 在跑前 = 跑后 |
| 隔离规则 | 同 P-E1 |
| 备注 | per spec §3.3 "Existing horizontal-orchestrator commands remain available"；与 `tests/unit/test_planner_*.py` 12 cases 互补 |

## P-E8: stage exit → planner-handoff 终态

| 字段 | 内容 |
|------|------|
| 入口 | 接 P-E5；agent prompt：`请走完 stage exit` |
| 预期产物 | `.planner-handoff.json` `stage_status=exited`；`next_sprint` 字段更新 |
| 必清状态 | handoff `stage_status=exited` + `exited_at` ISO8601；下游 rdd-builder 入口可达 |
| AC 断言 | exit 0；handoff 终态字段齐全；handoff v1 schema 合规 |
| 隔离规则 | 同 P-E1 |
| 备注 | 闭环：stage entry (P-E1) → stage exit (P-E8) 完整生命周期 |

## 覆盖矩阵

| planner 内部阶段 | 覆盖 scenarios |
|-------------------|----------------|
| stage entry | P-E1 |
| intake | P-E2 |
| propose / brainstorm | P-E3, P-E4 |
| approve / reject | P-E5, P-E6 |
| 横切命令 | P-E7 |
| stage exit | P-E8 |

## 与现有 12 cases 的关系

- `tests/unit/test_planner_*.py`（12）：保留，单元层
- `tests/integration/test_approve_proposal.bats` + `test_approved_inconsistency.bats` + `test_add_improve_from_roadmap.bats` + `test_feedback_cmd.bats`：保留，契约/结构层
- `tests/e2e/agent/test_rdd_planner_e2e.bats`（8，本 spec）：新增，prose UX 真 e2e

总计 20+ cases 覆盖 rdd-planner（12 旧 + 8 新），分层无重叠。

## 关键空白

`tests/integration/` 当前**无**任何 rdd-planner 命名的 .bats 文件（grep `rdd-planner` 0 命中）。本 spec 8 cases 是该流程的 e2e 入口补全。
