# build 侧证据核对：rddf-layout-manifest（improvement）

> 审查者：build agent（**技术/证据核对**，非 planner 的 metis 轮次 —— metis 1 轮已用于 `.rddf/reviews/rddf-layout-manifest-planner-review.md`，本轮不消耗 planner 预算）
> 对象：`.rddf/improvements/rddf-layout-manifest.md`（+ `feat-rddf-layout-manifest.md`、`improvement-suggestions.md` 末行）
> 基线：`master @ a143469`（工作树含 3 个未跟踪新工件）
> 日期：2026-11-16

## 判定

**有条件通过（CONDITIONAL）—— 需 planner 修订后再立项。**

立意成立：ADR-0026 已把分类维度定好，缺的是可执行形态；把「目录里有什么」变成机器可读真源，方向正确，证据链（ADR-0026 / defaults / doctor 现状）经核对属实。

但**验收集有 4 条 BLOCKER**：2 条在本仓必然失败（假红）、1 条与共享代码结构性矛盾（不可能满足）、1 条会把已废弃的 v3 名字固化进新文档 —— 这 4 条都不是措辞问题，逐条证据见下。

---

## 一、事实核对结果

| 文档断言 | 核对 | 证据 |
|---|---|---|
| ADR-0026:26-44 定义 runtime-only / committed 两分类 | ✅ | `docs/adr/ADR-0026-internal-metadata-namespace-convention.md` Decision 段表格 + §添加新 metadata 类别指引 4 步 |
| `_lib/core/defaults.py:24-31` 有 2 条路径类 DEFAULTS | ✅ | `state.path` / `event_log.path` |
| `defaults.py:67-71` 有 5 个模块常量（mirror 注释自承） | ✅ | `STATE_VECTOR_PATH`/`EVENT_LOG_PATH`/`MEMORY_PATH`/`DETECTOR_PLUGIN_DIR`/`ACTION_PLUGIN_DIR` |
| `_lib/issue_reporter.py:161` 用 `Path(root)/".rddf"/"issues"` | ✅ | 另有 `os.path.join(root,".rddf","state")` 形态（`_lib/cli/__main__.py:216` 等）⇒ Out of Scope「反向 grep 失明」成立 |
| `state-and-events.md:47-55` 只覆盖 3 个 handoff | ✅（**但内容已过期**，见 B-4） | Layer 3 表格 3 行 |
| doctor 24 个 category、无布局类 | ✅ | `doctor_main.py:27-54` `_CHECKERS` 实测 24 条 |
| `rdd-doctor/SKILL.md` description 写「13 file categories」 | ✅ | `SKILL.md:4` + `:10`（实际 24）⇒ 漂移属实 |
| `gitignore_check.py` 只核 `openspec/`，不核 `.rddf/` | ✅ | 该文件只读 `project.yaml` 的 `git.openspec_tracked` |
| `rddf init` 不建 `.rddf/` | ✅ | `_lib/cli/init_cmd.py:27` `_INSTALL_SOURCES = [skills,_lib,package.json,rddf.sh]`；`setup_cmd.py` 只做 ai-context |
| `_lib/verifier/state_paths.py` 有 6 条 verifier 文件名 | ✅（行号是 34-41，不是 30-40） | `SKILL_OWNS_PATHS` 6 条 |
| `check_project_setup.sh:27-31` 是既有 ignore 判定 | ✅（但**不可复用**，见 S-4） | Check1/2/3 = `state/`、`wt/` 被忽略 + `plans/` 未被忽略 |
| `RDDF_STATE_DIR` 重定向存在 | ✅ | `_lib/session_stats.py:24`、`_lib/rfc_interview_state.py:17`、`_lib/subagent_strategy.py:104` |

---

## 二、BLOCKER（4）

### B-1 「输出确定性」AC 与共享 renderer 的 timestamp 结构性冲突

