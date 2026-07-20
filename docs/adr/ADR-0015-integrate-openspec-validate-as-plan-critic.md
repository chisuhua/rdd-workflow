# ADR-0015: Integrate `openspec validate` as the plan-critic gate for plan_done

> **状态**: 已采纳
> **日期**: 2026-07-08
> **决策者**: sisyphus
> **依据**: ADR-0007 (gate-mechanism), ADR-0005 (human-in-loop), ADR-0014 (review-phase-and-debt-reflow)

## Context

### 背景

`spec-workflow` v2.0 三阶段架构（ADR-0003）定义了 `arch → plan → ship` 的严格前向流转。每个阶段都有「退出 → 进入下一阶段」的门控点，由 `skills/_lib/gate.py` 的默认 `Check` 列表实现（ADR-0007）。

`plan_done` 门控点当前 4 个默认 check（`skills/_lib/gate.py:148-153`）：

| Check | 行为 | 性质 |
|---|---|---|
| `arch_handoff_exists` | 检查 `.rddf/state/.arch-handoff.json` 存在 | structural |
| `changes_committed` | 检查 `openspec/changes/<name>/proposal.md` 存在 | structural |
| `artifacts_complete` | 检查 `proposal.md` / `design.md` / `tasks.md` 三件套都在 | structural |
| `deps_analyzed` | **始终返回 `(True, "warning")`** —— 伪 check | fake-placeholder |

**`deps_analyzed` 永远返回 True**，这意味着 deps 步骤从未真正被门控阻断。`tests/integration/test_*.bats` 中 `openspec status` 命令已多处被使用（`propose.md:520,550,730`、`status.md:303`、`execute.md:510`），但 `openspec validate` —— OpenSpec 工具内置的结构 + 语义校验 —— 从未被任何 check 调用。

### 缺口 1：plan 没有语义质量门控

`plan_done` 当前 4 个 check **全是结构性**（文件存在性 + 提交性），对 plan 内容质量（clarity / verifiability / completeness）零覆盖。一个 `proposal.md` 写成「我们打算优化一下性能」也能通过 plan_done gate。

### 缺口 2：OpenSpec 的内建验证能力未接

`@fission-ai/openspec` CLI 1.4.1（`package.json` engines 声明 `>=1.3.1`）已经提供：

| 命令 | 行为 |
|---|---|
| `openspec validate --all --strict --json` | 验证所有 spec 与 change，强制 spec.md 必须含 `## Purpose` + `## Requirements` + `#### Scenario:` 块 |
| `openspec validate <change-name> --json` | 验证单个 change 的 proposal/design/tasks 模板强制段（如 `proposal.md` 的 `## Why`、`design.md` 的 `## Goals / Non-Goals`、`tasks.md` 的任务组） |
| `openspec status --change <name> --json` | 显示每个 artifact 的完成状态（已有 `propose.md`、`status.md`、`execute.md` 在用） |

这是 OpenSpec 工具自带的 **plan-critic-like 验证**，与 `docs/adr/ADR-0005-human-in-loop-nodes.md` L119 设计的 `ship.plan_review` "Prometheus 计划审查" 节点**同构**。

### 缺口 3：`ship.plan_review` 节点设计有但未实装

ADR-0005 §4 描述了 8 个 plan/ship 节点，其中 `ship.plan_review` 是「Prometheus 计划审查」—— **对生成的计划做摘要确认/调整**。但 `skills/_lib/human_nodes.py:62-70` 的 `BUILTIN_NODE_DEFS` **仅注册 7 个节点**，未包含 `ship.plan_review`（或任何"对 plan 的内容审查"节点）。

### 缺口 4：与 0014 review-phase 的对称性

ADR-0014 设计了 `guide-ship` Phase 2.5 review 节点专门处理**执行结果**（execute 后债务的分类回流）。当前没有对**计划内容**做对等 review 的节点/门控。

---

## Decision

我们在 `skills/_lib/gate.py` 的 `plan_done` 门控点集成 `openspec validate` 作为 plan-critic；在 `skills/_lib/human_nodes.py` 注册 `plan.review_validation` 节点作为可选的人工升级路径。两端共用 `OpenSpecValidateReport` 这个 view 文件（`skills/_lib/validate_report.py`）作为消费契约。

### 修改后的 plan_done 门控

