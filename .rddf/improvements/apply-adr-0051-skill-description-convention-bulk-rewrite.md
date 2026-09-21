---
优先级: P0
来源: "ADR-0051 (commit a65c243) + Oracle review `ses_f5bf53e0bffemcDQZvdcZQmweW`"
阶段: phase-3
分类: governance
类型: refactor
主题: 流程定制层
---
**优先级**: P0 | **来源**: ADR-0051 (commit a65c243) + Oracle review `ses_f5bf53e0bffemcDQZvdcZQmweW`
**阶段**: phase-3 | **分类**: governance | **类型**: refactor
**主题**: 流程定制层

## Why

ADR-0051 (2026-09-15) 确立了 skill `description` 字段的单一职责约定 — 只回答"何时调我",反触发由 `guide` recommender 集中处理,边界由 `role.boundaries` SSOT 承载。rdd-builder v3 描述作为最小验证样本(commit a65c243)解决了 Oracle 审查中的 3 个 BLOCKING 错误(语义反转 / 决策表误述 / 主旁路颠倒),但还有 25 个 skill 仍按 v1 风格写,继续产生同源错误。本次改进是批量应用 ADR-0051 的 5 Decision 到全部 25 个 skill,消除"description 字段承担三重职责"这一系统性根因。

## What Changes

- 4 个主阶段 skill description 重写:rdd-arch / rdd-planner / rdd-verifier / rdd-quick(rdd-builder 已在 commit a65c243 应用 v3 描述)
- 21 个子技能 description 重写:propose / execute / writing-plans / add-improve / deps / status / feature / roadmap / rdd-doctor / rdd-env-check / rdd-hub-bootstrap / rddf-session / rdd-workflow-brainstorm / cross-repo-protocol / sync-hub / watch-hub / report-issue / openspec-gate / contract-check / spoke-system-prompt-injection / INSTALL
- 5 个写作类 subagent 并行重写(1 负责主阶段 5 个,4 负责子技能每 5-6 个),共享同一 v3 描述模板保证风格一致
- 新增 `tests/integration/test_skill_description_convention.bats` — 三项断言: ≤ 200 tokens / 无 anti-trigger 段 / 引用 role.boundaries
- `skills/guide/SKILL.md` recommender 升级: 集中所有 26 个 skill 的反触发判断
- `docs/architecture/v4-pipeline-data-flow.md` 加 "skill description convention" 段

## 架构依据

- [ADR-0051](docs/adr/ADR-0051-skill-description-convention.md) — 描述字段单一职责 5 Decision(2026-09-15)
- [ADR-0028](docs/adr/ADR-0028-role-model-per-phase.md) — `role.boundaries.owns / not_owns` 是边界 SSOT,description 应引用而非复制
- Oracle review session `ses_f5bf53e0bffemcDQZvdcZQmweW` — 揭示 3 类 BLOCKING 错误根因:
  1. TRIGGER #3 语义反转("proposal.md is TARGET, not input source" 与 L55 实际行为矛盾)
  2. "Default routing" 段误述决策表(把 1 行的 case 5 dispatch-quick 描述为 modal default,而 case 1 approve 才是 4 行)
  3. DO-NOT 反触发列表与 ADR-0048 主旁路关系矛盾(建议 small change → rdd-quick 直连,但 builder P0 dispatch 是主路径)
- 用户判断(2026-09-15):"反触发建议和 rdd-builder 没有直接触发关系" — 印证 Oracle 结论

## 范围

**In Scope**:

- 25 个 skill description 重写:
  - 主阶段 4: rdd-arch / rdd-planner / rdd-verifier / rdd-quick
  - 子技能 21: propose / execute / writing-plans / add-improve / deps / status / feature / roadmap / rdd-doctor / rdd-env-check / rdd-hub-bootstrap / rddf-session / rdd-workflow-brainstorm / cross-repo-protocol / sync-hub / watch-hub / report-issue / openspec-gate / contract-check / spoke-system-prompt-injection / INSTALL
- 新增 `tests/integration/test_skill_description_convention.bats` — 三项断言: ≤ 200 tokens / 无 anti-trigger 段 / 引用 role.boundaries
- `skills/guide/SKILL.md` recommender 升级: 集中所有 26 个 skill 的反触发判断
- `docs/architecture/v4-pipeline-data-flow.md` 加 "skill description convention" 段