- **AC 原文**：第 7 条「同仓连续两次 `--json` 字节一致（entries 按 `path` 排序、**无时间戳字段**）；含 `schema_version: 1` 与 `tool_version`」。
- **实现事实**：`skills/rdd-doctor/scripts/doctor_render.py:97-110` 的 `render_json()` **无条件**写 `"timestamp": datetime.now(timezone.utc).isoformat()`；payload 键只有 `{timestamp, categories_checked, findings, summary}`。
- **后果**：任何走 `render_json` 的输出**不可能**字节一致 ⇒ AC 第 7 条**按当前设计不可满足**。若为满足它而改 `doctor_render.py`，则**全部 24 个 category 的 JSON 契约同时变更**（timestamp 字段消失或增 version 字段），而 Impact 清单**未列 `doctor_render.py`** ⇒ 实施者要么偷偷改共享文件（超范围），要么交付一条必然失败的 AC。
- **处置（二选一，推荐前者）**：
  - (a) 把 AC 降为「**layout payload 段**字节一致（不含共享 `timestamp` 字段）」，`schema_version`/`tool_version` 放在 layout 自己产出的段里；`render_json` 不动。
  - (b) 把 `doctor_render.py` 纳入 Impact，并单独立一个「doctor JSON 契约 v2」的 change（涉及 24 个 category 的消费方兼容，不应搭车）。

### B-2 「机读清单」没有交付通道；`tool_version`/`schema_version` 也不在既有 JSON 里

- **文档定位**：主题写「`.rddf/` **机读清单**」；来源写「供第三方项目与 e2e 测试床遵循」；Out of Scope 写「**不新增 `rddf layout` 子命令** —— 契约出口复用既有 JSON 通道：`rddf doctor --category layout --json`」。
- **事实**：`rddf doctor --category layout --json` 的输出是 **findings 列表**，不是 `RDFF_LAYOUT` 清单内容 ⇒ **第三方拿不到清单本身**。被砍掉的 `rddf layout` 恰恰是唯一能给清单的出口。
- **同时**：`tool_version` / `schema_version` 在 doctor 现有 JSON 里**不存在**（见 B-1 同源），要加就得动共享 renderer。
- **内部矛盾**：架构依据第 1 条说「这类知识不能靠散文维护：布局演进时散文不会红」；而砍掉清单出口后，剩下的机器可读形态只有 Python 常量 + 散文表格 —— 散文正是被否掉的形态。
- **处置**：planner 必须明确「清单视图」的契约出口，三选一：
  - (a) `RDFF_LAYOUT` 作为 Python 常量随 `rddf init` 一起安装（`_lib/` 整个目录被复制，`init_cmd.py:76-83`）⇒ 第三方可 `import`，但**必须写明 import 路径不是稳定 API**；
  - (b) 恢复一个只读 `rddf layout --json` 子命令（推翻 YAGNI 决策，须写明消费者是谁 —— opencode-config 的 `workspace.json`？e2e 测试床？）；
  - (c) 明确放弃「第三方消费机读清单」这一定位，把 `docs/architecture/rddf-layout.md` 的表格定为**人读契约**、机读清单只服务 doctor 内部 ⇒ 需同步下调「来源」里的第三方/e2e 诉求，否则立意与交付不匹配。

### B-3 断言 B / 判据③ 用 `git check-ignore` 直查目录 ⇒ 本仓必然假红

- **AC 原文**：断言 B「每条 entry 的 `class` 与 `git check-ignore` 结果一致（`runtime-only` ⇒ 被忽略、`committed` ⇒ 未被忽略；用 `git check-ignore`）」；AC 第 2 条「本仓输出 **0 finding**」。
- **实测（本仓）**：

  ```
  $ git check-ignore -v .rddf/state/            → NOT-IGNORED   ← .rddf/state/ 是 runtime-only
  $ git check-ignore -v --no-index .rddf/state/ → .gitignore:10:.rddf/state/
  $ git check-ignore -v .rddf/state/.probe       → .gitignore:10:.rddf/state/
  $ git check-ignore -v .rddf/wt/                → .gitignore:11:.rddf/wt/
  $ git check-ignore -v .rddf/issues/            → .gitignore:14:.rddf/issues/
  ```

