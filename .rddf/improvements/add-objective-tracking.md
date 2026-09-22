---
优先级: P1
来源: 2026-09-22 用户发起 — 借鉴 HydraForge Master Plan 思路，在保持现状 features/phases 框架不动的前提下，新增"复杂目标跟踪"工件类型
阶段: phase-3
分类: governance
类型: feature
主题: 流程定制层
roadmap_ref:
  project_id: 流程定制层
  phase: phase-3
---

**优先级**: P1 | **来源**: 2026-09-22 用户发起 — 借鉴 HydraForge Master Plan 跟踪文档思路，新增第 3 类工件 `objective`（跨 sprint 复杂目标跟踪）

**阶段**: phase-3 | **分类**: governance | **类型**: feature

**主题**: 流程定制层

## 架构依据

### 现状痛点

rdd-workflow 现有 roadmap 工件体系（v2.2+）：

| 工件 | 路径 | 维护模式 | 适用场景 |
|------|------|----------|----------|
| 主文档 | `.rddf/roadmap.md` | 半自动（rdd-arch CLI） | 阶段骨架 + AUTO-INDEX 索引 |
| Phase fragment | `.rddf/roadmap/phases/*.md` | 手工 | 阶段定义 |
| Feature fragment | `.rddf/roadmap/features/*.md` | **derived view**（零手工） | 跨 phase 聚合当前状态 |

**真实缺口**：当一个"复杂目标"需要**多个 sprint + 多个 feature + 多个 openspec change**协同推进时（如 `bypass-audit-mechanism + hub-federation governance` 这种跨 sprint deferred objective），没有对应的"目标级跟踪工件"：

- feature fragment 是 derived view，无法承载 planner 的手工修订意图（§Why we changed, §deferral rationale）
- openspec/changes 是单 change 视角，无法跨 change 给出"目标完成度"全景
- 主文档 `.rddf/roadmap.md` 是状态快照，无历史轨迹

### 借鉴对象：HydraForge Master Plan

外部参考（`/workspace/project/HydraForge/docs/roadmap/2026-09-16-pdk-chat-demo-evolution-roadmap.md`，984 行）展示了"单文档 Master Plan 跟踪复杂多 sprint 目标"的可读价值（依赖图、复盘表、调整日志）。但其**单文档 13 章节**模式与 rdd-workflow **分片 + derived-view** 哲学冲突。

### Oracle 审查结论（2026-09-22，ses_f37f04c17ffe）

经 2 轮 Oracle 咨询确定：
1. **命名**：`objective`（而非 `program`/`track`/`initiative`）— 精确对齐用户用语"复杂目标"
2. **与 feature fragment 区别**：feature = derived view（零手工聚合）；objective = 手工维护的 source-of-truth（planner 修订意图层）
3. **执行链路 90% 已存在**：planner→builder P0→execute→verifier→archive 全链路覆盖；缺的是"objective 文件创建/修订/消费"3 个读写点
4. **协作模式**：串行（planner 填 → builder 创建 change → execute → verifier → planner 复盘）
5. **planner 唯一写入点**：避免 builder/execute 隐式写 objective 侵蚀 rdd-planner 单门控（ADR-0028）

### 与现有架构的关系

- **rdd-planner owns 扩展**：`roadmap.md + features/*.md + phases/*.md` 已 owns，新增 `objectives/*.md` 不违反现有边界
- **AGENTS.md 关键术语对照表**：当前区分"improvement（5 段草稿）vs openspec proposal"。本次新增第 3 类术语 "objective" 不冲突，因为 objective **不创建 change**，只跟踪跨 sprint 目标
- **rdd-arch 完全脱离 roadmap**（per ADR-0048）：本次不动 rdd-arch
- **rdd-builder NOT owns roadmap.md**（per SKILL.md line 44）：本次不动 builder

## 范围

**In Scope**：

### A. 新工件 `.rddf/roadmap/objectives/<name>.md`

骨架（11 段 → 实际 6-7 个手写单元）：

