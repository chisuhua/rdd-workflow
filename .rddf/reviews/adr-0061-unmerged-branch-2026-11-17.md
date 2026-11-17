# ADR-0061 审稿报告 —— 合入门（归档不代劳合并，但未合入不得归档）

> 对象：`docs/adr/ADR-0061-archive-gate-refuses-unmerged-branch.md`
> 角色：architect（opencode build agent 的角色矩阵）
> 档位：`arch`
> 审稿：oracle 1 轮 + critic 5 轮（用户批准第 3 轮起的后续复审，直到 APPROVE）
> 结论：**已采纳（2026-11-17）**

## 一、oracle 咨询（1 轮，2026-11-17）

**判定**：REJECT（方向成立，但判据可满足性 / 保护面 / 状态机闭合三处有硬伤）。

| # | finding | 处置 |
|---|---|---|
| A-1 | 门只覆盖 worktree 模式，而被合法化的 lightweight 走 `phase3_archive.sh` 的 inline 分支 ⇒ 合起来在**被合法化的模式上没有任何合入判定** | ✅ 采纳 ⇒ 两份 ADR 互相点名：ADR-0036 修订的前置立项必须自带合入判定，或在它落地前 lightweight 保持不可达（V-G） |
| A-2 | 「worktree 未提交改动 ⇒ 拒绝」按字面实现会**永久拒绝**（v4 的 artifact 复制使 `.rddf/plans/<name>.md` 在 worktree 里呈未跟踪态） | ✅ 采纳 ⇒ 决策 2 ① 加**噪声排除**（系统复制的 `openspec/changes/<name>/`、`.rddf/plans/<name>.md` 不算未提交改动）+ **优先级高于「已合入」**；V-3 补判据 |
| A-3 | 内容等价兜底是 tip-to-tip 比较 ⇒ 「squash/rebase 不被锁死」是 over-claim | ✅ 采纳 ⇒ 改为 **patch-id 判据**（`git cherry`），并把 over-claim 降级为条件句 |
| A-4 | state 2「ref 缺失 ⇒ 放行」与 `verifier-lifecycle:100` 直接冲突 | ✅ 采纳 ⇒ 「ref 缺失」从「无法判定」挪到**拒绝**（⓪ 前置存在性检查），与 fail-closed 对齐 |
| A-5 | 指引文案在最可能的失败场景（execute 默认不 commit）里给错药 | ✅ 采纳 ⇒ 指引按失败原因**分叉**（合并 / 先提交 / 先提交后合并 / 分支不存在） |
| A-6 | `archive-auto-commit` 的 lightweight MUST 被一刀切改成负向断言 = 免掉一条今天仍然红的义务 | ✅ 采纳 ⇒ R4 **正向重指向**为「`rdd-builder` P3 lightweight MUST 调用 `commit_archive_moves`」，且该 delta **主责在 ADR-0061** |
| A-7 | 退役面漏算（4 处 → 9 份 spec） | ✅ 采纳 ⇒ 退役清单扩到 R1~R10，并量化全局残余面（**204 处 / 47 份 spec**）后移入 backlog |
| A-8 | 「文档领先实现」只被「列为前置」缓解了一半 | ✅ 采纳 ⇒ V-G 把解除条件写成「建分支 **且** 归档路径补齐（含分支合入）都落地前」 |
| A-9 | 选项 A 的拒绝理由是循环的（同一份 ADR 正在改那两份 spec） | ✅ 采纳 ⇒ 改写为两条更硬的理由：**维度错配**（与 ADR-0036 修订直接冲突）+ **授权主体错位**（归档不该替人改默认分支）；spec 冲突降级为「需要 delta 的成本」 |
| A-10 | `openspec_tracked=false ⇒ serial` 的行为可留、理由必须换 | ✅ 采纳 ⇒ 行为与既有测试不变，注释措辞随 ADR-0036 修订改写 |

## 二、critic 审稿（5 轮）

### 第 1 轮 —— REJECT（2 BLOCKER + 8 SHOULD_FIX + 4 NITS）