**Out of Scope**:

- `_lib/` Python 模块(不读 description)
- `rddf` CLI 命令(从 skill 调用,不直接读 description)
- `role.boundaries` 字段本身(per ADR-0028 已是 SSOT,本改进不重定义)
- rdd-builder v3 description(已 commit a65c243,作为最小验证样本)
- 任何新 ADR 起草(本次纯应用 ADR-0051 既有 5 Decision)

## Capabilities

- MUST: 每个 skill description ≤ 200 tokens(per ADR-0051 Decision 4)
- MUST: 不含 "**DO NOT use**" / "**Prefer ... instead**" / "**Legacy entry**" 类 anti-trigger 段落(per Decision 1-2)
- MUST: 不复制 role.boundaries.owns / not_owns 列表,改用引用(per Decision 3)
- MUST: 不引导走 deprecated / legacy fallback 路径(per Decision 5)
- MUST NOT: 改动 `_lib/` Python 模块或 `rddf` CLI 命令(它们不读 description)
- MUST NOT: 修改 `role.boundaries` 字段本身(per ADR-0028 已是 SSOT)
- SHOULD: 5 个写作类 subagent 并行重写时,共享同一 v3 描述模板以保证风格一致
- SHOULD: 每个 skill description 重写后,grep 验证无残留 anti-trigger 关键词
- SHOULD: bats 测试覆盖所有 26 个 skill description(per ADR-0051 §后续待办)

## Impact

- **正向影响**:
  - 25 个 skill description token 平均下降 40-60%(从 50-380 tokens 收敛到 ≤ 200 tokens)
  - 消除"description 字段承担三重职责"这一系统性根因,后续 skill 设计直接套模板即可
  - `guide` recommender 成为反触发 SSOT,跨 26 个 skill 一致性自动保证
  - Oracle BLOCKING 类错误(事实反转 / 决策表误述 / 主旁路颠倒)在新 batch 中不再产生
  - AI agent 在 skill 选择时获得更聚焦的触发条件,降低误选率

- **负面影响 / 风险**:
  - 第一次按本改进重写 25 个 skill description 是大工作量,需要 5 个写作类 subagent 并行,资源占用较高
  - `guide` recommender 升级是关键路径,如果升级失败会导致反触发判断缺失(single point of failure)
  - 风格一致性需 5 个 agent 共享同一 v3 模板,如果模板设计不当会产生轻微漂移
  - 历史 OpenSpec proposal 引用的 description 文本可能因重写而失效(需 grep 验证)

- **迁移成本**:
  - 已有 27 个 `.rddf/improvements/*.md` 文件不受影响(本次只改 skill description)
  - rdd-builder v3 description 已落地,作为本改进的参考样本
  - 实施路径上无 breaking change(description 字段是 advisory metadata,无 CI grep)

## 关键场景

- GIVEN skill description 含 anti-trigger 列表("**DO NOT use**" / "**Prefer ... instead**" 风格)
  WHEN 应用 ADR-0051 Decision 1-2
  THEN description 只描述正向触发条件(身份 / 触发前置 / 默认行为),反触发判断交由 guide recommender 集中处理

- GIVEN skill description 复制 role.boundaries.owns / not_owns 列表
  WHEN 应用 ADR-0051 Decision 3
  THEN description 改为 "see role.boundaries.owns / not_owns" 一行引用,避免双 SSOT 漂移

- GIVEN skill description 引导走 deprecated / legacy fallback 路径(如 propose 子技能 / `.plan-handoff.json` fallback)
  WHEN 应用 ADR-0051 Decision 5
  THEN description 保持"严格守门"语气,不暗示可以绕开 canonical 路径;实施层 fallback 仍存在,但 description 不引导

- GIVEN 25 个 skill 描述 token 数普遍 50-380,差异巨大
  WHEN 应用 ADR-0051 Decision 4(≤ 200 tokens 预算)
  THEN 每个 skill description 控制在 ≤ 200 tokens,优先覆盖触发条件 + 数据契约 + 默认行为

## 技术约束