```markdown
---
id: objective-<name>
status: active | deferred | completed | archived
created: <YYYY-MM-DD>
last_revised: <YYYY-MM-DD>
review_by: <YYYY-MM-DD>          # D2 90 天 grace 机器可执行锚点
owner: rdd-planner
priority: P0 | P1 | P2
manual_deps: [<objective_id>]    # ADR-0022 复用
supersedes: <objective_id>       # 替代链
theme: <一句话目标>
---

## 1. 驱动诊断（Why now）          [必有；含适用场景]
## 2. 目标愿景 + 完成判据           [必有；末尾 2-3 条 done-when]
## 3. 架构依据                      [条件必有：有 ADR 必引用，否则写"无"]
## 5. 反例（本 objective 语境专属）  [可选；通用反例去 AGENTS.md/ADR]

## 9. 目标依赖与 Decision Gate
### 9.1 前置 objective 依赖         [手工，2-3 节点可维护]
### 9.2 Go / No-Go Decision Gate    [deferred objective 的全文核心]
### 9.3 跨 objective 影响
### 9.5 DAG snapshot（可选）        [仅 sprint 复盘时写；格式：转录 + 时间戳 + regenerate 命令]

## 10. next_sprint_candidates       [候选非指令；deferred 时允许 "N/A — <理由>"]

## 11. 跟踪台账（append-only）       [合并原 §6+§11；唯一时序记录]
| Sprint | kind | 内容 | Decision/调整 | 原因 |
  # kind ∈ deferral-rationale | go-decision | sprint-review | scope-change | adr-amendment
```

**硬性规则（写进 schema 注释）**：
- "纯结构聚合用 feature（免费、自动、零维护）；需要跨 sprint 目标叙事与复盘记录才建 objective（手工、planner 季度修订）"
- §6 / §7 / §8 不内嵌：分别为 derived view（rddf roadmap show-objective 实时派生），文件内只保留一行 `> 关联实体由 CLI 派生`
- §3 引用 ADR **必有**：本仓库 ADR 文化强，无架构锚点的 objective 视为策划失职

### B. CLI 子命令（`rddf roadmap` namespace）

```
rddf roadmap list-objectives              # 列出所有 objective（含 status 过滤）
rddf roadmap show-objective <id>          # 渲染完整 objective（含 derived view 渲染 §6/§7/§8）
rddf roadmap add-objective <id> ...       # 创建新 objective（生成 frontmatter + 骨架）
rddf roadmap revise-objective <id>        # 交互式修订（sprint 复盘仪式）
rddf roadmap archive-objective <id>       # 90 天 grace 后归档到 objectives/archive/
rddf roadmap deps-objective <id>          # 派生 §7/§8/§9.5 DAG（CLI 实时输出）
rddf roadmap snapshot-objective <id>      # 把 deps 快照写入 §9.5（仅 sprint 复盘时允许）
```

### C. Schema 落盘

`_lib/schemas/objective_schema.json` (version 1)：
- frontmatter 字段 9 个：id/status/created/last_revised/review_by/owner/priority/manual_deps/supersedes/theme
- section 校验：6-7 个手写单元（§1§2§3(条件)§5(可选)§9§10§11）
- kind 枚举 5：deferral-rationale / go-decision / sprint-review / scope-change / adr-amendment
- "N/A — <理由>" 格式约束：禁止静默留空

### D. rdd-doctor 新增 2 个巡检类别

- `objective-lifecycle`：检查 `review_by` 到期 + grace 状态
- `objective-structure`：检查结构不变量（kind 在枚举、日期单调、必填段非空）
- ❌ **不**加 `objective-evidence-drift` 新鲜度巡检——D2 grace 已覆盖停滞语义，避免 doctor 退化为考勤机

### E. rdd-planner 接入（2 个读写点）

- **planner_stage_exit.sh** 末尾追加：刷新 AGENTS.md `<!-- AUTO-OBJECTIVES -->` 哨兵段（与现有 AUTO feature fragments / sprint 同模式）
- 新增 `planner_objective_revise.sh` 子脚本：交互式修订界面（生成 next_sprint_candidates 候选 + 追加台账行）
- rdd-planner/SKILL.md 在 phase 列表加 §objectives 治理段（含"何时建 feature / 何时建 objective"决策规则）