| finding | 处置 |
|---|---|
| BLOCKER 1：dirty 检查缺噪声排除 / 优先级 / 返回值定义 | ✅ 全部补入决策 2 ① 与 V-3 |
| BLOCKER 2：内容等价用 tip-to-tip ⇒ over-claim | ✅ 改 patch-id（`git cherry`），over-claim 降级为条件句 |
| SHOULD_FIX：state 2 与 `verifier-lifecycle` 冲突 | ✅ 「ref 缺失」改为拒绝 |
| SHOULD_FIX：指引文案不分叉 | ✅ 分叉为四支 |
| SHOULD_FIX：dirty 三态返回值没写进定义 | ✅ 已写入 |
| SHOULD_FIX：`opt-in` + `FORCE_BRANCH_DELETE` 的组合未点名 | ✅ 决策 4 明写「不得同时生效」，实现上拒绝该组合（V-6） |
| SHOULD_FIX：合入门应先于 AC 门 | ✅ 决策 5 + V-7 |
| SHOULD_FIX：false 分支的 spec delta 要列完整步骤清单 | ✅ 决策 7 + Consequences 如实记录既有省略（不 normative 化） |
| SHOULD_FIX：命名撞车（「归档门」已指 AC 门） | ✅ 文档抬头加**术语**块：「合入门」= `archive_premerge_check`；「归档门」= `archive_gate_check` |
| SHOULD_FIX：opt-in 使用频率需纳入审计阈值 | ✅ Consequences 写明建议 `ARCHIVE_ALLOW_UNMERGED: 3` |
| SHOULD_FIX：两份 ADR 的影响范围漏 `docs/adr/README.md` | ✅ 已补 + V-13 |
| NIT：文档里的替换字符 | ✅ 已修 |

### 第 2 轮 —— REJECT（2 BLOCKER 残余）

| finding | 处置 |
|---|---|
| BLOCKER 1：V-C 在本 ADR 声明范围内不可满足（退役面少算 ≥9 份 spec） | ✅ 两次修订后收敛：V-C 的判定对象改为**位置级有限集合**（R 表「位置」列），全局残余面量化后移入 backlog |
| BLOCKER 2：R6 重指向到 `rdd-builder` 会造出**假的红 MUST**（该段文字只在 `skills/execute/SKILL.md`） | ✅ R6 改为**收窄为 execute-only**（含删除「Phase 1 / Phase 2 段」限定词 + 3 个 Scenario 一并收窄 + Scenario 3 的 WHEN 重指向） |
| SHOULD_FIX：`RDDF_EXECUTION_ROOT` 机制陈述已死 | ✅ 改为真实通道（`phase2_execute.sh` 写 handoff + `select_worktree.sh` 解析工作区） |
| SHOULD_FIX：过渡态未写 | ✅ 「依赖顺序与过渡态」段：撤销子句的收益要等 ADR-0061 落地 |
| SHOULD_FIX：Status 先于签批声明已修订 | ✅ 签批前用 `AMENDED (pending 2026-11-17)`，收口时统一转正并清 4 处 pending |

### 第 3 轮 —— REJECT（3 BLOCKER：2 残余 + 1 条本轮引入）

| finding | 处置 |
|---|---|
| BLOCKER 1：V-C 的判定对象是 spec 级、处置粒度是位置级 ⇒ 覆盖面大于枚举清单 | ✅ V-C 改为「R 表「位置」列所列的每一处」；R 表新增独立「位置」列（行级）；全局残余面按 204 处 / 47 份 spec 量化并移入 backlog |
| BLOCKER 2：R6 的 3 个 Scenario 未处置 | ✅ R6 的处置扩到 Requirement 1 正文 + 3 个 Scenario，并保留 Scenario 结构（避开 openspec 校验） |
| BLOCKER 3：⓪ 的传播缺口（opt-in 覆盖面 / 指引分支 / ⑤→④ 笔误） | ✅ 五处口径统一：⓪ 行补「默认不放行 + opt-in 可覆盖」；新增「opt-in 覆盖面统一」条；指引补第四支；V-5 同步；笔误修正 |

### 第 4 轮 —— REJECT（2 BLOCKER：条款互斥）

| finding | 处置 |
|---|---|
| BLOCKER 1：V-C 第二句与 R1「保留标题」互斥（R1 的标题含 guide-ship ⇒ V-C 恒红） | ✅ V-C 增加**历史标识豁免句**（R1 保留的标题不计入判定，判定对象是正文/断言文本）；R2/R4/R5/R9 的标题改为**一并改写** |
| BLOCKER 2：backlog 把 R6 的 3 个 Scenario 重复分配 | ✅ backlog 删除这 3 个位置（并注明「不含 R 表已覆盖的位置」） |

