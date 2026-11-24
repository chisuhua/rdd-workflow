# Agent 角色对齐：治理角色层 vs 阶段技能层

> **For**: 在本仓写文件、评审 change、或给 agent 加权限的人。只想跑工作流的话，从 `../ONBOARDING.md` 开始即可，本页可以跳过。
>
> **本页不是真源。** 本页解释**两层角色体系的关系**；每一条事实的真源在别处，见下方真源排序。
> 本页与代码/契约不一致时，**以真源为准**，并把本页当作待修项。

## 真源排序（本页只解释，不复述）

| 主题 | 真源 | 本页的角色 |
|---|---|---|
| `role:` 字段结构 | `_lib/schemas/skill_role_schema.json` | 不复述字段 |
| owns / not_owns 的匹配算法 | `openspec/specs/skill-role-model/spec.md`（§ownership-entry-matching-semantics） | 不复述算法 |
| 「owns 只列本 skill 真正产出的工件」 | 同上（§skill-role-owns-generated-artifacts-only） | 只解释为什么它决定了下面的归属表 |
| 角色模型的决策理由 | `docs/adr/ADR-0028-role-model-per-phase.md` | 不复述决策 |
| 每个 skill 的 owns 全量清单 | 各自的 `skills/<name>/SKILL.md` frontmatter | 不复述清单 |
| `.rddf/` 布局与逐条目读写方 | **声明层** `_lib/core/rddf_layout.py`；**解释层** `rddf-layout.md`（与代码不一致时以代码为准） | 只做「治理位置」视角的速查 |
| opencode 侧角色矩阵（治理身份 / 审查配对 / 派发契约） | `~/.config/opencode/prompts/build.md`（快照日期见下） | 只给指针 + 命名消歧 |
| 两层解耦的决策 | `~/.config/opencode/docs/MULTI-AGENT-DESIGN.md` §2.6 | 只引用结论 |

> **快照声明**：本页关于 opencode 侧的描述对应 `prompts/build.md` 的 2026-11-17 状态。**活契约在 opencode 侧**；
> 本页只保留不随实现细节漂移的部分（命名、归属判定、双落点），权限实现、派发字段、kind 优先级一律不复述。

## 两个体系的坐标

仓库里存在**两套**名字相似但语义不同的角色体系，且**互不依赖**：

| | opencode **治理角色层** | rdd-workflow **阶段技能层** |
|---|---|---|
| 是什么 | 单会话内的**治理身份**，可切换 | 阶段**工件归属**声明 |
| 取值 | `architect` / `planner` / `builder` / `verifier` / `general` / `no-role` | `rdd-arch` / `rdd-planner` / `rdd-builder` / `rdd-verifier` / `rdd-quick` |
| 声明位置 | opencode 侧（本仓之外） | `skills/*/SKILL.md` frontmatter 的 `role:` 块 |
| 状态载体 | `.rddf/state/role.json`（消费方写，本仓不解析） | 无独立状态文件；阶段状态在 `.rddf/state/*handoff*.json` |
| 审查配对 | 每个角色有固定审查者 | 无审查者概念（只有产物归属） |

**关键**：rdd-workflow **不依赖** opencode —— 不装任何 AI 助手也能按 `SKILL.md` 完整工作。
两层的交集只有一条：opencode 侧把 rdd-workflow 当作**可选增强层**（装了就用对应 skill，没装走内置流程）。
也就是说「角色」是 opencode 的治理概念，「skill」是本仓的产物归属概念，**任何一方都不以另一方为前提**。

## 命名消歧

| 容易混淆 | 实际含义 |
|---|---|
| `architect`（角色） vs `rdd-arch`（skill） | 前者是**会话治理身份**（可写哪些文件由 opencode 侧配置决定）；后者是**阶段技能**，产物只有 `docs/adr/ADR-*.md`、`docs/architecture/*.md`、`.rddf/state/.arch-handoff.json` |
| `verifier`（角色） vs `rdd-verifier`（skill） | 前者负责**出验收报告**（落 `.rddf/reviews/`）；后者的产物是**记账**（`.rddf/state/verifier/**`）—— 见下一节 |
| `builder`（角色） vs `rdd-builder`（skill） | 前者权限覆盖全仓，**但两处例外**：不得单方面改已签批 ADR 的决策内容、被派发的 builder 类后端不写架构文档目录。后者的产物**全量见 `skills/rdd-builder/SKILL.md` 的 `owns`**，易错点是它**不** own `design.md`（由执行该 change 的 agent 撰写）也**不** own `.rddf/reviews/**` |
| `role_class` vs `current_role` | `current_role` = 治理身份；`role_class` = **被派发后端的能力类**（`builder` / `architect` / `verifier`），决定「能做什么」，**不改变治理身份** |

