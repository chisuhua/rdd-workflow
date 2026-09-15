# ADR-0051: Skill `description` 字段约定 — 正向触发条件 + 单一职责

> **Date**: 2026-09-15
> **Status**: 待采纳
> **Supersedes**: (none)
> **Amends**: (none)
> **Author**: rdd-builder description refactor (Oracle review + 用户判断)

## Context

rdd-workflow 共有 26 个子技能 + 5 个主阶段 skill,每个 skill 在 frontmatter `description` 字段描述自身。**当前没有统一约定**,各 skill description 风格不一、长度悬殊(~50-380 tokens)、职责混叠。

2026-09-15 在 `rdd-builder` description 重写过程中,Oracle 审查发现 3 个 BLOCKING 级事实错误(per `skills/rdd-builder/SKILL.md` Oracle review session `ses_f5bf53e0bffemcDQZvdcZQmweW`):

1. **TRIGGER #3 语义反转** — 写 "proposal.md is TARGET, not input source",与 SKILL.md L55 实际行为(P0 读取已存在的 proposal.md)矛盾
2. **"Default routing" 段误述决策表** — 把 ADR-0049 9 行决策表中 1 行的 case 5 dispatch-quick 描述为默认行为,而 case 1 approve 才是 modal default(4 行)
3. **DO-NOT 反触发列表与 ADR-0048 主旁路关系矛盾** — 建议 "small change → rdd-quick 直连",但 ADR-0048 明确 builder P0 dispatch 是主路径,direct rdd-quick 只是旁路 fallback

Oracle DIMENSION 2/6/10 指出根因:**description 字段被错位承担了 routing / anti-routing / boundaries 三重职责,导致事实陈述容易与 SSOT 漂移**。

用户判断(2026-09-15):"rdd-builder 没有直接触发关系的反触发建议应去掉";Oracle 与用户方向一致 — 反触发不应进 description。

### 架构依据

- [ADR-0028](ADR-0028-role-model-per-phase.md) — `role.boundaries.owns / not_owns` 是边界的 SSOT
- [ADR-0043](ADR-0043-rdd-workflow-v4-stage-merge.md) — 4 阶段架构,主阶段 skill 描述需对齐
- [ADR-0048](ADR-0048-v4-stage-merge-revision.md) §Decision 3 — builder P0 dispatch-quick 是主路径,direct rdd-quick 是旁路
- [ADR-0049](ADR-0049-rdd-builder-phase0-llm-integration.md) Decision 2 — auto-decision 9 行表,case 1 approve 是 modal default
- [ADR-0050](ADR-0050-rdd-builder-auto-pick-mode.md) — auto-pick 模式默认 ON
- `skills/guide/SKILL.md` — 推荐器入口,扫描项目状态推荐下一步 skill

## Decision

### Decision 1: description 字段单一职责 — "何时调我"

`description` 字段**只**回答"何时调我",承担以下三个子职责:

1. **身份声明** — skill 在 v4 架构中的阶段定位(主阶段) / 功能定位(子技能)
2. **触发前置条件** — 数据契约(必备文件 / schema / env var)
3. **默认行为** — auto-pick / auto-decision 等 ON/OFF 默认状态

**不**包含:

- 反触发 / 何时不调我 — 集中到 `guide` 推荐器
- boundary ownership — 引用 `role.boundaries.owns / not_owns`(per ADR-0028),不复制
- 备选方案对比 — 引用 body 段或 ADR,不重复列举
- ADR 引用尾注 — body 已有,description 只指关键 ADR(最多 1-2 个)

### Decision 2: 反触发的归属 — `guide` 推荐器为 SSOT

反触发判断(何时不调 rdd-builder / 何时不调 rdd-quick / ...)集中在 `guide` skill 的描述与 recommender 实现。理由:

- **N×N 重复问题**: 若每个 skill 列举反触发,26 个 skill × N 个反场景 = 不可维护
- **集中一致性**: guide 一次升级,所有 skill 自动同步
- **正交解耦**: 选哪个 skill 是 routing 问题,选哪个 skill 干什么是 description 问题,两者不应混叠

每个 skill 的 description 删除 `**DO NOT use ... when**` / `**Prefer ... instead**` 类段落。

### Decision 3: boundaries 的归属 — 引用而非复制

`role.boundaries.owns / not_owns`(per ADR-0028)已是 SSOT。description 字段**不复制** Owns/Not owns 列表,改为引用:

```yaml
description: |
  ... (省略触发条件等) ...
  Boundary ownership: see role.boundaries.owns / not_owns.
```

这样:

- 边界声明单点修改,description 不需要同步
- 避免 "description 漏写 design.md / spec.md" 类漂移错误(Oracle DIMENSION 6 BLOCKING)

### Decision 4: Token 预算 — ≤ 200 tokens

description 字段预算 ≤ 200 tokens(约 800 字符)。理由:

- AI agent 在每次 skill 选择时都会读 description,过长会挤占决策上下文
- OpenCode `available_skills` 列表展示时,过长 description 会换行截断
- 当前 rdd-builder v1 描述 ~380 tokens,Oracle 评审后 v3 精简到 ~150 tokens,验证可行

精简优先级(高 → 低):

1. 删 Owns/Not owns 复制(Dim 6 BLOCKING)
2. 删 anti-trigger 列表(Dim 2/10 BLOCKING)
3. 删 ADR 引用尾注
4. 合并语义重复的句子

### Decision 5: 反向 fallback 的处理 — 不在 description 引导

