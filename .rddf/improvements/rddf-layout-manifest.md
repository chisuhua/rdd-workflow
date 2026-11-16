---
优先级: P1
priority: P1
来源: 2026-11-16 opencode-config 侧提问「是否该有一份完整的 .rddf/ 目录与文件用法知识，供第三方项目与 e2e 测试床遵循」—
  核查发现产品仓无单点真源：路径常量只有 5 个模块常量 + 2 条 DEFAULTS 条目，散文仅覆盖 handoff 与两个插件目录，doctor 24 个
  category 里没有布局类；ADR-0026 已给出「runtime-only / committed artifacts」二分但未被工具执行
阶段: phase-4
分类: governance
类型: improvement
主题: rddf 布局单一真源 —— .rddf/ 机读清单 + layout 子命令 + doctor layout category + 散文由清单派生
状态: approved
approved_at: 2026-11-16
approved_by: rdd-planner
review_notes: "s → y: 5 段审核通过 + 2 轮审稿处置闭合（metis 13 条 finding 全部采纳；build 侧证据核对 4 BLOCKER + 9 SHOULD_FIX 全部处置）—— 逐条处置见正文「审稿记录」段"
roadmap_ref:
  project_id: 多方对称与回归
  phase: phase-4
---

**优先级**: P1 | **状态**: approved（2026-11-16，rdd-planner）
**阶段**: phase-4 | **分类**: governance | **类型**: improvement

**主题**: rddf 布局单一真源 —— .rddf/ 机读清单 + layout 子命令 + doctor layout category + 散文由清单派生

## 审稿记录

两轮审稿，全部处置完毕。

**第 1 轮 — metis**（报告：`.rddf/reviews/rddf-layout-manifest-planner-review.md`，13 条 finding 全部采纳）：

| # | finding | 处置 | 落点 |
|---|---|---|---|
| 1 | `owner ∈ {product, third-party}` 与事实不符 | 改为可观测字段 `read_by` / `write_by`，逐条给 `file:line` 依据 | 范围表 + Capabilities MUST |
| 2 | `created_by=rddf` 实为手工 —— 不可观测 | 字段删除 | 范围表 |
| 3 | 应复用 ADR-0026 两分类 | `class` 直接取 ADR-0026，`gitignored` 由它派生 | 范围表 + Capabilities MUST |
| 4 | 已存在的顶层噪声让 AC 自相矛盾 | 加 `transient` + `.roadmap-migrate-backup-*` glob 条目；判据②放行 transient | 范围表 + 判据② + Acceptance |
| 5 | 反向 grep 断言失明 | 删除，改为断言 A（`defaults` + 5 个模块常量被覆盖）+ 断言 B（`class` 与 ignore 实况一致）；失明边界写进 Out of Scope 与风险① | Out of Scope + What Changes + 风险① |
| 6 | `schema_version` 演进策略缺失 | 成文（增字段/增 entry 不升版、改语义或删 entry 升版、消费方忽略未知字段、按 `path` 集合比较） | Acceptance + 文档要求 |
| 7 | `required` 单布尔对 `wt/` 误报 | 改 `required_when ∈ {always, worktree, never}` | 范围表 + Acceptance |
| 8 | 缺最小第三方 fixture AC | AC 改为「集合恰好相等」（不是「exit 0」） | Acceptance |
| 9 | 文档层过度设计却漏「文件级」 | 文档降级为「表格 + 三步」+ 补「文件级」 | In Scope + Acceptance |
| 10 | SKILL.md 写死 category 数字本身是漂移源 | 改为不写数字 | In Scope + Acceptance |
| 11 | `rddf layout` 子命令零消费者（YAGNI） | 当时砍掉 —— **本轮推翻**，见下表 B-2 | Out of Scope → 已改写 |
| 12 | `RDDF_STATE_DIR` 重定向使「`.rddf/state` 唯一」不成立 | 声明「本清单描述默认布局」 | Acceptance + Out of Scope |
| 13 | 与既有 category 职责边界 | 实测 `gitignore_check.py` 不核 `.rddf/` ⇒ 无重叠；与 `check_project_setup.sh` 的重复关系登记为风险③ | 风险③ |

**第 2 轮 — build 侧证据核对**（报告：`.rddf/reviews/rddf-layout-manifest-builder-review.md`，4 BLOCKER + 9 SHOULD_FIX 全部处置）：