- **机制（已用最小复现确认，`/tmp/opencode/ci-test2`）**：**目录内含 tracked 文件时，git 不把该目录计入 exclude 列表** ⇒ `git check-ignore <dir>/` 返回 NOT-IGNORED。本仓 `.rddf/state/` 含 tracked 文件 `.rddf/state/index.md`（`git ls-files .rddf/state` → 1 条）⇒ 正好命中该情形。
- **后果**：`state/`（runtime-only）会被判据③ 报「未忽略」warning ⇒ **AC 第 2 条「本仓 0 finding」与断言 B 同时失败**。
- **处置**：把判定规则写死进「范围」与验收：`kind=dir` ⇒ 用**探针文件** `<path>/.probe`（或 `--no-index`）判定；`kind=file` ⇒ 直接查路径。并补一条 AC：「对含 tracked 文件的目录（`state/`），判定结果为 ignored」。

### B-4 「文件级」一节的数据源已过期，会把 v3 遗留名固化进新文档

- **文档要求**：新页含「文件级」一节，含「`state-and-events.md` 的 **3 个 handoff 文件**」。
- **该表现状（`docs/architecture/state-and-events.md:47` 标题 + `:53-55` 表体；`:14-16` 的 mermaid 图同样过期）**：

  | File | Written by | Read by |
  |---|---|---|
  | `.arch-handoff.json` | `guide-arch` | `guide-design`, `guide-plan` |
  | `.design-handoff.json` | `guide-design` | `guide-plan` |
  | `.plan-handoff.json` | `guide-plan` | `guide-ship` |

  写入/读取方是 **v1~v3 的 skill 名**（现已 `rdd-arch`/`rdd-planner`/`rdd-builder`），文件名 `.design-handoff.json` / `.plan-handoff.json` 在 v4 已废弃 —— `_lib/cli/guide_cmd.py:172-173,199-200` 只把它们当 **legacy 探测**，`_lib/builder_deps.py:42` 用的是 `.planner-handoff.json`，`_lib/builder_feedback_router.py:31` 用 `.planner-feedback.json`。
- **后果**：照抄该表 ⇒ 新文档从第一版起就是错的，且把废弃名固化成「布局事实」—— 与本项「消除漂移」的立意正好相反。
- **处置**：① 「文件级」一节**以代码为源**（`_lib/builder_deps.py:42` / `_lib/builder_feedback_router.py:31` / `_lib/verifier/state_paths.py:34-41`），不要从散文表抄；② 本次**顺手修 `state-and-events.md` 的过期表**（它本来就在「散文补链」范围内 —— 补链 ≠ 只加一行链接，而是把该表的 skill 名与文件名修成 v4）；③ `state-and-events.md` 的散文中还写着 `guide-design`/`guide-plan`/`guide-ship`，一并修正。

---

## 三、SHOULD_FIX（9）

