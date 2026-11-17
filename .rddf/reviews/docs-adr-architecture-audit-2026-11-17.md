# docs/architecture + docs/adr 文档审查报告（2026-11-17）

> **角色**：verifier（只读审查；未修改被审查文档）
> **范围**：`docs/architecture/`（18 个 md）+ `docs/adr/`（61 个 md + README）
> **判据来源**：① 用户本次要求 ② ADR-0000 模板 + ADR-0060 形态契约 ③ `~/.config/opencode/prompts/build.md` 角色矩阵（治理面真源）④ 仓库代码现状（`skills/*/SKILL.md` frontmatter、`_lib/`、`openspec/specs/`）
> **证据要求**：每条判定至少一条 `file:line` 或命令输出；未取证的不写。

---

## 0. 结论摘要

| 维度 | 判定 |
|---|---|
| 链接完整性 | ❌ 5 处断链 |
| 索引一致性 | ❌ README Doc Map 漏 3 篇；ADR README 散文段落后 25 个 ADR |
| 与代码现状一致 | ❌ 9/18 architecture 篇含已删除 skill 名；37/61 ADR 含失效引用 |
| ADR 形态契约 | ❌ 存量不合规严重（但 ADR-0060 已声明「不追溯」） |
| **与 opencode 角色矩阵对齐** | ❌ **最大的系统性缺口**：rdd-workflow 侧完全没有镜像 opencode 侧的角色矩阵声明 |

**关键判断**：文档漂移不是随机噪声，而是**两个独立漂移源**——
① **产出侧漂移**（rdd-workflow 自身 v3→v4 演进而文档没跟上）；
② **跨仓漂移**（opencode 侧角色矩阵 v1.9→v2.2 演进而 rdd-workflow 侧零镜像）。
后者在 `docs/architecture` + `docs/adr` 中**完全没有落点**，是本次审查最需要修的部分。

---

## 1. 机械体检结果

### 1.1 断链（5 处）

| 位置 | 链接 | 实际应为 |
|---|---|---|
| `docs/architecture/rddf-layout.md:54` | `../../../adr/ADR-0026-...md` | `../adr/ADR-0026-...md`（多上两级） |
| `docs/architecture/v4-pipeline-data-flow.md:650` | `../../adr/ADR-0051-...md` | `../adr/ADR-0051-...md` |
| `docs/adr/ADR-0033-...md:6,216` | `../.rddf/improvements/submodule-aware-project-root.md` | 该 improvement 文件已不存在 |
| `docs/adr/ADR-0036-...md:6` | `../proposal-approved.md` | `../improvement-approved-format.md`（或对应 improvement） |

### 1.2 索引漂移

- `docs/architecture/README.md:13-26` Doc Map 只列 14 篇；目录实有 18 篇。**漏列**：`layer-0-progressive-context.md`、`guide-orchestrator-flow.md`、`rdd-arch-rdd-planner-integration.md`。
- `docs/architecture/README.md:34` 「last regenerated … as of v2.0.9+」← `package.json` 为 `4.0.0`；且其指向的 `historical-evolution.md` 时间线**止于 v2.1.0**（`historical-evolution.md:22-26`），v3/v4 无刷新锚点。
- `docs/adr/README.md` 索引表格本身由 `_lib/adr_index_generator.py` 生成且**逐条与 ADR 正文一致**（`tests/unit/test_adr_index_gate.py` 守着）——**表内无漂移**。漂移全在**生成块之外的散文**：顶部「v3.0+ 实施状态」表（`:10-23`，最大编号 0035，ADR-0036~0060 全缺席）、「主题分类」（`:159-193`，最大 0025）、「架构演进」（`:129-134`，止于 v4.0.1）、「上次同步: 2026-09-03」（`:260`，而 ADR-0060 日期 2026-10-28）。
- `docs/adr/README.md:23` 把 ADR-0014 记为「已采纳（设计稿）」，而 `ADR-0014:6` 与索引 `:43` 都是「待定」——**唯一一处方向相反的矛盾**。

### 1.3 垃圾文件