### F. PoC 验收

双跑验证动态机制：
1. `objective-bypass-audit-hub-governance.md`（**deferred**）— 验证 §9.2 + N/A 格式 + 跨 repo 快照
2. `objective-onboard-new-skill.md` 或类似小目标（**active**）— 验证 §11 台账 append + §10 候选填充

每个 PoC 必须至少完成：1 次 sprint 复盘台账写入 + 1 次 deps 快照生成 + 1 次 review_by 设定。否则动态机制零覆盖。

### G. 文档

- `AGENTS.md`：新增"objective 工件"段（含 feature vs objective 决策表）
- `docs/adr/ADR-NNNN-objective-tracking.md`：新 ADR（编号取 `docs/adr/` 当前最大值 +1）
- ADR 含与 feature fragment / openspec change / improvement 4 工件区分矩阵

**Out of Scope**：

- **不修改** `rdd-arch`（per ADR-0048 完全脱离 roadmap）
- **不修改** `rdd-builder` 的 role.boundaries（builder 不写 objective）
- **不创建** 独立的 evidence/ 子目录（v0.2 升级触发条件显式：单 objective evidence >20 条 或 需跨 repo 引用）
- **不引入** 自动升级 objective 状态为 change（planner 手工判定）
- **不实现** objective-level AC 验证（objective 不替代 change 验证，仅作跨 sprint 跟踪）
- **不内嵌** change-level ASCII DAG（用 §9.5 日期戳快照 + `rddf deps` 派生）
- **不修改** feature fragment 现有 schema 或 CLI（保持 derived view 零维护）
- **不删除或迁移** `.rddf/roadmap/features/` 已有内容（向后兼容）

## Why

- **现状痛点**：跨 sprint 复杂目标（如 `bypass-audit-mechanism + hub-federation governance` 已在 feat-fix-archive-gaps-v2 §22 显式 deferred 至 v3.2，但无文件跟踪其进展）只能靠 feat fragment 或隐式 session 记忆，一旦延期就消失在 git history
- **修复价值**：让 rdd-planner 有"目标级"工件可写，让跨 sprint 推进有可审计的 source-of-truth
- **Why now**：Oracle 第二轮已对 D4/D5/D6/PoC 给出明确裁决（参见 `ses_f37f04c17ffe`），设计层面已收敛；infra 方面 `add-improve` 已支持 7 段硬门控、`rdd-planner` 已 owns `roadmap.md`、feature fragment 模式可类比

## What Changes

| 文件/路径 | 类型 | 行数估算 |
|-----------|------|----------|
| `skills/roadmap/SKILL.md` | 扩 | +200（7 个新 CLI + objective 概念段） |
| `skills/roadmap/scripts/` | 新 | +300（5 个 CLI wrapper） |
| `_lib/objective.py` | 新 | +250（schema + parser + derive） |
| `_lib/schemas/objective_schema.json` | 新 | +120 |
| `_lib/cli/objective_cmd.py` | 新 | +180 |
| `_lib/cli/__init__.py` | 改 | +1（路由） |
| `skills/rdd-planner/SKILL.md` | 扩 | +50（objectives 治理段） |
| `skills/rdd-planner/scripts/planner_stage_exit.sh` | 改 | +10（哨兵段刷新） |
| `skills/rdd-planner/scripts/planner_objective_revise.sh` | 新 | +80 |
| `skills/rdd-doctor/scripts/checks/objective_lifecycle_check.py` | 新 | +120 |
| `skills/rdd-doctor/scripts/checks/objective_structure_check.py` | 新 | +100 |
| `skills/rdd-doctor/scripts/doctor.sh` | 改 | +2（注册 2 类别） |
| `AGENTS.md` | 扩 | +30（objective 段） |
| `docs/adr/ADR-NNNN-objective-tracking.md` | 新 | +150 |
| `.rddf/roadmap/objectives/objective-bypass-audit-hub-governance.md` | 新 | ~60（PoC） |
| `.rddf/roadmap/objectives/objective-onboard-new-skill.md` | 新 | ~40（PoC） |
| `tests/unit/test_objective_schema.py` | 新 | +200（≥10 case） |
| `tests/unit/test_objective_parser.py` | 新 | +150 |
| `tests/integration/test_objective_lifecycle.bats` | 新 | +120 |
| `tests/integration/test_objective_structure.bats` | 新 | +100 |
| `tests/integration/test_rdd_planner_objective.bats` | 新 | +80 |