| # | finding | 处置 | 落点 |
|---|---|---|---|
| B-1 | 「输出确定性」AC 与共享 renderer 的 `timestamp` 结构性冲突 | 清单出口独立为 `rddf layout --json`（自带 `schema_version`/`tool_version`，无时间戳）；**不改** `doctor_render.py`，共享 JSON 契约零变更 | In Scope + Out of Scope + Acceptance |
| B-2 | 机读清单没有交付通道 | 恢复 `rddf layout` 子命令作为清单出口（推翻 metis 第 1 轮的 YAGNI 裁决 —— 消费方就是本项立意本身） | In Scope + Why + Impact |
| B-3 | `git check-ignore` 直查目录在本仓假红 | 目录条目改用探针 `<path>/.probe`；规则写死 + 补 AC | In Scope（匹配与探测规则）+ Acceptance |
| B-4 | 「文件级」数据源已过期 | 改以代码为源；本次一并修 `state-and-events.md` 的 v3 遗留 handoff 表 | In Scope + Acceptance |
| S-1 | severity 词汇错位 + 退出码描述失实 | 加 `severity` 列（WARNING/INFO）；判据①=WARNING、②=INFO、③=WARNING；兼容性段改写为 `exit_code_for` 实现原话 | 范围表 + 判据 + Impact |
| S-2 | fresh 第三方项目必然报错 | `.rddf/` 不存在 ⇒ 本 category 0 finding；`required_when` 三态语义写清 | In Scope + Acceptance |
| S-3 | glob 匹配语义未定义 | 精确 → fnmatch glob → 未登记；`kind` 不参与匹配 | In Scope（匹配规则） |
| S-4 | 与 `check_project_setup.sh` 事实重复且不可复用 | 登记为风险③，写明两个出口的定位 | 风险③ |
| S-5 | Impact 漏 3 个必然要改的文件 | 补 `SKILL.md`（usage 枚举 + category 表）、`docs/architecture/README.md` | Impact |
| S-6 | 「实测存在」清单里 3 项不存在 | 拆分「实测存在」与「仅文档提及/外部约定」；`orch_plans` 全仓零引用 ⇒ 移除 | What Changes 1 |
| S-7 | `improvement-suggestions.md` 摘要与正文口径不一致 | 该行随批准移入 `improvement-approved.md`（摘要重写，纠正「路径常量仅 2 个」） | 索引文件 |
| S-8 | AC 写死基线 SHA | 改为「本仓当前 checkout」 | Acceptance |
| S-9 | 判据②把第三方自建目录变成必须找上游登记 | 判据②降为 INFO，且文档写明「用户自建目录不需上游登记」 | Capabilities SHOULD |
| N-1~N-4 | 行号偏差 / ADR 改动性质 / `path` 相对基准 / extension-points 只加链接 | 全部修正 | 全文 |

## 架构依据

`.rddf/` 是 rdd 的状态与工件面，它的「有哪些条目、谁读谁写、什么时候必需、是否入库」**没有单点真源**：

| 现状 | 证据 |
|---|---|
| 分类有 ADR，但没有机器可执行形态 | `docs/adr/ADR-0026-internal-metadata-namespace-convention.md:26-44` 已定义 `runtime-only`（`state/` `wt/` `detectors/` `actions/`）与 `committed artifacts`（`plans/` `improvements/`），并规定 gitignore 规则 —— 但没有任何代码/校验引用这张表 |
| 路径常量只有零星几条 | `_lib/core/defaults.py:24-32` 有 `state.path` / `event_log.path`；`:67-71` 另有 `STATE_VECTOR_PATH` / `EVENT_LOG_PATH` / `MEMORY_PATH` / `DETECTOR_PLUGIN_DIR` / `ACTION_PLUGIN_DIR`（注释自承是 DEFAULTS 的 mirror）；其余路径硬编码在模块里，两种写法并存：`Path(root) / ".rddf" / "issues"`（`_lib/issue_reporter.py:161`）与 `os.path.join(root, ".rddf", "state")`（`_lib/cli/__main__.py:216`） |
| 散文覆盖不全 | `docs/architecture/state-and-events.md:47-55` 只覆盖 3 个 handoff 文件；`docs/architecture/extension-points.md:29-30` 只写 `detectors/` `actions/`，并注明真源是 `defaults.py` |
| 没有布局校验 | `skills/rdd-doctor/scripts/doctor_main.py:27-54` 的 24 个 category 无布局类；`gitignore_check.py` 只核 `openspec/` 与 `project.yaml.git.openspec_tracked` 的一致性，**不核 `.rddf/`** |
| 描述已漂 | `skills/rdd-doctor/SKILL.md:4` 的 description 写「13 file categories」，实际 24 |