`docs/adr/ADR-0001-x.md` 全文 4 行（`---` / `status: 已采纳` / `---` / `X`）。
它不是随手误提交，而是 `docs/superpowers/plans/2026-08-07-guide-design-phase1-diagnostic.md` 里 7 处 `touch "$PROJECT_ROOT/docs/adr/ADR-0001-x.md"` 留下的**测试夹具**。代价：生产 ADR 目录里躺着一份伪 ADR，且迫使 6 处消费方硬编码跳过它（`_lib/adr_index_generator.py:28-29`、`tests/unit/test_adr_index_gate.py:25-28`、`tests/integration/test_adr_index.bats:43-45`、`test_adr_directory.bats:68-71,82,93,104`）。

---

## 2. docs/architecture 的问题

### 2.1 与代码现状不符（P0）

| # | 位置 | 问题 | 证据 |
|---|---|---|---|
| A1 | `overview.md:70` | rdd-arch 被描述为负责「ADR creation, **gap analysis**, roadmap」——gap analysis 已由 ADR-0057 删除；roadmap 已由 ADR-0048 划归 rdd-planner | `skills/rdd-arch/SKILL.md:34-36` 把 roadmap 列入 `not_owns`；`workflow-phases.md:54` 明写「rdd-arch is completely detached from roadmap」 |
| A2 | `overview.md:81-88` | Sub-skills 表的「Called by」列全是 `guide-design`/`guide-plan`/`guide-ship`/`guide-arch` | 这 4 个 skill 已由 ADR-0044 硬删除；`skills/` 下 0 个 |
| A3 | `overview.md:114-117` | 列出 `rddf discover-arch-artifacts` / `rddf env-check` / `archive-history` 三个不存在的子命令 | `_lib/cli/` 无 `discover_arch_artifacts_cmd.py` / `env_check_cmd.py`；`sessions_cmd.py` 只有 `list\|show\|current\|resume\|abandon\|gc` |
| A4 | `loop-engine.md:39,76` | `rddf session set-mode` 不存在；`rddf session resume` 漏 `--owner`（必填） | `_lib/cli/sessions_cmd.py:11-13,55` |
| A5 | `skills-and-handoff.md:88` / `rdd-arch-rdd-planner-integration.md:346` | 引用 `plan_intake.sh` —— 全仓零命中 | v4 已并入 `skills/rdd-builder/scripts/phase1_plan.sh` |
| A6 | `gates-and-quality.md:42-47` | arch_quality_gate 的 4 项检查名与代码不符（文档写 debt/alignment/clarity/actionable；代码是 `arch_alignment`/`adr_clarity`/`handoff_actionable`/`file_size`） | `_lib/arch_quality_gate.py:275,308,337,370,441` |
| A7 | `gates-and-quality.md:9` | 「Architecture proposals (ADRs, **gap analyses**)」—— gap analysis 工件已删除 | ADR-0057 §Decision |
| A8 | `skills-and-handoff.md:70` | 把 `.design-handoff.json` 当现行契约 | v4 已改 `.planner-handoff.json`（`skills/rdd-builder/SKILL.md:12`）；`state-and-events.md:59` 自己已注明 v4 命名变更 |

### 2.2 内部矛盾

- **roadmap 归属**：A1 —— `overview.md:70` 说 rdd-arch 写 roadmap，而 `workflow-phases.md:54` / `roadmap-organization.md:237` / `skills/rdd-arch/SKILL.md:34-36` 三处说 rdd-planner 独占。**3 比 1，overview 错**。
- **verifier 是第 4 还是第 5 阶段**：架构文档统一写 Stage 4（`workflow-phases.md:315`），但 `skills/rdd-verifier/SKILL.md:26,59` 自称「5th phase / 第 5 阶段」——**矛盾源头在 skill 自己**，架构文档在抄它。
- **阶段总数自相矛盾**：`overview.md:5` 同时写「5-stage lifecycle (`propose → plan → execute → status → archive`)」与「four-stage v4 architecture」，而 `overview.md:129` 又断言「任何写三阶段/五阶段的文档都是过时的」。

### 2.3 过时数字 / 版本

