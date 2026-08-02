# refine-plan-openspec-integration

## Why

guide-plan 对 openspec 的调用停留在"能跑就行"的层面，与 openspec 原生能力存在三处脱节：其一，openspec v1.7.0 起 `openspec status --change X --json` 输出完整的工件级 DAG（`artifacts[].requires` 边、`ready/blocked/missingDeps`、`applyRequires`，Kahn 拓扑排序），但 Phase 2.5 fill 仍**硬编码** design→tasks 顺序，对 custom schema 不兼容；其二，propose Phase 4 的 artifact instructions 循环是 **HALF-IMPLEMENTED 伪代码**（`skills/propose/SKILL.md` 548-563 行，AGENTS.md 已标注），design/tasks 之外的 artifact 从未由 `openspec instructions <artifact> --json` 原生驱动；其三，`skip_specs: true`（v1.7.0）原生支持零 delta change，doc-only/test-only change 仍在用自建规避逻辑。需要明确的是：**change 级 DAG openspec 没有**（上游 `add-change-stacking-awareness` 仅为 active proposal，未发布），rdd-workflow 的 deps skill、`manual_deps`/`manual_blocks`（ADR-0022）、wave 调度、execution_mode 推荐（ADR-0024）属编排层职责，必须保留自建——本提案只把工件级能力委托给 openspec，不重复造轮子也不误删自建层。

依据：ADR-0015（openspec validate 集成为 plan-critic，已实装于 `skills/_lib/gate.py`）、ADR-0020（增量 skeleton planning）、ADR-0022（manual_deps）、ADR-0024（deps 驱动执行模式）、openspec v1.7.0 changelog（`artifacts[].requires`、transitive closure 修复、`skip_specs`）。

## What Changes

**In Scope**:

- **版本约束升级**：`package.json` engines.openspec-cli `>=1.3.1` → `>=1.7.0`，AGENTS.md / README 同步
- **Phase 2.5 fill 改为 DAG 驱动**：消费 `openspec status --change <name> --json`，计算 `applyRequires` 的**传递闭包**，按拓扑序对 ready 工件依次调用 `openspec instructions <artifact> --change <name> --json` 补全；blocked 工件跳过并先补依赖
- **补完 propose instructions 循环**：移除 HALF-IMPLEMENTED 伪代码（548-563 行），全部 artifact 由 openspec instructions 驱动
- **plan-done 门控增加 `status --json isComplete` 校验**（`openspec validate --all --strict --json` 已由 ADR-0015 在 gate.py plan_done 注册为 error 级 check，本提案不重复建设）
- **`skip_specs: true` 接入**：doc-only / test-only change（由 `roadmap-meta.yaml` 的 `change_type` 判定）在 `.openspec.yaml` 写 `skip_specs: true`，替代自建零 delta 规避
- **graceful degradation**：CLI <1.7.0 时回退硬编码 artifact 顺序 + 输出升级 warning（不硬失败）
- **单元测试 + bats 集成测试**

**Out of Scope**：不动 deps skill 输入输出格式（change 级 DAG、Mermaid 报告、`deps-analysis.json` 全保留）；不删 `manual_deps`/`manual_blocks`；不动 execution_mode 推荐逻辑；不 fork/自定义 openspec workflow schema；不实装或跟踪上游 `add-change-stacking-awareness`（仅文档备注）；不改 guide-design / guide-ship 的 openspec 调用。

## Capabilities

### New Capabilities

- `plan-artifact-dag-fill`：fill 阶段由 openspec 工件 DAG 驱动（传递闭包 + 拓扑序 + ready/blocked 感知），custom schema 天然兼容
- `openspec-version-degradation`：CLI 版本检测与降级路径（<1.7.0 回退硬编码顺序 + warning）

### Modified Capabilities

- `workflow-plan-phase`：propose instructions 循环实装（伪代码清零）；plan-done 增加 `isComplete` 校验；doc-only/test-only change 使用 `skip_specs: true`

## Impact

- **受影响文件**：`package.json`（engines）、`skills/guide-plan/SKILL.md`（Phase 2.5 fill）、`skills/guide-plan/scripts/plan_done_gate.sh`（isComplete 校验）、`skills/propose/SKILL.md`（伪代码移除）、`skills/propose/scripts/propose_change.{sh,py}`（instructions 循环实装）、`skills/propose/scripts/infer_change_type.py`（skip_specs 判定复用）、AGENTS.md、README.md、`tests/unit/`、`tests/integration/`
- **兼容性**：CLI <1.7.0 降级路径行为与现状一致；deps skill / ADR-0022 / ADR-0024 全部无回归
- **硬约束**：`applyRequires` 必须算传递闭包（v1.7.0 changelog 明确修复过只查根节点的问题）；openspec CLI 调用只解析 `--json` 输出；不得删除任何 change 级 DAG 自建逻辑
- **协同**：与 `move-proposal-creation-to-design` 天然兼容——design 阶段预建的完整 proposal 在 `status --json` 中显示 proposal=done，DAG 驱动的 fill 自然跳过

## Acceptance

- [ ] Phase 2.5 fill 顺序由 `status --json` 工件 DAG 驱动（可注入伪 status JSON 验证拓扑序）
- [ ] propose Phase 4 伪代码清零，全部 artifact 经 `instructions --json` 创建
- [ ] plan-done 增加 `isComplete` 校验，与 ADR-0015 既有 `openspec_validate` check 并存无重复
- [ ] doc-only change 使用 `skip_specs: true` 的 e2e 场景通过
- [ ] CLI <1.7.0 降级路径有测试覆盖且行为与现状一致
- [ ] `package.json` engines.openspec-cli 升级为 `>=1.7.0`，文档同步
- [ ] deps skill / manual_deps / ADR-0024 相关测试无回归
- [ ] 单元测试 + bats 集成测试通过，CI 全绿