**合计**：~2340 行新代码 + 约 100 行改造。

## Acceptance

### 工件契约
- [ ] `.rddf/roadmap/objectives/` 目录存在，frontmatter 9 字段全部覆盖（含 `review_by` / `supersedes`）
- [ ] objective 文件 6-7 个手写单元齐全（§1§2§3条件§5可选§9§10§11）
- [ ] §11 跟踪台账 kind 枚举 5 项（deferral-rationale / go-decision / sprint-review / scope-change / adr-amendment）
- [ ] "N/A — <理由>" 格式：deferred objective 的 §10 必填项允许此格式，禁止静默留空

### CLI 契约
- [ ] `rddf roadmap list-objectives` 列出所有 objective，支持 status 过滤
- [ ] `rddf roadmap show-objective <id>` 渲染完整内容含 derived view（§6/§7/§8 由 CLI 实时派生）
- [ ] `rddf roadmap add-objective <id> --theme "..."` 生成 frontmatter + 骨架
- [ ] `rddf roadmap revise-objective <id>` 交互式修订 + 自动追加 last_revised
- [ ] `rddf roadmap snapshot-objective <id>` 写入 §9.5 时间戳快照（含 `> Snapshot derived at <date>, regenerate: rddf deps <objective>`）

### Schema
- [ ] `_lib/schemas/objective_schema.json` version 1 存在
- [ ] frontmatter 校验：9 字段类型 + 必填/可选 + enum
- [ ] section 校验：必填 vs 可选 vs 条件必有 vs 允许 N/A

### Doctor 巡检
- [ ] `bash skills/rdd-doctor/scripts/doctor.sh --category objective-lifecycle` 检查 `review_by` + grace 状态
- [ ] `bash skills/rdd-doctor/scripts/doctor.sh --category objective-structure` 检查结构不变量
- [ ] ❌ **不**实现 `objective-evidence-drift` 新鲜度巡检（保持 doctor 结构检查器本质）

### Planner 接入
- [ ] rdd-planner/SKILL.md 含"何时建 feature vs objective"决策规则
- [ ] `planner_stage_exit.sh` 末尾刷新 AGENTS.md `<!-- AUTO-OBJECTIVES -->` 哨兵段（与 feature fragments 模式一致）
- [ ] `planner_objective_revise.sh` 子脚本：交互式修订界面

### PoC 双跑（动态覆盖）
- [ ] `objective-bypass-audit-hub-governance.md`（deferred）：§1 §3 §5 §9.2 填实，§10 显式 `N/A — deferred 至 v3.2`，§11 含初始 deferral-rationale 行
- [ ] `objective-onboard-new-skill.md` 或同类（active）：§11 含 ≥1 次 sprint-review 台账行，§10 含 ≥1 条 next_sprint_candidate
- [ ] 每个 PoC 至少完成：1 次 sprint 复盘台账写入 + 1 次 deps 快照生成 + 1 次 review_by 设定

### 测试
- [ ] `tests/unit/test_objective_schema.py` ≥10 case 全绿
- [ ] `tests/unit/test_objective_parser.py` ≥6 case 全绿
- [ ] `tests/integration/test_objective_lifecycle.bats` ≥4 case 全绿
- [ ] `tests/integration/test_objective_structure.bats` ≥4 case 全绿
- [ ] `tests/integration/test_rdd_planner_objective.bats` ≥3 case 全绿
- [ ] `./test.sh --full --regression` 无新增失败（对齐 AGENTS.md 归档前回归门）

