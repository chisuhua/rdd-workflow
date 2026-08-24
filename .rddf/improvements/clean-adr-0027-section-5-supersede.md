# clean-adr-0027-section-5-supersede

**优先级**: P2 | **来源**: Oracle 复核 2026-08-24(初版 P2-D + G6 + G7 + G8 文档对齐包)
**阶段**: v2.1.x | **分类**: docs | **类型**: chore

## 架构依据

Oracle 复核在审计 ADR-0027 实施现状时发现 4 个文档/对齐类问题(合成本 PR-6):

1. **ADR §5 Triage 设计缺 supersession 注**——§5 全文无替代说明;ADR-0029 (Issue-Driven Proposal Creation) 实际取代了它
2. **ADR 文本漂移**——ADR §4 写 `normalize_for_hash` 在 `issue_reporter.py`,实际实现迁移到 `_lib/issue_dedup.py`(更合理,但 ADR 需同步)
3. **测试文件命名漂移**——审计报告中提到 `tests/integration/test_feedback_loop.bats`,实际不存在;真实文件是 `test_archive_close_dual_mode.bats`
4. **`_classify_interrupted_phase` 用了 ADR §1.1 没列的 `phase-interrupted` 类别**——分类 taxonomy 微漂移

加上 **G6**:ADR §3 / §6 / §8 承诺的配套工件(`issue_reporter_schema.json`、`.issue-reporter.json` state、`.reporting-config.json` 缓存、一次性 banner)全部**未实现**——但 `.rddf.json` 的 `reporting` namespace env-var fallback 已能工作。

**Oracle 建议**(审计原文 §5.6 PR-6):「对 Gap 6 做显式取舍(推荐:ADR 中删掉 `.issue-reporter.json`/`.reporting-config.json`/banner 承诺而非补实现——现状 env-var 方案已够用)」。

## 范围

### In Scope

1. **PR-6.1**:`docs/adr/ADR-0027-continuous-evolution-feedback-loop.md` §5 末尾新增 supersession 注,明确指出设计由 ADR-0029 (Issue-Driven Proposal Creation) 替代
2. **PR-6.2**:ADR-0027 §4 "GitHub issue title 模板"段更新文本——指明 `normalize_for_hash` 实现位置改为 `_lib/issue_dedup.py`
3. **PR-6.3**:ADR-0027 §3 / §6 / §8 中**删除**以下承诺文本(对应 G6):
   - `.rddf/state/.issue-reporter.json` state 文件
   - `.rddf/state/.reporting-config.json` 配置缓存
   - `一次性 banner` 输出
   - `_lib/schemas/issue_reporter_schema.json`
   - `close_on_archive / retention_days / redact_patterns` 中 `retention_days`(保留 `close_on_archive` + `redact_patterns`)
4. **PR-6.4**:ADR-0027 §1.1 类别清单末尾追加 `phase-interrupted`(对应 G8),说明它是 `_classify_interrupted_phase` 在 orchestrator 接管场景下使用的细分
5. **PR-6.5**:`docs/architecture/improvement-check-mechanisms.md` 6. 参考段同步微调——增加指向 ADR-0029 的明确说明;`tests/integration/test_feedback_loop.bats` 不存在的错误在原 audit 文本中标"待修订"(可选,非阻断)
6. **PR-6.6**:`docs/adr/README.md` ADR-0027 行的"关键决策"列更新——增加"§5 由 ADR-0029 替代" 注脚

### Out of Scope

- **不**重写 ADR-0027 全文(只新增 supersession 注,保留原始决策动机便于追溯)
- **不**新增 ADR-0029(已存在)
- **不**实现 G6 中删除的工件(明确决策为不实现)
- **不**改 `_classify_interrupted_phase` 实现(仅在 ADR §1.1 增加该类别名,实现已存在)
- **不**改 Oracle 复核报告原文(只更新本提案的交叉引用)
- **不**动 Oracle 复核 session `ses_fcd821b6dffec9xoFJ515aq5Eo` 的产物(只更新引用)

## 关键场景

### 场景 A:用户读 ADR-0027 时不被旧 Triage 设计误导

**GIVEN** 用户读 ADR-0027 §5 "Triage - guide-design / guide-arch 消费 issue"
**WHEN** 翻到 §5 末尾
**THEN**
- 看到 supersession 注,提示设计已由 ADR-0029 替代
- 不需要逐字读 ADR-0029;知道 §5 是设计历史,真正路径看 ADR-0029

### 场景 B:`.rddf.json::reporting.retention_days` 用户不被误导