后果分两个方向：

1. **第三方项目不知道「必须有什么」**：`state/` `improvements/` `plans/` `roadmap/` `project.yaml` 里哪些必需、哪些按模式才需要（`wt/` 只在 worktree 模式存在）、哪些可省，只能读代码反推。`rddf init` 只装 `.opencode/skills/rdd-workflow`（`_lib/cli/init_cmd.py:27`），**不建** `.rddf/`，所以第三方首次使用时手里没有任何布局依据。
2. **消费方扩展点没有边界声明**：`config/`（消费方私有目录，rdd 零引用；与 rdd 自己的 `.rddf/config.json` 同名不同物）、`reviews/`（`_lib/` 与 `skills/` **零引用**，纯 agent 产物）这类条目，rdd 不读不写 —— 但没有一处写明，外部项目无从判断自己加的文件会不会被覆盖或误读。

这类知识不能靠散文维护：布局演进时散文不会红；也不能靠「扫代码里的路径字面量」兜住 —— 实际写入有 `Path(root) / ".rddf" / X` 与 `os.path.join(...)` 两种拼接形态，字面量扫描对真正的写入方**失明**（见「范围」的 Out of Scope）。

## 范围

### In Scope

- 新增 `_lib/core/rddf_layout.py`：单一清单 `RDFF_LAYOUT`。每条字段 + 取值域：

  | 字段 | 取值 | 说明 |
  |---|---|---|
  | `path` | 字符串，**允许 glob** | **相对 `.rddf/` 的顶层条目名**（不写 `.rddf/` 前缀），如 `state` / `roadmap.md` / `.roadmap-migrate-backup-*` |
  | `kind` | `dir` \| `file` | 区分目录与顶层文件；**不参与路径匹配**，只用于存在性检查与 ignore 探测形式 |
  | `read_by` / `write_by` | 列表，元素 ∈ {`rdd`, `agent`, `user`, `git`, `external-tool`} | **可观测事实**，逐条给依据（例：`wt` 由 git 建、`issues` 由 rdd 读写、`reviews` 只由 agent 写、`config` 由外部工具建且 rdd 不读） |
  | `required_when` | `always` \| `worktree` \| `never` | `always` = 项目启用 rdd 后应当存在（缺失 = 布局漂移）；`worktree` = 仅 worktree 模式要求存在；`never` = **不要求存在**（按需创建或由外部创建） |
  | `transient` | bool | 临时候选项（如迁移 backup），判据②对它放行 |
  | `class` | `runtime-only` \| `committed` | **直接取自 ADR-0026**，`gitignored` 由它派生，不另立第三套分类 |
  | `severity` | `WARNING` \| `INFO` | 该条目相关的**缺失类**判据定档（doctor 只有 CRITICAL/WARNING/INFO 三档，无 error 档） |

- 新增 **清单出口** `rddf layout --json`（只读子命令，`_lib/cli/layout_cmd.py`）：输出 `RDFF_LAYOUT` 全量清单，payload 含 `schema_version` / `tool_version` / `entries`（按 `path` 排序），**无时间戳字段** ⇒ 同仓连续两次输出字节一致。**这是机读清单的唯一对外出口**；`rddf doctor --category layout` 只出 findings，不承载清单内容。

- 新增 doctor category `layout`（注册进 `skills/rdd-doctor/scripts/doctor_main.py` 的 `_CHECKERS`），三支判据：
  ① `required_when=always` 的条目缺失 ⇒ **WARNING**；
  ② 出现**未登记且非 `transient`** 的 `.rddf/` 顶层条目 ⇒ **INFO**；
  ③ `class` 与 `.gitignore` 实况不符（`runtime-only` 未忽略 / `committed` 被忽略）⇒ **WARNING**。
  校验器只 `scandir` 一层，**禁止递归**（`.rddf/wt/<name>/` 是完整 checkout）。
  **本 category 永不产生 CRITICAL** ⇒ `rddf doctor` 不会因布局问题 exit 2。
  **`.rddf/` 目录不存在 ⇒ 本 category 返回 0 findings**（项目尚未启用 rdd，不该被诊断）。

