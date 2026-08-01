# refine-plan-openspec-integration

**优先级**: P1 | **来源**: 架构评审讨论 2026-08-01
**阶段**: v2.1 | **分类**: planning
**类型**: feature
**依赖**: | **特性**:

## 架构依据

1. **openspec v1.7.0 原生提供工件级 DAG**：`openspec status --change X --json` 自 v1.7.0 起输出 `artifacts[].requires` 边、`ready/blocked/missingDeps` 状态、`applyRequires`，拓扑排序为 Kahn 算法（上游 `src/core/artifact-graph/graph.ts`）。guide-plan Phase 2.5 fill 目前**硬编码** design→tasks 顺序（`skills/guide-plan/SKILL.md`），与 openspec 原生能力重复且对 custom schema 不兼容。
2. **`openspec instructions <artifact> --json` 提供原生模板与创建指引**：propose Phase 4 的 artifact instructions 循环是 **HALF-IMPLEMENTED 伪代码**（`skills/propose/SKILL.md` 548-563 行，AGENTS.md 已标注），design/tasks 之外的 artifact 从未真正由 openspec 驱动。
3. **`openspec validate --strict --json` 覆盖 14 项 delta 校验**（SHALL/MUST、scenario、跨 section 冲突、MODIFIED scenario 丢失防护等），`skip_specs: true`（v1.7.0）原生支持零 delta change——可替代 doc-only/test-only change 的自建规避逻辑。
4. **change 级 DAG openspec 没有**：上游 `add-change-stacking-awareness` 仅为 active proposal（未发布），无 `dependsOn`/`blocks` 字段、无 `openspec deps/graph/diff` 命令。rdd-workflow 的 deps skill、`manual_deps`/`manual_blocks`（ADR-0022）、wave 调度、execution_mode 推荐（ADR-0024）属编排层职责，**必须保留自建**。
5. **版本事实**：项目要求 openspec CLI v1.3.1+，本地实测 v1.4.1，`artifacts[].requires` 需 v1.7.0+——精细化集成必须同步升级版本约束并保留降级路径。

## 范围

- **In Scope**:
  - openspec-cli 版本约束升级 ≥1.7.0（`package.json` engines + AGENTS.md + README）
  - Phase 2.5 fill 改为消费 `openspec status --change <name> --json` 工件 DAG：计算 `applyRequires` 的**传递闭包**，按拓扑序对 ready 工件依次调用 `openspec instructions <artifact> --change <name> --json` 补全
  - 补完 propose Phase 4 的 instructions 循环，移除 HALF-IMPLEMENTED 伪代码（全部 artifact 由 openspec instructions 驱动）
  - plan-done 门控增加 `status --json isComplete` 校验（`openspec validate --all --strict --json` 已由 ADR-0015 在 `skills/_lib/gate.py` plan_done 注册为 error 级 `openspec_validate` check，本提案不重复建设）
  - doc-only / test-only change 在 `.openspec.yaml` 写 `skip_specs: true`，替代自建零 delta 规避
  - CLI <1.7.0 graceful degradation：回退硬编码 artifact 顺序 + 输出升级 warning
  - 单元测试 + bats 集成测试
- **Out Scope**:
  - 不动 deps skill 输入输出格式（change 级 DAG、Mermaid 报告、`deps-analysis.json` 全保留）
  - 不删 `manual_deps` / `manual_blocks`（ADR-0022）
  - 不动 execution_mode 推荐逻辑（ADR-0024）
  - 不 fork / 自定义 openspec workflow schema（继续用 `spec-driven`）
  - 不实装或跟踪上游 `add-change-stacking-awareness` proposal（仅文档备注其存在）
  - 不改 guide-design / guide-ship 的 openspec 调用

## 关键场景

- GIVEN 骨架 change 仅有 `proposal.md`, WHEN Phase 2.5 fill 运行, THEN 按 `status --json` 拓扑序依次补全 specs / design / tasks（而非硬编码顺序），每个 artifact 内容由 `instructions <artifact> --json` 驱动
- GIVEN `status --json` 中某 artifact `status=blocked` 且 `missingDeps` 非空, WHEN fill 运行, THEN 跳过该 artifact 并先补全其依赖
- GIVEN doc-only change, WHEN 创建/校验, THEN `.openspec.yaml` 含 `skip_specs: true` 且 `openspec validate --strict` 通过
- GIVEN plan-done 门控执行, THEN 每个 active change `status --json` 的 `isComplete=true`（`validate --all --strict --json` 已由 ADR-0015 既有 check 覆盖）
- GIVEN openspec CLI 版本 <1.7.0, WHEN guide-plan intake / fill 运行, THEN 输出升级 warning 并回退到硬编码 artifact 顺序（行为与现状一致）
- GIVEN `applyRequires: ["tasks"]`, WHEN 计算必需 artifact 集合, THEN 传递闭包包含 tasks → specs/design → proposal（而非仅检查 tasks）

## 技术约束

- MUST 用 `applyRequires` 的传递闭包计算必需 artifact 集合，禁止只查根节点（v1.7.0 changelog 明确修复过此问题）
- MUST CLI <1.7.0 时 graceful degradation，不得硬失败
- MUST NOT 删除任何 change 级 DAG 自建逻辑（deps skill / manual_deps / wave 调度）
- MUST 移除 propose Phase 4 的 HALF-IMPLEMENTED 伪代码（548-563 行），替换为真实实现
- MUST 所有 openspec CLI 调用解析 `--json` 输出，禁止解析人类可读文本
- SHOULD `skip_specs: true` 判定复用 `roadmap-meta.yaml` 的 `change_type` 字段（doc-only / test-only → true）
- SHOULD 在 deps 文档中备注上游 `add-change-stacking-awareness` 的存在，作为未来替换 manual_deps 的候选

## 验收标准

- [ ] Phase 2.5 fill 顺序由 `status --json` 工件 DAG 驱动（可注入伪 status JSON 验证拓扑序）
- [ ] propose Phase 4 伪代码清零，全部 artifact 经 `instructions --json` 创建
- [ ] plan-done 增加 `status --json isComplete` 校验，与 ADR-0015 既有 `openspec_validate` check 并存无重复
- [ ] doc-only change 使用 `skip_specs: true` 的 e2e 场景通过
- [ ] CLI <1.7.0 降级路径有测试覆盖且行为与现状一致
- [ ] `package.json` engines.openspec-cli 升级为 `>=1.7.0`，文档同步
- [ ] deps skill / manual_deps / ADR-0024 相关测试无回归
- [ ] 单元测试 + bats 集成测试通过，CI 全绿（含恒真断言门控）
