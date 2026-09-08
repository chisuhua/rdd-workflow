# rdd-arch e2e 测试场景 spec

> **日期**: 2026-09-08
> **所属**: `2026-09-08-e2e-test-plan-design.md` v1
> **覆盖 skill**: `rdd-arch`（per ADR-0016 discovery contract、ADR-0018 arch quality gate、ADR-0028 role model）
> **scenario 数**: 8（A-E1..A-E8）

## 0. 通用约定

详见 `2026-09-08-rdd-quick-e2e-scenarios.md` §0 通用约定字段定义。本 spec 复用。

**rdd-arch 专属约定**：
- 入口：`skill_use("rdd-arch")` 调 `rdd-arch/SKILL.md` prose 状态机
- handoff 契约：`.rddf/state/.arch-handoff.json` v3 schema（per ADR-0016）
- ADR 目录：`docs/adr/`（默认）或 `SPEC_WORKFLOW_ADR_DIR` env 覆盖
- Roadmap：`roadmap.md`（默认）或 `SPEC_WORKFLOW_ROADMAP_PATH` 覆盖
- arch-done gate：`check_arch_done_gate`（≥1 ADR + roadmap 存在）
- 状态机阶段：setup → ADR 创建 → 架构分析 → roadmap 定义 → arch-done gate

## A-E1: setup → arch discovery contract

| 字段 | 内容 |
|------|------|
| 入口 | agent prompt：`请按 skill_use("rdd-arch") 走 setup 阶段，输出 discovery 结果` |
| 预期产物 | `.rddf/state/.arch-handoff.json` 存在；`adr_dir` / `roadmap_path` / `architecture_dir` / `adr_pattern` / `discovered` 5 字段齐全（per ADR-0016 v1） |
| 必清状态 | handoff `version: 1`（非 0，per ADR-0016 消费者拒绝 version=0 payload） |
| AC 断言 | handoff 5 字段非空；`schema_version` 合规；env 变量优先级最高（`SPEC_WORKFLOW_ADR_DIR` 覆盖） |
| 隔离规则 | `setup_fake_project` 含 git init + `docs/adr/` 空目录 + `roadmap.md` 初始 stub |
| 备注 | 现有 `test_arch_discovery_contract.bats` 测脚本输出；本 case 测 agent 能否按 prose 跑 setup + 写入 handoff |

## A-E2: ADR 创建 → 4 段格式落地

| 字段 | 内容 |
|------|------|
| 入口 | 接 A-E1；agent prompt：`请创建 ADR-0001，主题：rdd-quick 引入。包含 Status / Context / Decision / Consequences 4 段` |
| 预期产物 | `docs/adr/ADR-0001-<slug>.md` 存在；含 4 段 + `**状态**: 待定` quote block（per spec 模板 ADR-0000） |
| 必清状态 | `docs/adr/ADR-0000-template.md` 未被覆盖；新 ADR 命名匹配 `^ADR-\d{4}-.+\.md$` |
| AC 断言 | 4 段标题存在；status 字段 `**状态**:` quote 块格式；非空内容 |
| 隔离规则 | 同 A-E1 |
| 备注 | per `docs/adr/ADR-0000-template.md` 模板 |

## A-E3: 差距分析 → arch-quality-gate 通过

| 字段 | 内容 |
|------|------|
| 入口 | 接 A-E2；agent prompt：`请对当前项目做 arch 差距分析并输出报告` |
| 预期产物 | `.rddf/state/.arch-quality-report.json` 存在；含 gaps 数组；`arch-quality-gate.py` 报告通过 |
| 必清状态 | report 字段含 ≥1 gap 描述 + severity ∈ {info, warn, error} |
| AC 断言 | report 字段齐全；`arch-quality-gate.py` exit 0；`STRICT_ARCH_GATE` 默认 OFF 时 warning 通行 |
| 隔离规则 | 同 A-E1 |
| 备注 | per `arch_quality_gate.py` + `skills/rdd-arch/scripts/arch_gap_analysis.sh`（Round B Task B1） |

## A-E4: roadmap 定义 → phase 分配

| 字段 | 内容 |
|------|------|
| 入口 | 接 A-E3；agent prompt：`请定义 3 个 phase 的 roadmap：phase-1 / phase-2 / phase-3，每 phase ≥1 theme` |
| 预期产物 | `roadmap.md` 含 3 个 `## Phase N:` 段；每段 ≥1 theme bullet；`# AUTO-INDEX` 段生成 |
| 必清状态 | `roadmap.md` 改前 vs 改后 diff 仅含新增 phase 段 |
| AC 断言 | 3 个 `## Phase` 段；AUTO-INDEX 含新 phase 引用；roadmap_state.json 计数 +1 |
| 隔离规则 | 同 A-E1 |
| 备注 | per `skills/roadmap/SKILL.md::init` + `roadmap_incremental_update.sh`（v2.2+） |