- 匹配与探测规则（**写死，实现不得自由发挥**）：
  - **未登记判定**：① `path` 字面精确匹配 → ② `fnmatch` glob 匹配（`*` 不跨 `/`，因只扫一层）→ ③ 都落空 ⇒ 判为未登记。精确优先于 glob ⇒ `roadmap.md` 不会被 `roadmap` 吃掉。
  - **ignore 探测**：`kind=file` ⇒ 直接查 `<path>`；`kind=dir` ⇒ 查**探针路径** `<path>/.probe`。**必须用探针**：目录内含 tracked 文件时 git 不把该目录计入 exclude 列表，直接查目录会得到 NOT-IGNORED —— 本仓 `.rddf/state/` 含 tracked 文件 `.rddf/state/index.md`，实测 `git check-ignore .rddf/state/` 返回未忽略（`git check-ignore --no-index .rddf/state/` 与 `git check-ignore .rddf/state/.probe` 才命中 `.gitignore:10`）。

- 新增 `docs/architecture/rddf-layout.md`：**表格 + 「新增一个顶层条目的三步」**（引用 ADR-0026 §41-44 的类别决策与 gitignore 步骤），并含一节「文件级」—— **以代码为源**，不抄散文：`_lib/verifier/state_paths.py:34-41` 的 6 条 verifier 文件名 + `_lib/builder_deps.py:42` / `_lib/builder_feedback_router.py:31` / `_lib/adr_catalog.py:127` 的 handoff 文件。不要求逐字生成、不要求比对测试。

- 散文补链与修正：
  - `docs/architecture/state-and-events.md`：**补链接 + 修过期内容** —— 其 Layer 3 表格（`:53-55`）与 mermaid 图（`:14-16`）写的是 v1~v3 的 skill 名（`guide-design`/`guide-plan`/`guide-ship`）与已废弃的 `.design-handoff.json`/`.plan-handoff.json`（v4 实际为 `.arch-handoff.json` / `.planner-handoff.json`，前者只余 legacy 探测用途，见 `_lib/cli/guide_cmd.py:172-173,199-200`）⇒ 本次一并修成 v4 命名，再加指向新页的链接。
  - `docs/architecture/extension-points.md`：只加链接（`:29-30` 已列 `detectors/`/`actions/`，不重复展开）。
  - `docs/adr/ADR-0026-*.md`：表格加一句「机器可执行形态见 `rddf layout --json` 与 `rddf doctor --category layout`」—— **纯描述性补充，不改变该 ADR 的任何决策**。
  - `docs/architecture/README.md`：Doc Map 表新增一行（该文件明写 Update Convention：新增 `architecture/*.md` 必须在同一 change 内更新）。

- 把 `skills/rdd-doctor/SKILL.md` 的 description 里的固定数字去掉（改「多维 file-category 诊断」），**不再写死数目**；同时更新 `:26` 的 usage 行里硬编码的 category 花括号枚举（实测已漏 `baseline-freshness`，本就在漂移）与 `:74` 起的 category 说明表。

### Out of Scope

- **不把现有路径引用改成读常量**（那是一次大重构；本项只建清单与校验）。
- **不做「扫代码路径字面量 ⊆ 清单」的反向断言** —— 实测两种拼接形态在字面量 grep 下都不出现（`Path(root) / ".rddf" / "issues"`、`os.path.join(root, ".rddf", "state")`），它会「看起来验了其实失明」；且文档里存在历史假想名（`docs/schemas/README.md:41` 的 `.rddf/triggers/*.yaml`，真实是 `.rddf/state/triggers.json`），反向扫会把文档错误固化成布局事实。改用两条更便宜的断言（见 Acceptance）。
- **不定义第三方扩展的内容格式** —— 只声明 `read_by`/`write_by`；`external-tool` 条目（如 `config/`）rdd 不读、不写、不校验内容。
- **不改 e2e 仓** —— 它的断言改动机在 `rdd-workflow-e2e` 自己的 change 里。
- **不改 `skills/rdd-doctor/scripts/doctor_render.py`** —— 共享 JSON renderer 的 `timestamp` 字段与 24 个 category 的 JSON 契约保持不变；清单的确定性输出由独立的 `rddf layout --json` 承担。
- **不承诺 `_lib.core.rddf_layout` 的 import 路径是稳定 API** —— 第三方通过 `rddf layout --json` 消费，不直接 import 产品内部模块。
- **不改 `rddf init` 建 `.rddf/` 骨架** —— 本清单描述的是「已启用 rdd 的项目」；`.rddf/` 不存在时 layout/doctor 均静默。