**GIVEN** 用户阅读 ADR-0027 §3 "默认配置"
**WHEN** 看到 YAML 示例
**THEN**
- **不**看到 `retention_days: 30`(本提案删除该字段)
- 看到注释:`retention_days 因 prunable code path 不可达,本 ADR 已删除承诺`
- 不会被过期字段误导配置

### 场景 C:实施者查询 schema 路径

**GIVEN** 实施者读 ADR §6 "schema 版本"段
**WHEN** 寻找 `issue_reporter_schema.json`
**THEN** **不**存在该 schema 文件;改为看到注释:`配套 schema 改为依赖现有 _lib/schemas/config_schema.json 的 reporting namespace;issue_reporter 不再单独维护 schema`

### 场景 D:实施者读 ADR §1.1 类别清单

**GIVEN** 用户或新实施者准备扩展 issue 类别
**WHEN** 翻看 §1.1
**THEN**
- 看到 `flow-bug / gate-failure / phase-crash / manual / phase-interrupted`(5 类)
- 知道后 1 类由 orchestrator 接管场景使用

## 技术约束

### Supersession 注写法

```markdown
> **2026-08-24 supersession 注**(Oracle 复核 sess_fcd821b6dffec9xoFJ515aq5Eo):
> 本节 "Triage - guide-design / guide-arch 消费 issue" 的原始设计
> (`guide-design` Phase 2 选项 4 "📨 triage 上游 issue" + `issue_to_proposal.sh`)
> 已被 [**ADR-0029 (Issue-Driven Proposal Creation)**](ADR-0029-issue-driven-proposal-creation.md) 替代。
> 实际当前路径:`guide-design` Phase 2 选项 3 "🐙 从 GitHub issue 创建提案"
> + `add-improve --from-issue` + 完整 brainstorm → proposal → archive 流程。
> 功能等价但用户路径更直接。
```

### 删除工件须保留动机

每段删除都要在变更 commit message 中保留"删除原因"指向本提案,**不在** ADR 中留痕(防 ADR 文档反复添加废弃历史)。

### 类别清单追加 `phase-interrupted`

```markdown
### 1.1 类别清单

| 类别 | 含义 | 上报? |
|------|------|------|
| `flow-bug` | rdd-workflow 自身 bug | ✅ |
| `gate-failure` | gate 逻辑错误 | ✅ |
| `phase-crash` | phase 抛未捕获异常 / exit code 非 0 | ✅ |
| `manual` | 用户显式 `rddf report-issue` | ✅ |
| **`phase-interrupted`** | orchestrator 接管场景下检测到的 phase 中断(SIGKILL 残留 trace) | ✅ |
```

## 验收标准

### 功能验收

- [ ] **AC-1**:ADR-0027 §5 末尾含 supersession 注,链接 ADR-0029
- [ ] **AC-2**:ADR-0027 §4 中 `normalize_for_hash` 实现位置改为 `_lib/issue_dedup.py`
- [ ] **AC-3**:ADR-0027 §3 / §6 / §8 删除 `.issue-reporter.json` / `.reporting-config.json` / banner / `issue_reporter_schema.json` 承诺
- [ ] **AC-4**:`retention_days` 配置字段从 ADR §3 默认配置示例删除
- [ ] **AC-5**:ADR-0027 §1.1 类别清单扩展为 5 类(含 `phase-interrupted`)
- [ ] **AC-6**:`docs/architecture/improvement-check-mechanisms.md` 交叉引用更新(含本提案 link)
- [ ] **AC-7**:`docs/adr/README.md` ADR-0027 行的关键决策增加 "§5 由 ADR-0029 替代" 注脚

### 测试

- 本提案**纯文档变更**,无功能代码改动 → **无需测试**。

### 不变量

- 不修改 ADR-0027 决策动机段落(只补 supersession 注 + 必要的实现位置说明)
- 不修改 Oracle 复核报告原文
- 不修改任何代码(`_lib/`、`skills/`、`tests/`)
- 不修改 `.rddf/state/*.json`(本提案不触发任何 state 写入)

## 依赖

- **前置**:无
- **依赖**:无
- **后续**:可与"ARCH-0029 用户教育"提案配对,但属另一主题

## 关联

- **父提案**(本提案关联的 audit):[Oracle 复核记录 2026-08-24](docs/architecture/improvement-check-mechanisms.md#五oracle-复核) §5.3 G6/G7/G8 + 5.2 P2-D
- **被引用 ADR**:
  - [ADR-0029](docs/adr/ADR-0029-issue-driven-proposal-creation.md) — Issue-Driven Proposal Creation(替代 §5 设计)
  - [ADR-0027](docs/adr/ADR-0027-continuous-evolution-feedback-loop.md) — 本提案修改对象
- **关联 standalone 改进**: 与 PR-1/PR-2/PR-3/PR-4/PR-5 完全独立