### 文档
- [ ] 新 ADR 落盘 `docs/adr/ADR-NNNN-objective-tracking.md`，编号为当前最大值 +1
- [ ] ADR 含 4 工件区分矩阵（roadmap 主文档 / phase fragment / feature fragment / objective / openspec change）
- [ ] AGENTS.md 加 objective 段（含 feature vs objective 决策表 + 与 improvement/openspec 区分）

### 兼容性
- [ ] 既有 feature fragment / phase fragment / 主文档 AUTO-INDEX 行为零变化
- [ ] 既有 rdd-arch / rdd-builder / rdd-verifier 不修改
- [ ] `rddf doctor` 11 类既有巡检结论不变

## Capabilities

### MUST
- 由 rdd-planner 创建 / 修订 / 归档 objective 文件
- objective 文件支持 manual_deps（ADR-0022 复用）+ supersedes 替代链
- §11 跟踪台账 append-only，包含 5 种 kind
- "N/A — <理由>" 格式：deferred objective 的 §10 允许此格式
- §6 / §7 / §8 由 CLI 实时派生（不手写）
- §9.5 DAG snapshot 由 planner 在 sprint 复盘时写入（含时间戳 + regenerate 命令）
- review_by 字段：90 天 grace 触发 archive-objective
- rdd-doctor 2 新类别（lifecycle + structure）仅做结构检查

### MUST NOT
- rdd-arch / rdd-builder / rdd-verifier 写 objective 文件
- 内嵌 change-level ASCII DAG（仅允许 §9.5 日期戳快照）
- 引入自动升级 objective 为 change 流程（planner 手工判定）
- 创建独立 evidence/ 子目录（v0.2 触发条件未到）
- 修改 feature fragment / phase fragment 既有 schema 或 CLI
- 修改 rdd-builder 的 role.boundaries

### SHOULD
- objective 文件总长（论证段）≤80 行；超 80 行 → doctor WARNING → 降级到 ADR 引用
- PoC 阶段限定 2 个 objective，验证后扩到 3-5 个常用场景
- review_by 默认 = created + 90 天

## Impact

### MUST（兼容性）
- 既有四阶段流程行为零变化（rdd-arch / rdd-planner / rdd-builder / rdd-verifier 各自 bats 全绿）
- `.rddf/roadmap/features/` 既有 60+ feature fragment 不受影响
- `.rddf/roadmap/phases/` 4 个 phase 文件不变
- `rddf doctor` 11 类既有巡检结论不变
- 不引入新 KNOWN_FAILURES 条目

### MUST（语义清晰）
- feature fragment 仍是 derived view（零手工），不被 objective 覆盖
- improvement 仍是 change 入口（5 段草稿），objective 不替代它
- openspec change 仍是单 change 视角，objective 跨 change 聚合但不生成 change

### MUST（planner 单门控）
- objective 文件写入权仅 rdd-planner（per ADR-0028 role.boundaries.owns 扩展）
- rdd-builder / rdd-verifier 在 P3 archive 后**不**自动写 objective §11（planner 在 sprint 复盘时手工追写）
- builder → planner 的反向通道（`.planner-feedback.json`）继续存在但不强制触发 objective 修订

### SHOULD（治理）
- 90 天 grace 触发 archive-objective 后，AGENTS.md AUTO-OBJECTIVES 段不再列出
- PoC 完成 1 个 sprint 后再做总评：是否需要调整骨架 / 是否需要 evidence 子目录升级
- 跨 repo objective 的依赖（DAG snapshot 价值最大）需手动标注跨 repo 边（rddf deps 静态分析覆盖不到）

### MUST NOT
- 不允许 rdd-builder P0 从 objective 文件直接生成 change（planner 仍必经 improvement 5 段草稿）
- 不允许 objective 文件污染 iteration.json / sessions.json（保持单一 SSOT）
- 不引入新 SSOT 文件（仅 schema + state 文件，无新持久化层）