## Why

三类读者在同一个 `.rddf/` 上各有缺口，且都不是「文档写得不够长」能补的：
1. **第三方项目**：首次使用 rdd 时手里没有任何布局依据（`rddf init` 不建 `.rddf/`），「哪些必须建、哪些按模式才需要」只能读代码反推。
2. **消费方扩展点**：`.rddf/config/`、`reviews/` 这类条目 rdd 不读不写，但没有一处写明 ⇒ 外部项目无从判断自己加的文件会不会被覆盖或误读。
3. **本仓自身**：布局演进时散文不会红、硬编码路径也不会红 ⇒ 漂移只能靠人发现。

因此本项的形态是「**把 ADR-0026 已有的分类落成机器可执行的清单**」，而不是另立一套文档规范：分类维度复用 ADR-0026 的 `runtime-only` / `committed`；字段取**可观测事实**（`read_by` / `write_by` 指到具体 `file:line`，而非「owner」这类判断）；未登记条目靠 doctor 报出来，而不是靠文档提醒。

「目录里有什么」是**可枚举事实**，它该有机器可读的真源。而 ADR-0026 已经把这个事实的**分类维度**定好了，缺的只是让它可执行 —— 所以本项是「把已有 ADR 落地为工具」，不是发明新分类。

`read_by` / `write_by` 必须是可观测字段，而不是「owner」这种聚合判断：`wt/` 由 git 建、`issues/` 由 rdd 读写、`reviews/` 只由 agent 写、`config/` 由外部工具建且 rdd 不读 —— 这四条都能在代码里指到具体行；写成「判断」就等于放弃了校验。同理 `required_when` 不能是单布尔：`wt/` 在轻量模式下永不创建，无条件 required 会对这类项目误报。

**为什么清单要独立出口（`rddf layout --json`）而不是复用 doctor 的 `--json`**：doctor 的 JSON 通道只承载 findings，装不下「清单本身」；且共享 renderer 无条件写 `timestamp`，无法满足「同仓连续两次输出字节一致」。此前「砍掉 `rddf layout` 子命令（YAGNI，当前无消费者）」的裁决被本轮推翻 —— 消费方就是本项的立意本身（第三方项目与 e2e 测试床需要机器可读的布局知识）。

出口分两个、互不重叠：`rddf layout --json` 是**清单视图**（给消费方与第三方 CI 读），doctor `layout` 是**诊断视图**（给项目自检，只读不写盘）；两者互不污染，也不需要改任何共享渲染器。

## What Changes