- MUST: 每个 skill description ≤ 200 tokens(per ADR-0051 Decision 4)
- MUST: 不含 "**DO NOT use**" / "**Prefer ... instead**" / "**Legacy entry**" 类 anti-trigger 段落(per Decision 1-2)
- MUST: 不复制 role.boundaries.owns / not_owns 列表,改用引用(per Decision 3)
- MUST: 不引导走 deprecated / legacy fallback 路径(per Decision 5)
- MUST NOT: 改动 `_lib/` Python 模块或 `rddf` CLI 命令(它们不读 description)
- MUST NOT: 修改 `role.boundaries` 字段本身(per ADR-0028 已是 SSOT)
- SHOULD: 5 个写作类 subagent 并行重写时,共享同一 v3 描述模板以保证风格一致
- SHOULD: 每个 skill description 重写后,grep 验证无残留 anti-trigger 关键词
- SHOULD: bats 测试覆盖所有 26 个 skill description(per ADR-0051 §后续待办)

## Acceptance

- [ ] 4 个主阶段 skill description 重写完成,每条 ≤ 200 tokens(rdd-arch / rdd-planner / rdd-verifier / rdd-quick)
- [ ] 21 个子技能 description 重写完成,每条 ≤ 200 tokens
- [ ] 所有 description grep 无 "DO NOT use" / "Prefer instead" / "Legacy entry" 等 anti-trigger 残留
- [ ] 所有 description 不复制 role.boundaries.owns / not_owns(改为引用)
- [ ] `tests/integration/test_skill_description_convention.bats` 新增并 pass,覆盖三项断言(≤ 200 tokens / 无 anti-trigger / 引用 role.boundaries)
- [ ] `skills/guide/SKILL.md` recommender 升级,集中所有 26 个 skill 的反触发判断
- [ ] `docs/architecture/v4-pipeline-data-flow.md` 加 "skill description convention" 段
- [ ] `./test.sh --quick` 全绿(无 regression)
- [ ] 5 个写作类 subagent 输出后,人工 review 通过(无事实错误或风格漂移)
- [ ] improvement-suggestions.md 移除本提案行(批准后由 sync_suggestions 自动清理)

## 验收标准

- [ ] 4 个主阶段 skill description 重写完成,每条 ≤ 200 tokens(rdd-arch / rdd-planner / rdd-verifier / rdd-quick)
- [ ] 21 个子技能 description 重写完成,每条 ≤ 200 tokens
- [ ] 所有 description grep 无 "DO NOT use" / "Prefer instead" / "Legacy entry" 等 anti-trigger 残留
- [ ] 所有 description 不复制 role.boundaries.owns / not_owns(改为引用)
- [ ] `tests/integration/test_skill_description_convention.bats` 新增并 pass,覆盖三项断言(≤ 200 tokens / 无 anti-trigger / 引用 role.boundaries)
- [ ] `skills/guide/SKILL.md` recommender 升级,集中所有 26 个 skill 的反触发判断
- [ ] `docs/architecture/v4-pipeline-data-flow.md` 加 "skill description convention" 段
- [ ] `./test.sh --quick` 全绿(无 regression)

## 相关

- 来源: [ADR-0051](docs/adr/ADR-0051-skill-description-convention.md) (commit a65c243) — 描述字段单一职责 5 Decision
- 关联: [ADR-0028](docs/adr/ADR-0028-role-model-per-phase.md) — `role.boundaries` SSOT 来源
- 关联: [ADR-0048](docs/adr/ADR-0048-v4-stage-merge-revision.md) §Decision 3 — builder P0 dispatch 是主路径,direct rdd-quick 是旁路
- 关联: [ADR-0049](docs/adr/ADR-0049-rdd-builder-phase0-llm-integration.md) Decision 2 — auto-decision 9 行表,case 1 approve 是 modal default
- 关联: [ADR-0050](docs/adr/ADR-0050-rdd-builder-auto-pick-mode.md) — auto-pick 模式默认 ON
- 文件: 25 个 `skills/*/SKILL.md` frontmatter description 字段
- 文件: `tests/integration/test_skill_description_convention.bats`(新增)
- 文件: `skills/guide/SKILL.md`(recommender 升级)
- 文件: `docs/architecture/v4-pipeline-data-flow.md`(新增段)