> `role_class` 的完整语义与越界判据在 opencode 侧 `prompts/build.md`；本仓对它的唯一决策见 `ADR-0034` §修订要点 2。

## 工件归属判定

给一条路径，按以下顺序判定「谁写」，**先命中先定**：

1. **在某个 skill 的 `owns:` 里** → 该 skill 写（清单在各 `SKILL.md`，本页不复述）。
2. **在 `.rddf/reviews/**`** → **角色层**（验收 / 评审 / 审计类报告；见下一节）。
3. **在 `.rddf/config/**`** → **外部工具**（消费方私有配置，rdd 不读不写不校验 —— 见 `rddf-layout.md` 的 `external-tool` 约定）。
4. **在 `_lib/core/rddf_layout.py` 的 `RDFF_LAYOUT` 里有 `read_by`/`write_by`** → 按 manifest；**manifest 声明两者都写时**（如 `state/`），逐文件归属按 `rddf-layout.md` 的文件级表。
5. **都不命中** → 未认领。新增前先登记 manifest（否则 `rddf doctor --category layout` 只给 INFO）。

样例：

| 路径 | 写方 | 依据 |
|---|---|---|
| `docs/adr/ADR-0001-*.md` | `rdd-arch` | `skills/rdd-arch/SKILL.md` 的 `owns` |
| `.rddf/improvements/<name>.md` | `rdd-planner` | `skills/rdd-planner/SKILL.md` 的 `owns` |
| `openspec/changes/<name>/tasks.md` | `rdd-builder`（`rdd-quick` 在 mode a 下也可一次性生成） | 两个 skill 的 `owns`；文件级优先于目录级 |
| `.rddf/state/verifier/<name>.json` | `rdd-verifier` | `skills/rdd-verifier/SKILL.md` 的 `owns` |
| `.rddf/reviews/<name>-verify.md` | **角色层**（verifier 角色） | 不是任何 skill 的产物；见下节 |
| `.rddf/config/arch-docs.json` | **外部工具**（architect 角色的配置） | manifest 的 `external-tool` |

## verifier 双落点

`verifier` 这条链路**故意分成两份落点**，它们用途不同、写方不同、生命周期也不同：

| 层 | 落点 | 写方 | 用途 | 进 git 吗 |
|---|---|---|---|---|
| **记账落点** | `.rddf/state/verifier/**`（文件清单的真源是 `_lib/verifier/state_paths.py` 的 `SKILL_OWNS_PATHS`） | `rdd-verifier` skill | 判决缓存（归档门的输入）、重试状态、审计流 | ❌ runtime-only，gitignored |
| **产品落点** | `.rddf/reviews/<change>-verify.md` 等 | **executing / auditing agent**（角色层） | 给人读的验收报告（判据来源、逐条证据、失败路由建议） | ✅ committed |

**为什么产品落点不在任何 skill 的 `owns` 里**：`owns` 只声明**本 skill 实际产出**的工件
（`skill-role-model/spec.md` 的 `skill-role-owns-generated-artifacts-only`）。
先例是 `design.md`：`rdd-builder` 的脚本不写它 ⇒ `owns` 不认领，但 SKILL.md 正文必须声明「由执行该 change 的 agent 撰写」。
`.rddf/reviews/**` 完全同构：本仓代码全仓**不读不写**它，所以由角色层认领，skill 只在正文里声明作者。

两个直接推论：

- **不要让 skill 去写 `.rddf/reviews/`**，也不要因为「snapshot 里看见这个文件」就把它加进某个 `owns`。
- **归档门只认记账落点**（`.rddf/state/verifier/.ac-verdict-<change>.json`）；产品落点写得再漂亮也不影响归档判定。

## 派发模型（浅）

opencode 可以把一个工程会话**派发**出去做一类工作。本仓能自证的事实只有三条：

1. **被派发后端的能力类**（`role_class`）决定允许写什么；越类要交回主会话，不在 session 内换类。完整判据在 opencode 侧。
2. **本仓对它的唯一决策**是 `ADR-0034` §修订要点 2：verifier 后端的写集上限是 `.rddf/state/verifier` 这个**目录** —— 这正是当初把 verifier 状态从 `.rddf/state/` 根下收拢进单一命名空间的原因。
3. **交回 / 反馈走 `rddf feedback add`**（single writer，`ADR-0037`；实现 `_lib/cli/feedback_cmd.py`）。kind 词表与「HANDOFF 首行」契约在 opencode 侧，本页不复述。**只记一条差集事实**（可机读真源：`_lib/feedback_appender.py` 的 `VALID_KINDS`）：`rddf feedback add` 接受 5 个 kind，其中 HANDOFF 只承载 3 个；两者**不是同一套词表**，不要互相映射。

> 不写：拒绝派发的条件、`kind` 优先级、HANDOFF 正文 5 项、权限实现。那些是 opencode 治理面的内部机制。