1. **`_lib/core/rddf_layout.py`**（新）：`RDFF_LAYOUT` 清单 + `as_dicts()`（按 `path` 排序）。首版条目：

   | `path` | `kind` | `read_by` | `write_by` | `required_when` | `transient` | `class` | 依据（file:line） |
   |---|---|---|---|---|---|---|---|
   | `state` | dir | rdd | rdd | always | false | runtime-only | `_lib/core/defaults.py:24-32`, `:67-71` |
   | `wt` | dir | rdd | git | worktree | false | runtime-only | `_lib/worktree.sh:13` |
   | `detectors` | dir | rdd | user | never | false | runtime-only | `_lib/core/defaults.py:70`; `docs/architecture/extension-points.md:29` |
   | `actions` | dir | rdd | user | never | false | runtime-only | `_lib/core/defaults.py:71`; `docs/architecture/extension-points.md:30` |
   | `issues` | dir | rdd | rdd | never | false | runtime-only | `_lib/issue_reporter.py:161` |
   | `improvements` | dir | rdd | rdd, agent | always | false | committed | `_lib/cli/feedback_cmd.py:70`; `_lib/planner_attach.py` |
   | `plans` | dir | rdd | rdd, agent | always | false | committed | `_lib/loop/actions.py:132`; `_lib/iteration/post_archive.py:201` |
   | `roadmap` | dir | rdd | agent | always | false | committed | `_lib/cli/roadmap_cmd.py:51` |
   | `roadmap.md` | file | rdd | agent | always | false | committed | `_lib/arch_quality_gate.py:41` |
   | `project.yaml` | file | rdd | user | always | false | committed | `_lib/adr_catalog.py:109`; `_lib/cli/rdd_verify_cmd.py:49` |
   | `reviews` | dir | agent | agent | never | false | committed | `_lib/` 与 `skills/` 零引用（实测） |
   | `config` | dir | external-tool | external-tool | never | false | committed | 全仓零引用（消费方私有目录） |
   | `skill-profiles` | dir | rdd | user | never | false | committed | `skills/rdd-session-bootstrap/rdd-session-bootstrap.sh:14` |
   | `.roadmap-migrate-backup-*` | dir | rdd | rdd | never | true | runtime-only | `.gitignore:40`（迁移 backup 副产物） |

   > 本仓 `.rddf/` 实测存在的顶层条目 = 上表全部（除 `detectors`/`actions`/`config`/`skill-profiles` 四个在本仓不存在，属「仅文档提及 / 外部约定」类，仍登记以免第三方扩展被判未登记）。`orch_plans` **不进清单** —— 全仓零引用。

2. **`rddf layout --json`**（新）：`_lib/cli/layout_cmd.py` + `_lib/cli/__init__.py` 注册（`_ROUTES` + `_SUBCOMMAND_DESCRIPTION`）+ `_lib/cli/__main__.py` 的 `_NO_STATE_CHECK` 增 `layout`（`.rddf/` 不存在时静默返回空清单）。输出 `{"schema_version": 1, "tool_version": "<version>", "entries": [...]}`，`entries` 按 `path` 排序，无时间戳字段。
3. **doctor `layout` category**（新）：`skills/rdd-doctor/scripts/checks/layout_check.py` + 注册进 `doctor_main.py` 的 `_CHECKERS`；三支判据与定档见「范围」。
4. **`docs/architecture/rddf-layout.md`**（新）+ 散文补链与修正（state-and-events 修表 / extension-points 加链 / ADR-0026 加一句 / architecture README 索引）。
5. **`skills/rdd-doctor/SKILL.md`** description 去固定数字 + usage 行 category 枚举同步 + category 说明表加行。
6. **测试**：
   - `tests/unit/test_rddf_layout.py`：字段完整 + 取值域闭合 + `path` 唯一 + `class` ⊆ {runtime-only, committed} + `severity` ∈ {WARNING, INFO}；
   - **断言 A**：`defaults.DEFAULTS` 里的路径类条目（`state.path` / `event_log.path`）与模块常量（`STATE_VECTOR_PATH` / `EVENT_LOG_PATH` / `MEMORY_PATH` / `DETECTOR_PLUGIN_DIR` / `ACTION_PLUGIN_DIR`）**均能被清单覆盖** —— 匹配规则：**精确匹配优先，其次最长前缀**（`.rddf/state/state-vector.json` 由 entry `state` 覆盖；`.rddf/detectors` 由 entry `detectors` 精确覆盖）；
   - **断言 B**：每条 entry 的 `class` 与 `.gitignore` 实况一致（`runtime-only` ⇒ 被忽略、`committed` ⇒ 未被忽略；`kind=dir` 用 `<path>/.probe` 探针，`kind=file` 直接查路径）；
   - `tests/unit/test_layout_cmd.py`：`rddf layout --json` 两次输出字节一致 + `schema_version` / `tool_version` 存在；
   - `tests/integration/test_doctor_layout.bats`：三支判据各一例 + 本仓自身 0 finding + `.rddf/` 不存在时 0 finding。

## Acceptance