- 版本号 4 套并存：`README.md:34` v2.0.9+ / `improvement-check-mechanisms.md:191` v2.0.9 / `workflow-phases.md:5` v4.0.1 / `guide-orchestrator-flow.md:3` v4.2 / `docs/adr/README.md:84` v4.1，而 `package.json:3` = **4.0.0**。
- ADR 计数：`rdd-arch-rdd-planner-integration.md:187,222,256,308` 写「41 ADRs」「42 ADRs」，实有 ADR-0000~0060。
- skill 计数：`guide-orchestrator-flow.md:32` 「5 个 skill」，实际 `skills/` 下 28 个 SKILL.md。
- `roadmap-organization.md:327` 文档版本 2026-09-21，早于其引用的 ADR-0059（10-19）/ADR-0060（10-28）。

### 2.4 缺失的关键契约

| # | 缺失内容 | 应落点 |
|---|---|---|
| B1 | **verifier 双落点**（产品落点 `.rddf/reviews/` + 记账落点 `.rddf/state/verifier/`）—— 18 篇 architecture 文档**零处**提及 `.rddf/reviews/` 作为落点 | `workflow-phases.md` Stage 4 Outputs；`rddf-layout.md:26,47` 的 `reviews/` 条目 |
| B2 | **ADR-0060 形态契约 + `ARCH_SHAPE_CHECK` opt-in 门禁** —— architecture 目录零命中，但 `_lib/arch_quality_gate.py:441` 已是生效代码 | `gates-and-quality.md` 的 arch_quality_gate 一节；`extension-points.md`「Adding a New ADR」清单 |
| B3 | **rdd-verifier ↔ archive_gate 双轨边界**（ADR-0035）—— `gates-and-quality.md` 全文不提 `rdd-verifier` / `archive_gate_check` | `gates-and-quality.md` |
| B4 | rdd-quick ↔ P0 dispatch 关系（ADR-0048）—— `overview.md:74` 停在 ADR-0047 旧模型 | `overview.md` |
| B5 | rdd-builder 六相状态机 —— 已覆盖（`workflow-phases.md:291`），但 `overview.md:72` 只写「6-phase internal state machine」未列举 | `overview.md` |

---

## 3. docs/adr 的问题

### 3.1 形态契约符合性（对照 `ADR-0000-template.md` + ADR-0060）

| 判据 | 结果 | 说明 |
|---|---|---|
| 缺 `## Verification` | **59 / 60** | 仅 ADR-0060 有。另有 ADR-0018:122 / ADR-0019:263 用中文 `## 验证`（语义等价） |
| 缺独立「后果/代价」章 | **5** | ADR-0009 / 0032 / 0035 / 0049 / 0050 |
| 有 Consequences 但缺「负面/风险」子章 | **13** | 另 5 份用英文 `### Positive`/`### Negative`（语义满足、格式漂移） |
| 备选方案表缺「结论」列 | **28 / 39** | 只有 ADR-0060 用三列「备选\|结论\|理由」；其余为两列「备选\|理由」，结论维度靠正文措辞承载，不可机读 |
| 正文 > 300 行 | **13** | 0002/0004/0005/0006/0007/0008/0010/0011/0012/0027/0048/0049/0055 |
| 正文 > 250 行（模板目标） | **16** | 上述 + 0003(275)/0016(290)/0019(279) |
| 过程日志混入 | **12** | ADR-0055:441（`## v3 修订日志` + commit 号 + Metis 审查表）、ADR-0049:224（Test Strategy/Rollout）、ADR-0048:280（测试改动台账）、ADR-0050:157（实测「零 regression」）、ADR-0054:156（`## Implementation Status`）、ADR-0036:103（`## Post-hoc Fix Record`）、ADR-0043:140（`## Implementation`）、ADR-0025:89、ADR-0034:126、ADR-0051:13（Oracle BLOCKING）、ADR-0025、ADR-0049 |
| 缺 Context 形似章 | **4** | ADR-0053/0054（`## Background`）、ADR-0028/0034（`## 问题`）——**正则不认** |
| 缺 Decision | **1** | ADR-0035（只有 背景/Scenario/权衡/升级/follow-up/参考） |
| 缺 References | **6** | 0011/0012/0020/0023/0041/0046 |