### 第 5 轮 —— REJECT（1 BLOCKER）

| finding | 处置 |
|---|---|
| BLOCKER：R1/R2 的「位置」列截断了各自 Requirement 的 normative 范围 ⇒ V-C 可被「半退役」平凡满足 | ✅ R1 扩到 `:202-:217`（含 2 个 Scenario）、R2 扩到 `:125` + `:139-:142`；V-C 新增「判定宽度 = 处置宽度」通则 |

### 第 6 轮 —— **APPROVE**（mergeable: yes；0 BLOCKER，4 SHOULD_FIX 全部采纳）

| finding | 处置 |
|---|---|
| SHOULD_FIX：R1 行未点名 Scenario 2（`:214-:217`） | ✅ 已点名并写明退役 `:216`/`:217` 两条断言 |
| SHOULD_FIX：V-C 通则对「点名 Requirement 的行」与「只点名单个位置的行」适用范围不同 | ✅ 通则按行分两类；R2 的范围显式裁定（`:127-:132`/`:134-:137` 是仍然为真的负向保证 ⇒ 不在处置范围） |
| SHOULD_FIX：负向断言必须带维度限定（否则与 `ship-execution-mode-project-yaml-priority` 的 "execution mode" 用字面矛盾） | ✅ 断言改为「SHALL NOT determine the execution mode（worktree vs lightweight）」，并把 spec 侧术语收敛归 `fix-execution-mode-decision` |
| SHOULD_FIX：「6 份 spec」实为 9 份 | ✅ 已改 |

## 三、评审预算

| 轮次 | 角色 | 判定 | 说明 |
|---|---|---|---|
| 1 | oracle | REJECT | 咨询轮（8 条 blocking） |
| 1 | critic | REJECT | 2 BLOCKER |
| 2 | critic | REJECT | 复审（BLOCKER 1 未闭合 + BLOCKER 2 残余） |
| 3 | critic | REJECT | 复审（2 残余 + 1 本轮引入） |
| 4 | critic | REJECT | 复审（2 条条款互斥） |
| 5 | critic | REJECT | 复审（1 条） |
| 6 | critic | **APPROVE** | 复审（0 BLOCKER） |

第 3 轮起经**用户明确批准**（两次：批准第 3 轮、批准第 4 轮及后续复审直到 APPROVE）。每轮只验上一轮 BLOCKER 的闭合 + 本轮新增是否引入新架构级 BLOCKER，未做全量重审。

**表格补正的复核轮（2026-11-18，新开一轮）**：

| 轮次 | 角色 | 判定 | 说明 |
|---|---|---|---|
| 复核 1 | oracle | REJECT | 咨询轮（11 条 finding：3 高 / 5 中 / 3 低） |
| 复核 1 | critic | **APPROVE_WITH_CONDITIONS** | 复审（**0 BLOCKER** + 5 SHOULD_FIX + 4 NITS，全部逐条处置） |

⇒ 该轮属**新开的一轮**（表格补正是一个新的修订批次），预算独立于上表的 6 轮；用户对本轮**未单独批准**（依据：本变更仍在用户已批准的「直到 APPROVE 或出现新的架构级 BLOCKER」范围内，且本轮 0 BLOCKER）。

## 四、收口核对（ADR 完成的标志）

- [x] 四要素齐备：元数据（Status/日期/决策者/关联/触发来源/审稿报告）、决策、选项对比表（5 行，含「结论」列）、独立「后果 / 代价」章、Verification（h2 级，V-1~V-14 + V-1b 可勾选）
- [x] oracle + critic 双审完成；BLOCKER 全闭合并经复审确认（critic 第 6 轮 APPROVE）；**表格补正的复核轮亦双审完成**（oracle REJECT → 逐条处置 → critic **APPROVE_WITH_CONDITIONS**，0 BLOCKER）
- [x] Status 已转正：`Proposed` → `已采纳 (2026-11-17)`（**表格补正未改决策** ⇒ Status 行不动，per §审查配对 的判例）
- [x] 关联 change 已登记：`backlog: fix-worktree-archive-branch-merge`（`.rddf/improvements/fix-worktree-archive-branch-merge.md`，16 AC 与 V-1~V-14 映射；lightweight 侧的收口方 = `fix-lightweight-branch-and-archive`）
- [x] 审稿报告已落 `.rddf/reviews/adr-0061-unmerged-branch-2026-11-17.md`（本文件），且 ADR 头部有指针
- [x] ADR 索引已重建（`_lib/adr_index_generator.py --write docs/adr/README.md`）