- [ ] `_lib/core/rddf_layout.py` 导出 `RDFF_LAYOUT`；每条含 `path` / `kind` / `read_by` / `write_by` / `required_when` / `transient` / `class` / `severity`；取值域闭合；`path` 唯一且按字典序输出
- [ ] `rddf layout --json` 在本仓输出 **0 条 finding 语义等价**的清单：`entries` 数 = 14（首版），每条含上述 8 个字段，含 `schema_version: 1` 与 `tool_version`
- [ ] **输出确定性**：同仓连续两次 `rddf layout --json` **字节一致**（entries 按 `path` 排序、无时间戳字段）—— 该输出**不经过** `skills/rdd-doctor/scripts/doctor_render.py`，共享 renderer 未被修改（`git diff --stat` 不含该文件）
- [ ] `rdd-doctor --category layout` 在本仓当前 checkout 输出 **0 finding** —— 含实测存在的 `.rddf/.roadmap-migrate-backup-20260820-160838/` 与 `-160955/`（由 `transient: true` 覆盖，`.gitignore:40` 已按其 glob 忽略）
- [ ] 三支判据可复现：① 把 `required_when=always` 的条目目录删掉 ⇒ **WARNING**；② `.rddf/` 下新建 `unknown-dir/` ⇒ **INFO**；③ 把某 `runtime-only` 条目从 `.gitignore` 移除 ⇒ **WARNING**
- [ ] **本 category 永不产生 CRITICAL**：上述三支判据的 exit code 均为 1（不是 2）
- [ ] **最小第三方 fixture**（只含 `project.yaml` + 一个 change 的临时项目，无 `wt/`）上：**WARNING 集合恰好等于** `required_when=always` 的条目集合 —— 不是「exit 0」这种无法区分「校验对了」与「校验没跑」的判据
- [ ] **`wt/` 模式判定**：fixture 无 worktree ⇒ 不因缺 `wt/` 报错；建 `.rddf/wt/x/` 后 ⇒ 该条目被视为「已满足」而非「未登记」
- [ ] **`.rddf/` 不存在** ⇒ 本 category 返回 **0 finding**（项目未启用 rdd）
- [ ] **断言 A/B 通过**：`defaults` 与模块常量里的路径全部被清单覆盖；每条 entry 的 `class` 与 ignore 实况一致 —— **含含 tracked 文件的目录**（`.rddf/state/`，tracked 文件 `.rddf/state/index.md`）：用 `git check-ignore .rddf/state/` 会得到「未忽略」，用探针 `git check-ignore .rddf/state/.probe` 才命中 `.gitignore:10`
- [ ] **`schema_version` 演进策略成文**：同版本只允许「增字段 / 增 entry」；改 entry 语义或删 entry ⇒ 升版本；消费方须忽略未知字段、按 `path` 做集合比较（写进 `docs/architecture/rddf-layout.md`）
- [ ] `docs/architecture/rddf-layout.md` 首段含「真源 = `_lib/core/rddf_layout.py`；本页为解释」+「对外出口 = `rddf layout --json`」+「新增顶层条目三步」+「文件级」一节（6 条 verifier 文件名 + 3 个 handoff 文件，**取自代码**）
- [ ] `docs/architecture/state-and-events.md` 的 handoff 表与 mermaid 图已修成 v4 命名（`.arch-handoff.json` / `.planner-handoff.json` / `.planner-feedback.json`；写入方 `rdd-arch` / `rdd-planner` / `rdd-builder`），不再残留 `guide-design` / `guide-plan` / `guide-ship` / `.design-handoff.json` / `.plan-handoff.json`
- [ ] 三处散文补链到位（`state-and-events.md` / `extension-points.md` / `ADR-0026`，ADR 处仅加描述性链接、不改决策）
- [ ] `docs/architecture/README.md` 的 Doc Map 表已含 `rddf-layout.md` 一行
- [ ] `skills/rdd-doctor/SKILL.md` description **不再含固定 category 数目**；`:26` usage 行的 category 枚举与 `_CHECKERS` 实况一致（无遗漏项）；category 说明表含 `layout` 一行
- [ ] 边界声明成文：本清单描述**默认布局**；`RDDF_STATE_DIR` 重定向（`_lib/session_stats.py:24`、`_lib/rfc_interview_state.py:17`、`_lib/subagent_strategy.py:104`）不在契约内
- [ ] 回归：`./test.sh --quick` 不新增失败；`git diff --stat` 不含「把现有路径引用改成读常量」的改动，且**不含** `skills/rdd-doctor/scripts/doctor_render.py`

## Capabilities