**关键：门禁实现与契约脱节。** `_lib/arch_quality_gate.py:180-193` 的 `_check_adr_shape()` 只查 4 段 + 行数 + 3 类过程日志正则 + Status 长度：
- **不查 Verification** —— 而模板 `:10` 明写「缺前瞻 Verification ⇒ 文档不成立」；
- **不查备选表的「结论」列与 ≥3 行**；
- 过程日志正则（`BLOCKER|SHOULD_FIX|NITS?|第 N 轮 critic|队列#N|台账 Entry#N`）对本仓**实际形态**（`## v3 修订日志` / `## Implementation Status` / `Metis B4 审查` / `## Post-hoc Fix Record`）**零命中**。

⇒ **门禁对真实漂移近乎无效**。ADR-0060:79 的「后续待办」只记了「接入 CI」，未记这个盲区。

### 3.2 状态词表不一致

`docs/adr/README.md:213-222` 的词表只有 6 值（待定/已采纳/已拒绝/已弃用/已替代为 ADR-NNN/已采纳，状态待核实），实际使用了 7 类表外写法：
`待采纳`（ADR-0049/0050/0051）· `模板（v3.0 候选占位）`（0009）· `✅ 已采纳…`（0010/0017/0018/0019）· `已采纳 + AMENDED` / `+ DOUBLE-AMENDED`（0038/0042/0047）· `已采纳 + 已实施（… commit f5eb49c …）`（0055，**把 commit 号写进 Status 行**）· `已替代为 ADR-0002 + ADR-0003`（0001，词表只允许单个 ADR-NNN）· YAML frontmatter `status:`（仅 ADR-0001-x.md —— 第三种元数据载体，generator 正则不识别）。
另有 5 份用英文键 `**Status**`（ADR-0043/0044/0049/0050/0051），其余 55 份用 `**状态**`。

### 3.3 会持续扩散的失效引用（模板 + 索引）

| 位置 | 引用 | 实际 |
|---|---|---|
| `ADR-0000-template.md:63` | `docs/proposal-suggestions-format.md` | `docs/improvement-suggestions-format.md` |
| `ADR-0000-template.md:64` | `skills/propose.md` | `skills/propose/SKILL.md` |
| `ADR-0000-template.md:65` | `skills/deps.md` | `skills/deps/SKILL.md` |
| `docs/adr/README.md:201-202` | 同上前两条 | 同上 |
| `docs/adr/README.md:248` | 同后两条 | 同上 |

⇒ **每次新建 ADR 都会复制这 5 处失效路径**（模板是复制源），属于「主动生产污染」。

### 3.4 历史类失效引用（存量，按 ADR-0060「不追溯」处理，不建议回改正文）

ADR-0001:101-107 / 0003:204-262 / 0013:1,13 / 0016:21-26 / 0017:80 / 0030:202-203 / 0031:34 / 0039:60 / 0045:14 / 0046:36,54 等 —— 指向已删除的 `skills/guide-*.md`、`skills/ac-verifier/`、`_lib/arch/protocol.py`。
建议：在 ADR-0060 体系下加一句**导航式说明**（正文为历史快照，路径以 ADR-0044/0045/0057 为准），而不是逐个改写。

---

## 4. 与 opencode build agent 角色矩阵的对齐

### 4.1 现状：两套角色体系并存，且只有一侧有文档

| | opencode 侧（治理面） | rdd-workflow 侧 |
|---|---|---|
| 角色集 | `architect` / `planner` / `builder` / `verifier` / `general` / `no-role` | `rdd-arch` / `rdd-planner` / `rdd-builder` / `rdd-verifier` / `rdd-quick` |
| 载体 | `.rddf/state/role.json`（role-v2 schema，sessions 分区）+ `pair.json` | SKILL.md frontmatter `role:` 块（ADR-0028 + `openspec/specs/skill-role-model`） |
| 语义 | **单会话内的治理身份**（可切换，切换写 history） | **阶段工件的归属声明**（owns / not_owns） |
| 审查 | architect → oracle → critic；planner → metis；builder → verifier | arch_quality_gate（机械）+ ADR-0060 形态检查（opt-in） |

opencode 侧**已显式声明解耦**：`~/.config/opencode/docs/MULTI-AGENT-DESIGN.md` §2.6（v1.9 起）「角色矩阵是自足内核，rdd-workflow 是可选增强层」。