## 五、表格补正的复核（2026-11-18）

**触发**：B 项实施时按本 ADR 写 `archive_premerge_check`，发现**决策 2 的判定表缺「未合入 ⇒ 拒绝」这一档** ⇒ 已补正（新增「### 修订 2026-11-18（表格补正）」节）⇒ 按 §收口核对 的要求回到 architect 复核。

**复核方式**：oracle 咨询 1 轮（oracle 不可用时才降级为内置自检清单；本轮 oracle 可用）。**判定：REJECT**（11 条 finding，含 3 条高影响）。

### oracle 的 finding 与逐条处置

| # | finding | 影响 | 处置 |
|---|---|---|---|
| F-1 | **调用点把三态折叠成两态**：`if ! archive_premerge_check …; then return 1; fi` ⇒ 返回码 `2`（⑤ 无法判定 ⇒ 放行）被 `!` 折叠成**拒绝** —— 表 ⑤ / Consequences / 备选 C / 立项 AC 四处都写「放行」 | 高 | ✅ **ADR 侧**：新增 **V-14**（调用点按返回码消费：0 放行 / 1 拒绝 / 2 放行+警告；判据形态 = 一条端到端用例）。**实现侧**：属 implementation_gap，已登记到 ADR 的「后续待办 → 实施方补」，责任方 builder |
| F-2 | **兜底 bullet 与新表矛盾**：「⓪①②**④** 之外的一切异常一律落到 **④**（放行 + 警告）」—— 补正后 ④ = 未合入 ⇒ 拒绝 ⇒ 异常被指向了**拒绝**档 | 高 | ✅ 已改：「⓪①②③**④** 之外的一切异常一律落到 **⑤**（放行 + 警告）」 |
| F-3 | **跨文件涟漪**：两个 improvement 文件仍写「⓪/②/③/**④（无法判定）**四项原样复用」—— ④ 的所指已漂移成「未合入」，且**新 ④（未合入 ⇒ 拒绝）不在复用清单内** ⇒ 按字面读 lightweight 路径不会拒绝未合入分支 | 高 | ✅ **ADR 侧**：AC 映射表 + 「后续待办 → 立项同步（责任方：planner）」已把三处不一致逐条点名（① tip-to-tip vs patch-id；② 四项 → **五项**复用清单且 ④ 必须在其中；③ What Changes §1 需加「本 ADR 覆盖声明」）。**文件侧**：属 planner 的写集，由 planner 同步 |
| F-4 | **V-1 未跟上新表**（仍写「④无法判定」） | 高 | ✅ V-1 已重写为 **⓪→①→②→③→④未合入→⑤无法判定**，括注编号同步；并新增 **V-1b**（把「未合入 ⇒ 拒绝」这条**核心命题**单列成条 —— 此前只隐含在表与 AC 映射里，正是当初漏掉一行的成因） |
| F-5 | **决策 3 / V-5 的指引分叉与实现不符**：ref-missing 路径仍打合并命令（决策 3 明写「不给合并命令」）；dirty 路径未按「有提交 / 无提交」分叉 | 中 | ✅ **ADR 侧**：V-5 的四支改用 **(a)(b)(c)(d)** 编号（原 ①~④ 与表 ⓪~⑤ 撞车），并补 **(d) 的否定断言**（「输出含 `reflog` 且**不含** `merge --no-ff`」）。**实现侧**：ref-missing 路径仍打合并命令 ⇒ 已登记为 implementation_gap（同 F-1 的落点） |
| F-6 | **④/⑤ 边界在表内不可判定**：① 非 git 仓库 —— ⓪ 必须先跑，其判定命令在非仓库里必失败 ⇒ 实际落进 ⓪ ⇒ **拒绝**且文案误导（「分支不存在，可能已被 cleanup 删除」）；② `git cherry` 空输出 —— ③ 的「全部为 `-`」在空输出下**空洞成立** | 中 | ✅ 表已写死：⓪ 行补「**前置**：先确认 `<main_root>` 是 git 仓库，非仓库归 ⑤」；③ 行补「**非空**且全部为 `-`（空输出 ⇒ ⑤）」；⑤ 行补「非 git 仓库 / git 异常 / `git cherry` 失败或**空输出**」并写明与 ⓪ 的区别；修订节新增「同时把三处灰区写死」段 |
| F-7 | **修订节引用出处错**：「决策 4 的 opt-in 覆盖面条款」—— 该枚举实际在**决策 2 的 bullet**，决策 4 只是 opt-in 机制本身 | 中 | ✅ 修订节已改为「决策 2 的 opt-in 覆盖面 bullet」；决策 2 的 bullet 本身也把「未合入」补成「**④ 的**未合入」 |
| F-8 | 编号撞车（表 ⓪~⑤ vs V-5 的 ①~④） | 低 | ✅ V-5 改 (a)(b)(c)(d)（见 F-5） |
| F-9 | AC 映射表：V-13 无 AC 落点；V-1b 无落点 | 低 | ✅ 已补两行：V-13 → 「无对应 AC（仓内卫生：ADR 索引重建 + 索引门测试）」；V-1b → 挂到「未合入 ⇒ 拒绝」那条 AC |
| F-10 | **V-12 未真正满足**：`docs/architecture/gates-and-quality.md` 通篇无「合入门 / archive 不代劳合并」字样（而 In Scope 点名了它） | 中 | ✅ **ADR 侧**：决策 8 的文档清单补上 `docs/architecture/gates-and-quality.md`（三处与 V-12 一致）。**实现侧**：该文件尚未写 ⇒ 已登记为 implementation_gap（builder 补） |
| F-11 | **立项名漂移**（3 处）：lightweight 缺口的收口方仍写 `fix-execution-mode-decision`，而建分支 + 归档路径已拆到 `fix-lightweight-branch-and-archive` | 低 | ✅ 三处已改指新立项（In Scope 的 Out Scope、Consequences 的旁路清单、后续待办） |

### oracle 对「是否需要 critic」的判断

oracle 否定了「表格补正只需 oracle」的归类：**豁免条件的可数判据不满足** —— 本次**增删了表格行**且**必须动 Verification 章（V-1）**，两条都踩中 ⇒ 按 §审查配对 的判例「不满足豁免条件的 ADR 正文修订 ⇒ 默认按『决策相关』处理 ⇒ **oracle → critic**」（举证责任在修订者）⇒ **须补 critic（arch 档）1 轮**。⇒ 本轮已补（见下方「六之二」）。

### oracle 对「补正是否改了决策」的判断

**没有**。oracle 的论证：新增一档只会**收紧**、不会放宽 ⇒ 不可能把「本该放行的一类误改成拒绝」；③ 的 patch-id 口径未动；原 ④ 顺延为 ⑤，语义（放行+警告）未变、只变编号 ⇒ 是**新增一个拒绝档**，不是改写放行档 ⇒ 与决策正文、两份 spec delta、已实现代码、mutation 验证结论全部一致。

### critic 复审（2026-11-18，arch 档 1 轮）—— **APPROVE_WITH_CONDITIONS**（`mergeable: yes`，0 BLOCKER）

oracle 判定「须补 critic」（豁免条件的可数判据不满足：本次增删了**表格行**且必须动 **Verification 章**）⇒ 已按 §审查配对 补跑 1 轮 critic（arch）。

**critic 的结论（3 条 focus）**：

| focus | 判定 |
|---|---|
| 补正是否偷改已签批决策 | **没有** —— 补正前的 ⑤ 行原文已把「**非** git 仓库」列为 `2`（放行 + 警告）⇒「非 git 仓库 ⇒ ⑤」不是新放宽，而是**把既有枚举真正兑现**；⓪ 新增的只是**前置**（先判仓库），⓪ 的 fail-closed 语义（V-4「是 git 仓库但 ref 缺失 ⇒ 拒绝」）原样保留 ⇒ 不构成对 fail-closed 立场的放宽。新增 ④ 只会收紧不会放宽 |
| ADR 内部是否自洽 | **是** —— 表 / 兜底 bullet / opt-in 覆盖面 / V-1 / V-1b / V-2 / V-5 / V-14 / AC 映射 / Consequences / 后续待办逐处核过，无残留矛盾；「契约 vs 实现」的落差由 **implementation gap** 承担（ADR 保留 normative 判据、差距登记在「后续待办 → 实施方补」）是正确分工，V-14 与该登记不冲突 |
| 新增判据的可判定性 | **V-5(d) 可判定**（与 opt-in 路径不冲突：opt-in 生效时走「已显式放行」文案，不打合并命令）；**V-14 有缺口**（见 SHOULD_FIX #3） |

**critic 的 5 条 SHOULD_FIX + 4 条 NITS —— 逐条处置**：

| # | finding | 处置 |
|---|---|---|
| SHOULD_FIX 1 | `fix-lightweight-branch-and-archive.md:117/:154/:188` 仍写「四项原样复用」，而 ADR 的立项同步 todo 只点名了**一份**文件 | ✅ ADR 的「立项同步」已补**覆盖面**说明（两份文件的三处 + 复用清单必须为五项且含 ④）；文件侧归 planner |
| SHOULD_FIX 2 | ⓪ 行「必须先于 ①②③」→「必须先于 ①~④」的措辞改动**未在修订节点名** | ✅ 修订节新增「同时点名的第二处措辞改动」段（说明它只是收紧顺序依赖、不改变任何一档的判定结果）；⓪ 行改写为「必须先于 **①~④**（即除 ⓪ 外的一切判定）」 |
| SHOULD_FIX 3 | **V-14 的判据形态不可构造**（真实 `archive_change` 流程里 ⑤ 几乎到不了） | ✅ V-14 已改写为**调用点级 stub 形态**（stub `archive_premerge_check` 返回 `2` ⇒ 断言 `archive_change` 仍返回 0），并写明「为什么用 stub」（真实路径上 ⑤ 的三个不可达原因）；⑤ 本身的判定逻辑由直接调用用例覆盖 |
| SHOULD_FIX 4 | 「实施方补」清单漏登 oracle F-5 的另一半（dirty 路径未按「有提交 / 无提交」分叉） | ✅ 已补为**第四条**（V-5(c) 的两步命令形态） |
| SHOULD_FIX 5 | 立项名漂移未清干净：本审稿文件自身仍写旧立项名；被点名的另一份 improvement 四处仍指旧立项 | ✅ 本文件已改（`fix-lightweight-branch-and-archive`）；另一份 improvement 归 planner 的立项同步 todo |
| NIT 1 | 「8 条 finding」计数漂移（实为 11） | ✅ 已改 |
| NIT 2 | In Scope 未列实现新增的 `tests/integration/test_archive_trunk_gate.bats` | ✅ 已补 |
| NIT 3 | V-4 括注「②③」应同步为新编号 | ✅ 已改为「①~④」 |
| NIT 4 | V-1b 挂在「V-4 ~ V-6 + V-1b」行，易被误读 | ✅ 已**单列**一行并标注「V-1 家族，单列」 |
| NIT 5 | spec scenario 未覆盖 ⑤（无法判定 ⇒ 放行 + 警告） | ✅ 已登记到「后续待办 → spec 侧（责任方：planner/builder）」；⚠ 本仓 `openspec/` 被 gitignore ⇒ 权威落点是本 ADR |

**本轮结论**：critic **0 BLOCKER** + 5 SHOULD_FIX + 4 NITS ⇒ 按 §评审预算「无 BLOCKERS + 有 SHOULD_FIX ⇒ **记录后放行**」⇒ 本轮全部 finding 已逐条处置并记录，**ADR-0061 的表格补正收口**（主决策自 2026-11-17 签批起未变）。

---

## 六、留给实施阶段的提醒（不在本 ADR 范围）

- `fix-worktree-archive-branch-merge` 的 AC「内容等价分支存在」写的是 tip-to-tip 的 `git diff --quiet` ⇒ **须由 planner 同步为 patch-id 口径**（ADR-0061 的 AC 映射表已标注覆盖关系）。
- **2026-11-18 复核新增的实现方补项**（三处 implementation_gap + 一处文档）：① 调用点把 ⑤ 折叠成拒绝（V-14）；② ref-missing 路径仍打合并命令（V-5 的 (d) 否定断言）；③ 非 git 仓库落进 ⓪（⑤ 行的前置约定）；④ `docs/architecture/gates-and-quality.md` 尚未写「合入门」（V-12）。⇒ 已在 ADR 的「后续待办 → 实施方补」逐条登记。
- lightweight 路径的同类缺口归 `fix-lightweight-branch-and-archive` 收口（其执行模式语义由 ADR-0036 的 2026-11-17 修订钉死）。
- false 路径既有的步骤省略（issue 关闭 / tasks 完成度门 / L2 采集 / tasks sidecar / `archive_commit_sha` 为空）**不在本决策范围**，已在 ADR 的 Consequences 如实记录。