description 不引导 agent 走 deprecated / legacy 入口(如 propose 子技能 / `.plan-handoff.json` fallback):

- 实施层 fallback 仍存在(Wave 1 coexistence per ADR-0048)
- 但 description 应保持 "严格守门" 语气,避免暗示 "可以绕 canonical 路径"
- 走 fallback 的 agent 由 guide 推荐器或显式 user instruction 触发

## 影响范围

### In Scope

- `skills/rdd-arch/SKILL.md` description
- `skills/rdd-planner/SKILL.md` description
- `skills/rdd-builder/SKILL.md` description ✅ (本 ADR 起草日已应用 v3 描述作为最小验证样本)
- `skills/rdd-verifier/SKILL.md` description
- `skills/rdd-quick/SKILL.md` description
- 21 个子技能 description(propose / execute / writing-plans / add-improve / deps / status / feature / roadmap / rdd-doctor / rdd-env-check / rdd-hub-bootstrap / rdd-session / rdd-workflow-brainstorm / cross-repo-protocol / sync-hub / watch-hub / report-issue / openspec-gate / contract-check / spoke-system-prompt-injection / INSTALL)

### Out Scope

- `_lib/` Python 模块(不读 description)
- `rddf` CLI 命令(从 skill 调用,不直接读 description)
- `role.boundaries` 字段本身(per ADR-0028 已是 SSOT,本 ADR 不重定义)
- `guide` skill 内部 recommender 实现细节(由 guide 自身维护)

## 备选方案

| 备选 | 理由 |
|------|------|
| 不写 ADR,逐 skill 修复 | 评估: 拒绝 — 无 SSOT,后续 25 个 skill 重写会反复犯同类错误 |
| 在每个 skill 写完整 TRIGGER + DO-NOT + Owns 段 | 评估: 拒绝 — anti-trigger N×N 重复 + boundary 复制 SSOT 漂移(Oracle BLOCKING) |
| **description 只讲正向触发 + 引用 role.boundaries + guide 集中反触发** | 评估: 接受 — 本 ADR 主张 |

## Consequences

### 正面

- description 平均 token 下降 40-60%(rdd-builder v1→v3: ~380→~150 tokens)
- 消除 Oracle BLOCKING 类型的 "事实反转" / "决策表误述" / "主旁路颠倒" 类错误
- 26 个 skill 维护成本下降(anti-trigger 单点维护)
- 触发条件更聚焦 → AI agent skill 选择更准确
- guide 反触发逻辑升级一次性影响所有 skill

### 负面 / 风险

- 第一次按本 ADR 重写 25 个 skill description 是大工作量,需要批量实施计划
- guide 升级时若漏改,会出现 description 与 recommender 行为不一致(需 test)
- 反触发从 "in 26 个 skill" 集中到 "in guide 1 处",guide 成为单点风险(需要 test coverage)

### 后续待办

- [ ] **rdd-builder v3 描述**作为最小验证样本 ✅ (2026-09-15 完成,见 SKILL.md L3-15)
- [ ] 主阶段 4 个 skill(rdd-arch / rdd-planner / rdd-verifier / rdd-quick)描述重写 — 待办
- [ ] 子技能 21 个描述批量套模板 — 待办
- [ ] `guide` recommender 升级:集中所有 26 个 skill 的反触发判断 — 待办
- [ ] 新增 bats 测试 `tests/integration/test_skill_description_convention.bats`:扫描所有 SKILL.md frontmatter,验证 ≤ 200 tokens + 无 anti-trigger 段落 + 引用 role.boundaries — 待办
- [ ] docs/architecture/v4-pipeline-data-flow.md 加 "skill description convention" 段 — 待办

## Migration / Backwards Compat

**No breaking changes**:

- description 字段是 advisory metadata,无 CI 测试 grep 其内容(per Oracle DIMENSION 9 验证)
- `role.boundaries` 字段(per ADR-0028)继续承担边界声明,本 ADR 仅禁止 description 复制
- 现有调用 skill 的代码 / 脚本 / 测试不依赖 description 字符串内容

**Behavior change**:

- AI agent 读 description 时信息更少,但更准确(无反事实)
- 之前依赖 description 中 "DO NOT use" 段做 routing 的 agent 需要改用 guide 推荐器

## Cross-references

- [ADR-0028](ADR-0028-role-model-per-phase.md) — `role.boundaries` SSOT 来源
- [ADR-0043](ADR-0043-rdd-workflow-v4-stage-merge.md) — 4 阶段架构,本 ADR 在其上约束 description 风格
- [ADR-0048](ADR-0048-v4-stage-merge-revision.md) §Decision 3 — 主旁路关系,description 必须正确反映
- [ADR-0049](ADR-0049-rdd-builder-phase0-llm-integration.md) Decision 2 — auto-decision 9 行表,description 引用时不能误述
- [ADR-0050](ADR-0050-rdd-builder-auto-pick-mode.md) — auto-pick 模式默认 ON

## References

- `skills/rdd-builder/SKILL.md` L3-15 — 本 ADR 起草日已应用的 v3 描述样本
- `skills/rdd-builder/SKILL.md` L36+ — `role.boundaries` SSOT
- `skills/guide/SKILL.md` — 反触发 SSOT 候选位置
- Oracle review session `ses_f5bf53e0bffemcDQZvdcZQmweW` — 2026-09-15 rdd-builder description 审查
- `docs/adr/README.md` — ADR 索引(本 ADR 起草后,索引末尾追加 ADR-0051 行)