**问题**：这份解耦声明**只存在于 opencode 侧**。rdd-workflow 的 `docs/architecture` + `docs/adr` 里**零处**提到角色矩阵、`role.json`、`role_class`、HANDOFF 派发契约、`.rddf/reviews/` 落点。后果：只读 rdd-workflow 文档的人会把 `rdd-arch` 的 `role.title: "Architect (架构治理者)"` 误读成 opencode 的 `architect` 治理角色，进而对「谁能写 ADR / 谁能 commit / 谁审谁」产生错误预期。

### 4.2 逐项对照

| 维度 | opencode 角色矩阵 | rdd-workflow 文档现状 | 对齐判定 |
|---|---|---|---|
| 角色命名 | `architect`/`planner`/`builder`/`verifier` | `rdd-arch` frontmatter `role.title: "Architect (架构治理者)"` | ❌ **同名不同义**，最高误读风险 |
| architect 写集 | `arch_paths` 命中的架构文档 + 治理面 `~/.config/opencode/**` + `.rddf/config/arch-docs.json` + `.rddf/reviews/<adr>.md` | `rdd-arch` owns = `docs/adr/ADR-*.md` + `docs/architecture/*.md` + `.arch-handoff.json` | ⚠️ 前两项**恰好重合**（本仓 `.rddf/config/arch-docs.json` 不存在 ⇒ opencode 走 fallback 目录集 = docs/adr + docs/architecture）；后两项 opencode 侧**无对应声明** |
| 审查机制 | architect = oracle → critic（语义审查，双审） | arch_quality_gate（机械）+ ADR-0060 形态检查（opt-in） | ❌ **两条路径都写 ADR，但只有 opencode 侧有语义审查**；ADR-0060:34 已把这个「约束链断点」记下来了，但 `docs/architecture` 没落成一句说明 |
| ADR 行数预算 | build.md「正文 = 决策本身，目标 **≤ 250 行**」 | 模板 `ADR-0000-template.md:8`「正文目标 ≤ 250 行」；ADR-0060:45 + `_lib/arch_quality_gate.py:177` 机械默认 **300 行** | ❌ **三处不一致**，机械检查比散文契约宽 50 行 ⇒ 违反散文契约的文档能通过机械门 |
| 形态必备要素 | 「四要素」+「Verification 章」= 文档成立的硬条件 | 模板 `:10` 同款措辞；但 `_check_adr_shape()` **不检查 Verification** | ❌ **契约与实现脱节**（模板承诺 ≠ 机械保证） |
| verifier 双落点 | 产品落点 `.rddf/reviews/**` ＋ 记账落点 `.rddf/state/verifier/**`（build.md 明写「skill 写入的全部状态文件都在这里」） | `rdd-verifier` frontmatter owns = **只有** `.rddf/state/verifier/*`；`.rddf/reviews/` 目录里已躺着 15 份验收报告 | ❌ **产品落点无声明归属**（skill 侧缺 `.rddf/reviews/**`） |
| `.rddf/` 布局真源 | 治理状态写在 `.rddf/state/role.json` / `pair.json` | `_lib/core/rddf_layout.py:59` 把 `state/` 声明为 `read_by=(rdd,), write_by=(rdd,)`；`rddf-layout.md:67-84` 文件级表只列 verifier 命名空间 + 3 个 handoff | ❌ **事实不符**：`role.json`/`pair.json` 由 agent 写；且治理状态在架构文档里不可见 |
| 派发契约 | `role_class`（architect/builder/verifier 三类）+ HANDOFF 首行 + 5 项凭据 + `rddf feedback add` single writer | ADR-0034:132-134 **已经引用了「被派发的 verifier 后端」**（写集上限 = `.rddf/state/verifier`）；但 `docs/architecture` 零提及派发模型 | ⚠️ ADR 侧**半覆盖**（只覆盖 verifier），architecture 侧空白 |
| 反馈通道 kind | `needs-revision` / `ac-fail` / `blocked` / `noted` | ADR-0037 定义 `rddf feedback add` single writer（`_lib/cli/feedback_cmd.py` 存在） | ✅ **同源，良好**（唯一一处真正对齐的地方） |
| ADR-0001-x.md 的双份跳过逻辑 | — | 6 处消费方硬编码跳过（见 §1.3） | ❌ 治理侧（opencode 的 ADR 索引/评审）也会撞上这个伪 ADR |