## A-E5: arch-done gate pass — ≥1 ADR + roadmap 存在

| 字段 | 内容 |
|------|------|
| 入口 | 接 A-E4；agent prompt：`请走完 arch-done gate 验证` |
| 预期产物 | `check_arch_done_gate` exit 0；arch-handoff.json `arch_done_status="done"`；stdout 含 "✓ arch-done" 段 |
| 必清状态 | handoff `arch_done_status=done`；`completed_at` 字段 ISO8601 |
| AC 断言 | exit 0；handoff `arch_done_status` ∈ {done, partial}（默认 done） |
| 隔离规则 | 同 A-E1 |
| 备注 | per `skills/rdd-arch/scripts/arch_done_gate.sh`（Round B Task B2）；与 `test_full_workflow_e2e.bats` 5/7 case 互补 |

## A-E6: arch-done gate fail — 0 ADR 阻断

| 字段 | 内容 |
|------|------|
| 入口 | 故意 skip A-E2（不创建 ADR） |
| 预期产物 | `check_arch_done_gate` exit 1；stderr 含 "至少需要 1 个 ADR"（per 现有 stderr 模板） |
| 必清状态 | handoff `arch_done_status` 不变（仍 initial）；`docs/adr/` 仅模板文件 |
| AC 断言 | exit 1；stderr 匹配 0 ADR 错误模板；arch-done handoff 不写 |
| 隔离规则 | 同 A-E1 |
| 备注 | per `arch_done_gate.sh:47` 错误信息；与 `test_full_workflow_e2e.bats` 5/7 case 重复但更深 |

## A-E7: arch-handoff stale 检测

| 字段 | 内容 |
|------|------|
| 入口 | 接 A-E5；但手动修改 `docs/adr/ADR-0001-*.md` 头部加 timestamp |
| 预期产物 | arch-handoff v2 schema 检测到 stale；`stale_revision` 字段触发 |
| 必清状态 | 第二次调 setup 走 fallback full（per-worktree .rddf/state/ 隔离，state 绑 codebase_commit） |
| AC 断言 | handoff `stale=true` 或 `revision` 字段更新；arch 状态机走 fallback full 路径 |
| 隔离规则 | 同 A-E1 |
| 备注 | per ADR-0027 continuous evolution + state 增量隔离；与 `test_arch_handoff_stale.bats` 互补 |

## A-E8: 隔离契约 — 不污染下游 planner state

| 字段 | 内容 |
|------|------|
| 入口 | 真跑 A-E1..A-E7 后，扫下游 planner 预期写的 state 文件 |
| 预期产物 | 7 scenario 全部不写 `.rddf/state/.planner-handoff.json` |
| 必清状态 | planner 路径专属文件 unchanged：`.planner-handoff.json` / `.design-handoff.json` / `proposal-suggestions.md` |
| AC 断言 | `find .rddf/state -name "*handoff*.json"` 仅含 `.arch-handoff.json`；plan/suggest/approved md 不变 |
| 隔离规则 | meta-测试 |
| 备注 | 跨阶段零污染；与 `2026-09-08-rdd-planner-e2e-scenarios.md` 互锁 |

## 覆盖矩阵

| arch 内部 phase | 覆盖 scenarios |
|------------------|----------------|
| Setup + discovery | A-E1 |
| ADR 创建 | A-E2 |
| 架构分析 + 质量门 | A-E3 |
| Roadmap 定义 | A-E4 |
| arch-done gate | A-E5, A-E6 |
| Stale 隔离 | A-E7 |
| 跨阶段零污染 | A-E8 |

## 与现有 10 cases 的关系

- `tests/unit/test_arch_*.py`（8）：保留，单元层
- `tests/integration/test_arch_*_extraction.bats`（9）+ `test_arch_discovery_contract.bats`（1）+ `test_rdd_arch_cli.bats`（1）：保留，契约/结构层
- `tests/e2e/agent/test_rdd_arch_e2e.bats`（8，本 spec）：新增，prose UX 真 e2e

总计 18 cases 覆盖 rdd-arch（10 旧 + 8 新），分层无重叠。