```
plan_done 默认 checks (修改后):
  [existing] arch_handoff_exists  (error)
  [existing] changes_committed    (error)
  [existing] artifacts_complete   (error)
  [new]      openspec_validate    (error)  ← 调用 openspec validate --all --strict --json
  [fixed]    deps_analyzed        (warning → real check or remove)
  [new]      plan_review_dismissed (warning)  ← 若用户用 plan.review_validation 跳过
```

### 决策 1：复用 OpenSpec CLI 而非自写 Momus/Tribunal

**选择理由**：
- OpenSpec 1.4.1 已强制 plan 必须含 Why / Goals / Decisions / Scenarios 等结构化段（来自模板 + validate 规则）—— 这就是 Momus 标准
- 项目 v2.0 显式声明 self-contained（`tests/integration/test_writing_plans_integration.bats:113-156` 断言 package.json 不含 oh-my-opencode 依赖）
- 自写多 agent Tribunal (exec + reviewer) 引入额外复杂度，与「OpenSpec 已覆盖 80% Momus 工作」不符

### 决策 2：错误级而非警告级

**选择理由**：
- `plan_done` 的失败会**阻断** plan → ship 流转，这是用户对 spec-workflow 的基本期望
- 警告级适合**已知可推迟**的错误（如 ADR-0014 的 `review_debt_recorded`），但 plan 不符合 OpenSpec schema 是**必须修复**的——`openspec validate` 失败时退出码非 0，标准 CI 集成直接 FAIL
- 让用户在 archive 阶段才被回退（plan 早已 ship 完毕）的代价比在 plan_done 拦截高得多

### 决策 3：`deps_analyzed` 改为真 check

**选择理由**：
- 当前 `_check_deps_analyzed` 始终返回 `(True, "warning")` 是**死代码**（伪 check）
- 真实现：调用 `openspec validate --specs --json`，检查 `.rddf/state/.deps-output.md` 存在且 deps-ai-result 不为空
- 若 openspec CLI 不可用或 deps 步骤未运行 → 返回 `(False, "warning")`（降级而非伪造通过）

### 决策 4：新节点 `plan.review_validation` 而非复用 `ship.plan_review`

| 命名差异原因 | 原因 |
|---|---|
| `plan.review_validation` | 命名空间在 `plan.*` —— 它**只关心 plan 阶段产物是否满足 OpenSpec schema**，不修改 plan |
| `ship.plan_review` (ADR-0005 L119 已设计) | 命名空间在 `ship.*` —— 它**在执行开始前确认任务列表**，可能修改 plan |

两者职责不重叠。`plan.review_validation` 处理 **plan 阶段退出前的 schema 验证拦截**；`ship.plan_review` 处理 **ship 阶段启动时的执行可行性确认**。

### 决策 5：Validation report 作为中间 view 文件

新文件 `skills/_lib/validate_report.py` 提供：

```python
@dataclass
class ValidateReport:
    timestamp: str
    passed: bool
    failed_items: list[dict]      # [{"id": ..., "type": ..., "issues": [...]}]
    summary: dict                  # {"items": 24, "passed": 21, "failed": 3, "by_type": {...}}
    raw_json_path: str             # 持久化到 .rddf/state/openspec-validate.json
```

写入 `.rddf/state/openspec-validate.json`（**gitignored**，与 `.rddf/state/` 一致），让下游 consumers（人类 menu、archive hook）能读取。

### 影响范围

**In Scope**：
- `skills/_lib/gate.py`：`plan_done` 加 `_check_openspec_validate`、`_check_deps_analyzed` 重写、加 `_check_plan_review_dismissed`
- `skills/_lib/human_nodes.py`：注册 `plan.review_validation` 节点（HUMAN mode 默认，可切 MULTI_MODEL）
- `skills/_lib/validate_report.py`：新增 view 模块（与 `iteration.py`、`deps_output.py` 同级）
- `docs/adr/ADR-0015-integrate-openspec-validate-as-plan-critic.md`：本 ADR
- `tests/unit/test_gate.py`：覆盖 3 个新 check 的单元测试
- `tests/unit/test_human_nodes.py`：8 个节点（含 plan.review_validation）
- `tests/integration/test_plan_review_phase.bats`：结构锁

**Out of Scope**：
- `guide-plan.md` Phase 4 流程改造（保留 plan-done 契约，不改 guide 状态机）
- `openspec` CLI 版本升级或 fork（用 CLI 1.4.1 现状即可）
- 自写 multi-agent Momus/Tribunal for plan critique（OpenSpec 已覆盖 80%）
- `ship.plan_review` 节点实装（ADR-0005 L119 设计，本 ADR 不实现）