### 4.3 一句话结论

> **opencode 侧把「角色矩阵 ↔ rdd-workflow」的边界写清楚了（§2.6 增强层 + ADR-0060:34 约束链断点），但 rdd-workflow 侧没有任何一份文档镜像这份边界。**
> 于是同一件事有两套真源、两套命名、且**分歧点恰好落在写集与审查**这两个最容易出事的维度上。

---

## 5. 修订建议（按优先级）

### P0 — 会持续制造新污染 / 会误导读者

| # | 动作 | 落点 | 验证方式（已有守卫可扩展） |
|---|---|---|---|
| P0-1 | 修 ADR 模板 + ADR README 的 5 处失效路径（`proposal-suggestions-format`→`improvement-suggestions-format`；`skills/propose.md`→`skills/propose/SKILL.md`；`skills/deps.md`→`skills/deps/SKILL.md`） | `docs/adr/ADR-0000-template.md:63-65`、`docs/adr/README.md:201-202,248` | 加一条 bats：模板与 README 不得含 `skills/propose.md` / `skills/deps.md` / `docs/proposal-suggestions-format.md` |
| P0-2 | 清 `docs/adr/ADR-0001-x.md`：夹具迁 `tests/fixtures/adr/`（或测试内 tmpdir），删文件，同步删 6 处硬编码 skip | `_lib/adr_index_generator.py:28-29`、4 个测试文件 | `bats tests/integration/test_adr_directory.bats tests/integration/test_adr_index.bats` |
| P0-3 | 统一 ADR 行数预算为 **250**（模板 250 / build.md 250 已一致，只机械门是 300） | `_lib/arch_quality_gate.py:177` `_DEFAULT_ADR_LINE_LIMIT` | 单测断言默认 250；或保留 300 但在 ADR-0060 记录理由 |
| P0-4 | 扩 `_check_adr_shape()`：加 Verification 章节检查 + 备选表「结论」列/≥3 行检查 + 过程日志正则（补 `## v3 修订日志`/`## Implementation Status`/`## Post-hoc Fix Record`/`Metis .* 审查`/`## Implementation`） | `_lib/arch_quality_gate.py:170-230` | `pytest tests/unit/test_arch_quality_gate.py` |
| P0-5 | 修正 `overview.md:70`（roadmap/gap analysis 归属）+ 重写 `overview.md:81-88`（Sub-skills 表 Called by 列） | `docs/architecture/overview.md` | 扩 `test_v4_doc_drift_contracts.bats` Test 14 的正则：**禁一切裸 `guide-*`/`ac-verifier` 提及**（排除显式 DEPRECATED 标注），而不只禁 3 种「live invocation」句式 |
| P0-6 | 修 5 处断链 + `docs/architecture/README.md` Doc Map 补 3 行 + 刷新行改 `as of v4.0.0` | 见 §1.1 / §1.2 | 扩一个 markdown link checker 进 `tests/unit/`（当前仓库无此守卫） |

### P1 — 与 opencode 角色矩阵对齐（本次用户明确关注项）

