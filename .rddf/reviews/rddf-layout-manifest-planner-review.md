# planner 审稿：rddf-layout-manifest（improvement）

> 审查者：metis 1 轮（planner 固定审查者）
> 对象：`.rddf/improvements/rddf-layout-manifest.md`（+ `.rddf/roadmap/features/feat-rddf-layout-manifest.md`、`improvement-suggestions.md` 末行）
> 决策基线：用户 2026-11-16 选定「只做产品侧」—— 消费方（opencode-config）不动，布局知识落在产品仓

## 判定

metis 返回 P0×5 / P1×4 / P2×3。**其中 4 条会直接产出一个错误的契约**，不是措辞问题：

1. **`owner ∈ {product, third-party}` 与事实不符**：`wt/` 由 git 建（`_lib/worktree.sh`）、`issues/` 由 rdd 读写（`_lib/issue_reporter.py:161-163`）、`reviews/` 只由 agent 写（`_lib/` 与 `skills/` **零引用**，实测）、`config/` 由外部工具建且 rdd 不读。草稿把这四处写成「判断」，等于放弃了可校验性。
2. **`created_by=rddf` 但实为手工 —— 不可观测**：没有任何机制能区分手工 `mkdir` 与代码 `mkdir`。留着就是一条实现不了且必误报的判据。
3. **反向 grep 断言失明**：真实写入是 `Path(root) / ".rddf" / "issues"`（`issue_reporter.py:161`）与 `os.path.join(root, ".rddf", "state")`，`grep '\.rddf/[a-z_-]+'` 两者都看不到 ⇒ 它验的是文档散文，不是布局消费方。且会在 docs 里命中历史假想名（`docs/schemas/README.md:41` 的 `.rddf/triggers/*.yaml`，真实是 `.rddf/state/triggers.json`）⇒ 把文档错误固化成布局事实。
4. **AC 自相矛盾**：仓库现在就有两个未登记顶层条目（`.rddf/.roadmap-migrate-backup-20260820-160838/`、`-160955/`），而草稿 AC 要求「干净仓库 exit 0」。

## 逐条处置

| # | metis finding | 级别 | 处置 | 落点 |
|---|---|---|---|---|
| 1 | `owner` 二分不成立，需可观测字段 | P0 | **采纳**：改为 `read_by` / `write_by` ∈ {rdd, agent, user, git, external-tool}，要求逐条给 `file:line` 依据 | 架构依据 + 范围表 + Capabilities MUST |
| 2 | `created_by=rddf` 实为手工 —— 不可观测 | P0 | **采纳**：字段删除 | 范围表 |
| 3 | 应复用 ADR-0026 的 `runtime-only` / `committed` 分类 | P0 | **采纳**：`class` 直接取 ADR-0026 两分类，`gitignored` 由它派生；架构依据补 ADR-0026 §26-44，文档加一句指向 | 架构依据 + 范围表 `class` 行 + In Scope 第 3 条 |
| 4 | 已存在的顶层噪声会让 AC 自相矛盾（backup 目录） | P0 | **采纳**：加 `transient` 字段与 `.roadmap-migrate-backup-*` glob 条目；判据②改为「未登记**且非 transient**」；AC 明确要求本仓 0 finding（含两个 backup 目录） | 范围表 + 判据② + AC 第 2 条 |
| 5 | 删/降级反向 grep 断言 | P0 | **采纳（替换）**：删除反向 grep，改为断言 A（`defaults.DEFAULTS` + 5 个模块常量被清单覆盖）+ 断言 B（`class` 与 `git check-ignore` 一致）；失明边界写进 Out of Scope 与风险 | Out of Scope + What Changes 5 + 风险① |
| 6 | `schema_version` 演进策略缺失 | P0 | **采纳**：成文（增字段/增 entry 不升版、改语义或删 entry 升版、消费方忽略未知字段、按 `path` 集合比较）+ 输出确定性 AC | AC 第 7/8 条 + 文档第 3 条 |
| 7 | `required` 单布尔对 `wt/` 误报 | P1 | **采纳**：改 `required_when ∈ {always, worktree, never}`；AC 加「无 worktree 不报错 / 建了视为已满足」 | 范围表 + AC 第 5 条 |
| 8 | 缺最小第三方 fixture AC（「exit 0」区分不了「校验对了」与「校验没跑」） | P1 | **采纳**：AC 改为「error 集合**恰好等于** `required_when=always` 集合」 | AC 第 4 条 |
| 9 | 文档层过度设计（生成/逐字比对），却漏了「文件级」 | P1 | **采纳**：文档简化为「表格 + 新增条目三步」；取消比对测试；补「文件级」一节（6 条 verifier 文件名 + 3 个 handoff） | In Scope 第 3 条 + AC 第 9 条 |
| 10 | `SKILL.md` 写死 category 数字本身是漂移源 | P1 | **采纳**：改为不写数字（不是改成 24） | In Scope 末条 + AC 第 10 条 |
| 11 | `rddf layout` 子命令零消费者（YAGNI） | P2 | **采纳**：砍掉子命令，契约出口复用 `rddf doctor --category layout --json` | Out of Scope + What Changes 2 |
| 12 | `RDDF_STATE_DIR` 重定向使「`.rddf/state` 唯一」不成立 | P2 | **采纳**：文档与 AC 声明「本清单描述默认布局」 | AC 第 11 条 + 风险 |
| 13 | 与既有 category 职责边界 | P2 | **采纳（写入依据）**：实测 `gitignore_check.py` 只核 `openspec/` 与 `project.yaml`，不核 `.rddf/` ⇒ 无重叠；`.rddf/*` 的忽略判定归 layout，`check_project_setup.sh:27-31` 的 `rddf_wt_ignored` 保留并注明关系 | 风险② |

## 未闭合项（交实施时确认）

- 断言 A 的前缀匹配规则需在实现时定死（`state.path` = `.rddf/state/state-vector.json` 应被 entry `state` 覆盖）—— 用「最长前缀 entry」还是「显式 `covers` 列表」，实现时择一并写进单测。
- `.gitignore` 缺失时的断言 B 行为：需先判文件存在（复用 `_lib/check_project_setup.sh:27-31` 既有判定），避免「缺 `.gitignore`」被两处各报一遍。
- `.rddf/wt/` 扫描必须严格一层（`scandir` 不递归）—— 在 worktree 内跑 doctor 时它是完整 checkout，递归会成片误报。