| # | 问题 | 证据 | 处置 |
|---|---|---|---|
| **S-1** | Severity 词汇与退出码语义没定死；兼容性段描述与实现不符 | 实现是「有 CRITICAL→2；否则有 finding→1；无→0」（`doctor_render.py:27-43`），**不是**「按 severity 取最大」（INFO/WARNING 都映射到 1）；doctor 只有 `CRITICAL/WARNING/INFO`（`:12-16`），**没有 error** | 范围表加 `severity` 列（用既有三档）；判据①明确用 CRITICAL 还是 WARNING 及理由；兼容性段改成实现原话 |
| **S-2** | `rddf init` 不建 `.rddf/`，但 `required_when=always` ⇒ fresh 第三方项目必然报错 | `init_cmd.py:27` 只装 `skills/_lib/package.json`；`setup_cmd.py` 只做 ai-context | 二选一：把惰性创建的目录（`state/` 等）从 `always` 降级；或明确「fresh 项目报 error 是预期行为（引导执行首条命令）」并写进文档 |
| **S-3** | 判据②的 glob 匹配语义未定义 | `path` 允许 glob，但未说匹配规则与 `kind` 是否参与。坑：本仓同时有 `roadmap`(dir) 与 `roadmap.md`(file)；planner review 的未闭合项建议「最长前缀 entry」⇒ `roadmap.md` 会被 `roadmap` 吃掉（结果恰好对但语义是蒙的） | 范围表写死：精确匹配优先 → glob 用 fnmatch → 都落空才判「未登记」；`kind` 不参与路径匹配，只用于存在性检查与探针形式 |
| **S-4** | 与 `check_project_setup.sh` 事实重复，且「复用既有判定」不可机械实现 | 该脚本 Check1/2/3 = `state/`、`wt/` 被忽略 + `plans/` 未被忽略（`:18-39`），与判据③/断言 B 同源；但它是 **bash+grep**，checker 是 Python ⇒ 没有可 import 接口，只能重写 | 承认重复并在文档写明两个出口的定位（`rddf setup`=修复入口，`doctor layout`=诊断入口）；或显式登记为「本项不消除该重复」的风险 |
| **S-5** | Impact 漏了 3 个必然要改的文件 | ① `skills/rdd-doctor/scripts/doctor_render.py`（若按 AC 加 version 字段）；② `skills/rdd-doctor/SKILL.md:26` **硬编码了 category 花括号枚举**（实测 23 个，**已漏 `baseline-freshness`** ⇒ 本来就在漂移）；同文件 `:74` 起的 category 说明表也要加一行；③ `docs/architecture/README.md` 的 Doc Map 表（该文件明写 Update Convention：新增 `architecture/*.md` 必须在同一 change 内更新） | 补进 Impact；② 的枚举建议改为「从 `_CHECKERS` 动态生成」或直接删掉花括号列表 |
| **S-6** | 「实测存在的」清单里 3 项在本仓不存在 | 本仓 `.rddf/` 顶层实测只有：`improvements/ issues/ plans/ project.yaml reviews/ roadmap/ roadmap.md state/ wt/` + 2 个 backup 目录。**`config/`、`orch_plans/`、`skill-profiles/` 都不存在**；`orch_plans` 在 `_lib/`+`skills/` 全仓**零引用**（`skill-profiles` 仅 `skills/rdd-session-bootstrap/` 用） | 措辞分「实测存在」与「仅文档提及/外部约定」两类；`orch_plans` 无引用则不进清单（否则判据②要求第三方建一个没人用的目录） |
| **S-7** | `improvement-suggestions.md` 摘要与 improvement 正文口径不一致 | 摘要写「路径常量仅 **2** 个 (`defaults.py:70-71`)」；正文写「**5** 个模块常量 + 2 条 DEFAULTS 条目」。实测 `defaults.py:67-71` 确为 5 个 ⇒ 摘要少算 | 同步摘要 —— 本项立意就是消除漂移，两个新工件自身不能互相漂 |
| **S-8** | AC 第 2 条把基线 SHA 写死 | 「本仓（master @ **a143469** + 本项改动）输出 0 finding」⇒ 仓库前进一个 commit 即失效（今天 HEAD 恰为 a143469，属巧合） | 改成不依赖 SHA 的相对判据（「本仓当前 checkout ⇒ 0 finding」）或「基线 = 本 change 的父 commit，由 baseline 指明」 |
| **S-9** | 判据②让「第三方自建 `.rddf/` 子目录」变成必须找上游登记 | 目标（架构依据第 2 条）是「声明扩展点边界」，但任何未登记顶层条目都 warning，而本仓**没有用户自定义条目的登记入口**（`read_by/write_by` 虽有 `user` 取值，却没定义怎么把用户条目声明为已知） | 要么定义用户目录通道（如 `.rddf/local/` 约定或 `.rddf/rddf-layout.local.json`），要么判据②降为 INFO 并写明「未登记不阻断」 |

---

## 四、NITS（4）

| # | 内容 | 证据 |
|---|---|---|
| N-1 | 行号偏差：`_lib/verifier/state_paths.py` 的 6 条在 `:34-41`（非 `:30-40`）；`doctor_main.py` 的 24 个 category 在 `:27-54`（非 `:23-47`）；`state-and-events.md` 的 handoff 表体在 `:53-55`（文档写 `:47-55`） | 实测 |
| N-2 | 「散文补链」包含改**已采纳** ADR 正文（ADR-0026 状态 = 已采纳）。按治理面属「描述性措辞补充」，builder 可执行，但建议实施时在行尾标注「本行不改变 ADR 决策」，避免被当成决策修订 | `ADR-0026-*.md:3` |
| N-3 | 判据②应明确**只扫 `.rddf/` 顶层一层**，且 `path` 相对 `.rddf/`（文档已写「禁止递归」✓，但没写 `path` 的相对基准在 `kind=file` 与 `kind=dir` 下是否统一） | — |
| N-4 | `docs/architecture/extension-points.md:29-30` 已写 `.rddf/detectors/` `.rddf/actions/` —— 补链时不必重复展开，直接加链接即可，避免两处各写一份目录说明 | 实测 |