| # | 动作 | 落点 |
|---|---|---|
| P1-1 | **新增一篇 `docs/architecture/agent-role-alignment.md`**：写清两套角色体系的分层关系（治理身份 vs 阶段工件归属）、命名消歧（`architect` ≠ `rdd-arch`）、工件归属对照表（opencode 角色 ↔ rdd-* skill ↔ owns 路径）、派发模型（`role_class` + HANDOFF + `rddf feedback add`）、verifier 双落点。并在 `docs/architecture/README.md` Doc Map 登记 | 新文件 + README |
| P1-2 | **`rdd-verifier` frontmatter owns 补 `.rddf/reviews/**`**（产品落点），与 build.md「产品落点 = `.rddf/reviews/`」对齐；同步 ADR-0034 §8 storage ownership 表加一行 | `skills/rdd-verifier/SKILL.md` frontmatter、`docs/adr/ADR-0034-...md:96-105` |
| P1-3 | `rdd-arch` frontmatter owns 补 `.rddf/config/arch-docs.json` 与 `.rddf/reviews/<adr>.md`（opencode architect 侧有此权限，skill 侧无声明 ⇒ 两处无主） | `skills/rdd-arch/SKILL.md` frontmatter |
| P1-4 | `.rddf/` 布局清单修正 `state/` 的 `write_by`（rdd + agent）并在 `rddf-layout.md` 文件级表补 `role.json` / `pair.json` / `.rddf/reviews/*.md` 三行 | `_lib/core/rddf_layout.py:59`、`docs/architecture/rddf-layout.md:63-84` |
| P1-5 | 在 `docs/architecture/gates-and-quality.md` 补 ADR-0035 双轨边界 + ADR-0060 `ARCH_SHAPE_CHECK` 两节（当前该文件零提及 verifier 与形态检查） | `docs/architecture/gates-and-quality.md` |
| P1-6 | `docs/architecture/state-and-events.md` 补「治理状态层」：`role.json`（role-v2, sessions 分区）/ `pair.json` 与 rdd 状态的关系 —— 否则「state 有三层」的说法对 opencode 侧读者不成立 | `docs/architecture/state-and-events.md` |
| P1-7 | 同步 `openspec/specs/skill-role-model/spec.md`（能力 spec = ADR 的等价物）：全文仍写「4 个 `guide-*` SKILL.md」，且 Scenario「guide-arch owns ADR + roadmap」与 v4 矛盾 | `openspec/specs/skill-role-model/spec.md` |

### P2 — 结构性治理（防止再次漂移）

| # | 动作 |
|---|---|
| P2-1 | **把 ADR README 的散文段也纳入生成范围**（顶部实施状态表 / 主题分类 / 架构演进 / 上次同步），否则 `adr_index_generator` 只能守住表格、散文继续漂 |
| P2-2 | **文档版本/计数派生化**：删掉手写版本号与 ADR/skill 计数，改为「见 `package.json` / `ls docs/adr` / `ls skills`」，或加一个 `rddf docs --check` 巡检 |
| P2-3 | **扩展现有守卫**：`test_v4_doc_drift_contracts.bats` 的 guide-* 正则从「3 种 live invocation 句式」扩到「裸提及」；新增 markdown link checker；新增 `docs/architecture` 与 `docs/adr` 的交叉引用一致性检查 |
| P2-4 | 存量 ADR 形态债（59 缺 Verification / 13 超 300 行 / 21 缺备选章 / 12 过程日志）**按 ADR-0060「不追溯」单独立项**（`.rddf/improvements/`），不要在本次回填 —— 否则单次 PR 变成 50+ 文件重写 |
| P2-5 | `docs/adr/README.md` 状态词表扩容（补 `待采纳`/`已采纳 + AMENDED`/多 ADR 替代）或统一收敛到 6 值；`ADR-0055` 的 Status 行去掉 commit 号（同时触发 `ARCH_ADR_STATUS_MAX`） |

---

## 6. 本次审查的边界

- **未修改** `docs/architecture/**` 与 `docs/adr/**` 任一文件（verifier 角色边界：不改实现/被审对象）。
- 未改动 `skills/**`、`_lib/**`、`openspec/**`（P0-1~P0-6 / P1-2~P1-7 的落点需切 builder 或 architect 执行）。
- 库存 ADR-0001-x.md 的 `git log` 未取到（子 agent 的 shell 被权限拒绝）；其「测试夹具」结论来自 `docs/superpowers/plans/2026-08-07-guide-design-phase1-diagnostic.md` 的 7 处 `touch` 与 6 处 skip 分支，证据充分但未含提交历史。
- `guide-*`/`ac-verifier` 共 318 处提及未逐条判定「历史快照」还是「现行描述」；分布为 docs/architecture 9/18 篇、docs/adr 37/61 篇。

---

## 7. 处置记录（2026-11-17，本报告落地后）