## `.rddf/` 治理位置速查

只列**治理层**关心的条目（全量见 `rddf-layout.md`）：

| 路径 | manifest 声明 | 存在要求 | 本仓解析它吗 |
|---|---|---|---|
| `.rddf/state/` | `state` 条目：`read_by = rdd`，`write_by = rdd, agent` | `always`（要求的是**目录**） | rdd 读写自身状态；治理文件不解析 |
| `.rddf/state/role.json` | 落在 `state` 条目下 | 文件本身由消费方按需创建 | ❌ 不解析 |
| `.rddf/state/pair.json` | 落在 `state` 条目下 | 未启用派发时不存在属**正常** | ❌ 不解析 |
| `.rddf/reviews/` | `reviews` 条目：`read_by = agent`，`write_by = agent` | `never`（不要求存在） | ❌ 不读内容、不写文件（manifest 有一条登记） |
| `.rddf/config/` | `config` 条目：`read_by = external-tool`，`write_by = external-tool` | `never` | ❌ 不读不写不校验 |

三条约定：

- **这两个文件不存在 ≠ 布局缺失**。消费方没启用治理层时它们本来就不该出现；manifest 里 `state/` 要求存在的是**目录**，不是目录里的每个文件。
- **`RDDF_STATE_DIR` 重定向不搬家治理路径** —— 清单描述的是路径约定，不是可重定向的运行时配置（见 `rddf-layout.md` 的「边界」段）。
- **`reviews/` 是 committed**：会进 git、会被 review，但 rdd 只登记不消费。现实里不止「验收报告 / 审稿报告」两类，还有 blocked 记录、discovery 记录、审计报告 —— 都属同一落点。

## 不复述清单

本页**故意不写**下面的内容，去这些地方看：

- `role:` 字段结构（title / perspective / boundaries / human_involvement）→ `_lib/schemas/skill_role_schema.json`
- owns / not_owns 的规范化与匹配算法、文件级 vs 目录级优先级 → `openspec/specs/skill-role-model/spec.md`
- 「owns 只列真正产出的工件」的规范性要求 → 同上；先例（`design.md`）见同 spec 的 Scenario
- 各 skill 的 owns 全量清单 → `skills/<name>/SKILL.md` frontmatter
- verifier 的记账文件清单与其 schema → `skills/rdd-verifier/SKILL.md`「State Files Owned」+ `_lib/verifier/state_paths.py`
- `role.json` / `pair.json` 的 schema 字段 → opencode 侧
- 派发能力类的越界判据、HANDOFF 契约、`kind` 优先级 → opencode 侧
- opencode 侧角色矩阵、审查配对、治理面文件作用域 → `~/.config/opencode/prompts/build.md`
- 角色模型的演进史 → `historical-evolution.md`

> **命名同步状态**：`openspec/specs/skill-role-model/spec.md` 已于 2026-11-24 同步到 v4 命名
> （`rdd-arch` / `rdd-planner` / `rdd-builder` / `rdd-verifier`，`rdd-quick` 是旁路）—— 按 spec 里的
> `guide-*` grep 现在只命中 **2 处带 `v4-residue:allow=rename-history` 豁免标记的历史注记**（记的是旧名，
> 不是活调用）。读的时候不需要做名字替换。

## 过期信号

本页不是活契约，会过期。判断方法（分两类，**第二类本仓无法机检**）：

**本仓可机检的漂移**

- `docs/architecture/README.md` 的 Doc Map 里本页的「描述」还准不准 —— 主题变了就该改那一行；
- 本页「真源排序」表里任一真源已被取代（看 ADR 的 `Status` 是否变成「已替代为」）；
- 本页「命名消歧」表里任一侧改了名字或增删了角色；
- `RDFF_LAYOUT` 里 `reviews` / `config` / `state` 三者的 `(read_by, write_by)` 变了（`tests/unit/test_agent_role_alignment_doc.py` 会红 —— 该测试解析行内 `read_by = …` / `write_by = …` 单元格并与 manifest 做**列表全等**，增删 role 都会红）。

**本仓无法机检的漂移（跨仓触发：任一命中就重拍快照）**

`~/.config/opencode/docs/MULTI-AGENT-DESIGN.md` 的版本变更，或 `~/.config/opencode/prompts/build.md` 的角色表 / 审查配对表 / `role_class` 取值集 / kind 词表变更。

> **已知不可机检面**（不装 opencode 就没有真源可比，所以不写断言、只列出来让人知道要去看）：
> 角色取值集、审查配对关系、`role_class` 的三种取值、HANDOFF 与 feedback 的 kind 差集、治理面文件作用域表。
> 这五项**故意不加测试** —— 加了会与本仓「不装 opencode 也能完整工作」的定位冲突，且 CI 环境无该路径。