---

## 五、对 planner metis 13 条 finding 的落地质量复核

metis 轮次已在 `.rddf/reviews/rddf-layout-manifest-planner-review.md` 完成，13 条全部标「采纳」。逐条核对落地质量：

- **落地到位（9 条）**：`read_by`/`write_by` 可观测字段 ✓（范围表 + Capabilities MUST）、删除 `created_by` ✓、`class` 复用 ADR-0026 ✓、`transient` + glob 覆盖 backup 目录 ✓、删反向 grep 改断言 A/B ✓、`schema_version` 演进策略成文 ✓、`required_when` 三态 ✓、最小 fixture AC（error 集合恰好相等）✓、文档降级为「表格 + 三步」+ 补「文件级」✓、SKILL.md 去数字 ✓、砍 `rddf layout` 子命令 ✓、`RDDF_STATE_DIR` 声明 ✓、与既有 category 边界 ✓。
- **落地打折（2 条）**：
  - **finding #3 的「断言 A 前缀匹配」被降级为未闭合项** ⇒ 直接引入了 S-3 的坑（`roadmap` vs `roadmap.md`）。
  - **finding #13 的「复用 `_lib/check_project_setup.sh` 既有判定」不可实现** ⇒ 引入 S-4 的重复。
- **未被 metis 捕获、但本轮新发现（4 条）**：B-1（timestamp 冲突）、B-2（清单无出口）、B-3（check-ignore 目录探针）、B-4（文件级数据源过期）+ S-1~S-9。

⇒ metis 1 轮已用尽且**不足以覆盖本项**，本轮的 4 条 BLOCKER 全部落在 metis 的检查面之外（**可执行性/契约出口/工具语义**，而非「隐藏意图/歧义/AC 缺失」）。修订后建议**不再追加 metis 轮次**，直接由 planner 修订文档 + builder 侧复核本报告的处置项。

---

## 六、建议的修订清单（可直接执行）

**planner 侧（改 improvement 文档）**

1. 「范围」表加 `severity` 列；判据①定档；兼容性段改写 exit_code 描述（S-1）。
2. 「范围」判据②/③ 写死匹配与探测规则：精确 → fnmatch glob → 未登记；`kind=dir` 用 `<path>/.probe` 探针（S-3、B-3）。
3. 明确清单视图的契约出口，并同步「来源」与 Out of Scope（B-2）。
4. AC 第 7 条降为「layout payload 段字节一致」，`tool_version`/`schema_version` 落到 layout 自有段（B-1）。
5. AC 第 2 条去掉写死的 SHA（S-8）；补一条 AC：「含 tracked 文件的目录（`state/`）判定为 ignored」（B-3）。
6. 「文件级」一节改以代码为源；把 `state-and-events.md` 的过期 handoff 表修成 v4（B-4）。
7. Impact 补 `doctor_render.py`（若选 B-1(b)）、`SKILL.md:26`+`:74`、`docs/architecture/README.md`（S-5）。
8. 措辞修正：「实测存在」三项拆分、`orch_plans` 去留、`improvement-suggestions.md` 摘要同步（S-6、S-7）。
9. 补 `required_when=always` 对 fresh 第三方项目的后果说明（S-2）与用户自定义条目的登记通道（S-9）。

**builder 侧（实施时）**

10. 探针判定 + 只扫一层（不得递归进 `wt/`）。
11. 判据②与 `check_project_setup.sh` 的重复关系写入文档风险（S-4）。
12. 改 ADR-0026 正文时标注「不改变决策」，走描述性措辞路径（N-2）。

---

## 七、遗留清扫（本轮范围）

- 本轮为只读审查，未产生代码/配置改动；未新增 TODO、临时日志、被 skip 的测试。
- 仓库工作树原有 3 个未跟踪工件（`rddf-layout-manifest.md` / `feat-rddf-layout-manifest.md` / `rddf-layout-manifest-planner-review.md`）+ 2 个已修改文件（`.rddf/roadmap.md` / `improvement-suggestions.md`），**非本轮产生，未处置**。
- 本报告为唯一新增文件：`.rddf/reviews/rddf-layout-manifest-builder-review.md`。
- **未 commit**（按规矩等确认）。