| 项 | 处置 | 备注 |
|---|---|---|
| P0-1 | ✅ 已修 | `ADR-0000-template.md` + `docs/adr/README.md` 的 5 处失效路径 |
| P0-2 | ✅ 已修 | 删 `docs/adr/ADR-0001-x.md`；6 处硬编码 skip 同步移除；历史 plan 加告警注记 |
| P0-3 | ✅ 已修 | `_DEFAULT_ADR_LINE_LIMIT` 300→250（同源断言测试已加） |
| P0-4 | ✅ 已修 | `adr_shape_findings()` 一级 API + Verification/备选表/标题级过程日志信号 + CLI 单一真源 + `--strict` 语义修正 + `no_adr_files_scanned` |
| P0-5 | ✅ 已修 | `overview.md` 的 guide-\* 残留表、roadmap/gap-analysis 归属、CLI 表、skill 计数 |
| P0-6 | ✅ 已修 | 5 处断链 + Doc Map 补 3 行 + 版本刷新行 + `historical-evolution.md` 补 v3/v4 |
| P1-1 | ✅ 已修 | 新增 `docs/architecture/agent-role-alignment.md`（144 行）+ Doc Map 登记；oracle→critic 双审通过（critic 第 1 轮 1 BLOCKER 已闭） |
| **P1-2 / P1-3** | ⚠️ **重定向（原建议不采纳）** | 原建议「给 `rdd-verifier` / `rdd-arch` 的 `owns` 加 `.rddf/reviews/**` 与 `.rddf/config/arch-docs.json`」**违反** `openspec/specs/skill-role-model/spec.md` 的 `skill-role-owns-generated-artifacts-only`（rdd-workflow 代码全仓零读写这些路径），并会破坏 `_lib/verifier/state_paths.py` 的逐字节比对不变量。改为按 `design.md` 先例：**SKILL.md 正文加作者声明**（`rdd-verifier` / `rdd-arch` 各一处），概念分层由 P1-1 的文档承载。Metis 与 Oracle 独立得出同一结论。 |
| P1-4 | ✅ 已修 | `state` 条目 `write_by` → `("rdd","agent")`；`rddf-layout.md` 增「治理状态（opencode 角色层）」子表 + 顶层表同步 |
| P1-5 | ⚠️ 部分 | `overview.md` 已注明 `ARCH_SHAPE_CHECK`；`gates-and-quality.md` 的整节重写（ADR-0035 双轨 + ADR-0060 形态门）**未做**，记为待办 |
| P1-6 | ⚠️ 部分 | `state-and-events.md` 的「治理状态层」未加；`.rddf/` 治理位置的说明由 `rddf-layout.md` + 新文档承载 |
| P1-7 | ⏭ 未做 | `openspec/specs/skill-role-model/spec.md` 仍用 v3 `guide-*` 命名；新文档「不复述清单」已加一条已知陈旧点提示，spec 本体待 planner 立项 |
| P2-1 ~ P2-5 | ⏭ 未做 | 均记入待办（散文段纳入生成器 / 计数派生化 / 守卫扩展 / 存量债立项 / 状态词表扩容） |

**新增的既有缺陷（本轮仅报告，见 `.rddf/reviews/adr-0060-amendment-2026-11-17.md` §五）**：
本仓有两个 ADR 索引生成器且格式分歧（`_lib/adr_index_generator.py` 4 列含日期 vs `_lib/sync_adr_index.py` 3 列且会删 `ADR_INDEX_START/END` 标记）；`tests/unit/test_sync_adr_index.py` 实际验的是全局安装副本而非仓内实现。

**本轮实跑中额外发现并已修复的既有缺陷**（详见 `.rddf/reviews/adr-0060-amendment-2026-11-17.md` §六）：
`tests/integration/test_known_failures_baseline.bats` 直接写仓库真实 `tests/KNOWN_FAILURES.txt`，而 `collect_bats_failures.sh` 的 30s 超时会杀掉进程、跳过 `teardown` ⇒ **回归门每次运行都会摧毁自己的基线**（87 行被截成 1 行），使全部既知失败被误报为「新增」。已通过 `KNOWN_FAILURES_BASELINE` env 覆盖 + 测试改用 tmp 基线 + `teardown` 守卫修复。

**最终验证**：`./test.sh --full --regression` ⇒ ✅ ALL PASSED（已知失败 11 / 新增失败 0 / 已修复 0，基线仍 87 行）；`pytest tests/unit/` 3361 passed / 3 skipped；`pytest tests/integration/` 201 passed；`docs/**` markdown 断链 0 处。