- MUST: `RDFF_LAYOUT` 是 `.rddf/` 布局的唯一声明点；新增顶层条目必须同时改它，否则 doctor 报「未登记」（INFO，不阻断）
- MUST: `read_by` / `write_by` 逐条有代码依据（提交说明里给出 `file:line`），禁止凭直觉归类
- MUST: `class` 直接复用 ADR-0026 的两分类，不引入第三套
- MUST: doctor `layout` 只诊断、**不修改任何文件**（与既有 category 一致），且只扫一层
- MUST: 清单的对外出口是 `rddf layout --json`；**不承诺** `_lib.core.rddf_layout` 的 import 路径是稳定 API
- MUST: `required_when` 为 `worktree` 的条目在非 worktree 项目上不产生 finding
- MUST: `kind=dir` 的 ignore 判定必须用探针路径 `<path>/.probe`，不得直接查目录路径
- SHOULD: `external-tool` 条目（`config/`）在人类输出里单独分组并注明「rdd 不读不写」
- SHOULD: 文档页「新增顶层条目三步」与 ADR-0026 §41-44 措辞一致，避免两处流程分叉
- SHOULD: 未登记条目报 INFO 而非 WARNING —— 第三方自建 `.rddf/` 子目录是**允许**的，doctor 不阻断；文档需说明「用户自建目录不需上游登记」

## Impact

- **新增**：`_lib/core/rddf_layout.py`、`_lib/cli/layout_cmd.py`、`skills/rdd-doctor/scripts/checks/layout_check.py`、`docs/architecture/rddf-layout.md`、`tests/unit/test_rddf_layout.py`、`tests/unit/test_layout_cmd.py`、`tests/integration/test_doctor_layout.bats`。
- **改动**：`skills/rdd-doctor/scripts/doctor_main.py`（`_CHECKERS` 加一行）、`_lib/cli/__init__.py`（`_ROUTES` + `_SUBCOMMAND_DESCRIPTION`）、`_lib/cli/__main__.py`（`_NO_STATE_CHECK` 加 `layout`）、`skills/rdd-doctor/SKILL.md`（description 去数字 + usage 枚举 + category 表）、`docs/architecture/{state-and-events,extension-points}.md`（补链 + 修表）、`docs/architecture/README.md`（Doc Map 索引）、`docs/adr/ADR-0026-*.md`（一处描述性链接）。
- **兼容性**：
  - 不改变任何现有路径取值与读写行为 ⇒ 默认行为零变化；
  - 新增 category 不影响既有 category 的退出码聚合 —— `exit_code_for`（`skills/rdd-doctor/scripts/doctor_render.py:27-43`）的规则是「有 CRITICAL → 2；否则有任何 finding → 1；无 finding → 0」，**不是**「按 severity 取最大」（INFO 与 WARNING 都映射到 1）；
  - 新增 `rddf layout` 子命令是**纯新增**，不改既有子命令行为；`rddf --help` 的子命令列表由 `list_commands()` 自动派生（`_lib/cli/__init__.py:120-122`），无需手工同步。
- **风险 ①**：清单与硬编码路径仍是**双写**。缓解是断言 A（覆盖 `defaults` + 5 个模块常量），但拼接形态（`Path(root) / ".rddf" / X`）仍不在断言内 —— 该边界必须在 `docs/architecture/rddf-layout.md` 显式登记，不得声称「全覆盖」。
- **风险 ②**：`class` 与 `.gitignore` 的一致性判定依赖 `git check-ignore`，在非 git 仓库里该命令返回 128 ⇒ 判据③ 须先判「是否 git 仓库」并跳过（不报 finding）；`.gitignore` 文件缺失时同样跳过并给出 INFO 说明。不得把「环境不可用」报成「不一致」。
- **风险 ③**：与 `_lib/check_project_setup.sh:18-39` 的三条既有判定（`state/`、`wt/` 被忽略 + `plans/` 未被忽略）**事实重复**。该脚本是 bash + grep、checker 是 Python，无可复用接口 ⇒ 本项**不消除**该重复，只在文档里写明两个出口的定位：`rddf setup` 是修复入口，`rddf doctor --category layout` 是诊断入口。
- **风险 ④**：在 worktree 内运行 doctor 时，`.rddf/wt/<name>/` 是完整 checkout，扫描必须严格一层，否则会成片误报。
- **依赖**：无。消费方（opencode-config 的 `workspace.json`）属外部工具私有，**不进本清单**。