### 备选方案

| 备选 | 理由 |
|---|---|
| A: 在 `propose.md` Phase 5 用 `openspec validate` 单 check，不改 gate.py | 拒绝：propose 是单 change，跨 change 的 validate 需要 gate.py 集中 |
| B: 用 warning 级 severity | 拒绝：plan_done 失败是真正的 schema 缺陷，警告会让低质量 plan 流入 ship |
| C: 复用 `ship.plan_review` 节点而非新建 `plan.review_validation` | 拒绝：命名空间混淆，且 ship.plan_review 还未实装 |
| D: 自写 Momus-like 多 agent 验证（executor+reviewer 加权评分） | 拒绝：违反 v2.0 self-contained 策略；OpenSpec 已覆盖 80% Momus |

## Consequences

### 正面

- **真正的 plan 质量门控**：plan_done 不再容忍「模糊 proposal」
- **零运行时新依赖**：复用 OpenSpec CLI（已是 engines 依赖）
- **结构 + 语义同时验证**：OpenSpec 模板强制的 Why/Goals/Decisions/Scenarios 等段落定义 plan 质量门槛
- **view 文件契约**：`.rddf/state/openspec-validate.json` 给下游消费者统一接口
- **错误级 severity**：CI-friendly，openspec validate 失败时 exit code 非 0，标准集成
- **不破坏向后兼容**：新的 check 名字唯一（`openspec_validate`），现有 `artifacts_complete` 等不变

### 负面 / 风险

- **OpenSpec CLI 不可用时降级**：若 `openspec` 不在 PATH，check 返回 `(True, "warning")` 而非硬阻断 —— 与 ADR-0007「error/warning 两级」哲学一致
- **validate 时间成本**：对大项目 `openspec validate --all` 可能秒级；plan_done 是过渡检查，可接受
- **新增 view 文件**：`validate_report.py` 增加一个 schema 模块，需要同步 unit 测试；新增 `openspec-validate.json` 增加一个 gitignore 条目

### 后续待办

- [ ] `guide-plan.md` 在 Phase 4 调用 `validate_report.write_report()` 刷新 report 文件
- [ ] `archive.sh` 在 archive 之前检查最近一次 `openspec validate` 通过
- [ ] `ship.plan_review` (ADR-0005 L119) 后续单独 ADR 实装
- [ ] 评估 `with_change` 范围 validate（仅验证 active changes，不验证全部 spec）

## References

- `docs/adr/ADR-0007-gate-mechanism.md` — 门控机制基础
- `docs/adr/ADR-0005-human-in-loop-nodes.md` L119 — `ship.plan_review` 设计
- `docs/adr/ADR-0014-review-phase-and-debt-reflow.md` — 对称性：execute 后 review
- `skills/_lib/gate.py:148-153` — 当前 plan_done 4 个 check
- `skills/_lib/human_nodes.py:62-70` — 当前 7 个 BUILTIN_NODE_DEFS
- `skills/_lib/iteration.py` — view 文件管理参考（同级 view 模块设计模式）
- `skills/_lib/deps_output.py` — view 文件参考（同级 view 模块 Schema 设计）
- `@fission-ai/openspec` CLI 1.4.1 — `validate --all --strict --json` 命令
- `package.json` engines.openspec-cli — `>=1.3.1` 已声明


---

### 修订记录

- **2026-07-20**: 本 ADR 中的 wiring 实装（guide-plan.md Phase 4 调用 `openspec validate` + `write_report()`）已在本 change `refine-adr-0015-wiring` 中完成。状态从 待定 -> 已采纳。
  - **实装内容**: `skills/guide-plan/SKILL.md` Phase 4 在 `run_plan_done_gate` 之后、`write_plan_handoff` 之前新增 PYEOF 块，对每个 active change 运行 `openspec validate <name> --json` 并通过 `validate_report.write_report()` 持久化到 `.rddf/state/openspec-validate.json`。
  - **Dual-run 说明**: 短期内 `openspec validate` 在 plan-done 时被运行 N+1 次（gate.py 的 `--all` 1 次 + guide-plan.md 的 per-change N 次）。长期 TODO 是合并到 gate.py 单次运行，需先决定是否拆分 view 文件为 per-change（触及本 ADR §决策 5 契约）。
  - **后续待办剩余**: `archive.sh` archive 前检查最近一次 validate 通过（第 2 条）、`ship.plan_review` 实装（第 3 条）、`with_change` 范围 validate 评估（第 4 条）仍未完成。
