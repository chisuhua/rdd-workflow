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

## 四、收口核对（ADR 完成的标志）

- [x] 四要素齐备：元数据（Status/日期/决策者/关联/触发来源/审稿报告）、决策、选项对比表（5 行，含「结论」列）、独立「后果 / 代价」章、Verification（h2 级，V-1~V-13 可勾选）
- [x] oracle + critic 双审完成；BLOCKER 全闭合并经复审确认（critic 第 6 轮 APPROVE）
- [x] Status 已转正：`Proposed` → `已采纳 (2026-11-17)`
- [x] 关联 change 已登记：`backlog: fix-worktree-archive-branch-merge`（`.rddf/improvements/fix-worktree-archive-branch-merge.md`，14 AC 与 V-1~V-13 映射）
- [x] 审稿报告已落 `.rddf/reviews/adr-0061-unmerged-branch-2026-11-17.md`（本文件），且 ADR 头部有指针
- [x] ADR 索引已重建（`_lib/adr_index_generator.py --write docs/adr/README.md`）

## 五、留给实施阶段的提醒（不在本 ADR 范围）

- `fix-worktree-archive-branch-merge` 的 AC「内容等价分支存在」写的是 tip-to-tip 的 `git diff --quiet` ⇒ **须由 planner 同步为 patch-id 口径**（ADR-0061 的 AC 映射表已标注覆盖关系）。
- lightweight 路径的同类缺口归 `fix-execution-mode-decision` 收口（其执行模式语义由 ADR-0036 的 2026-11-17 修订钉死）。
- false 路径既有的步骤省略（issue 关闭 / tasks 完成度门 / L2 采集 / tasks sidecar / `archive_commit_sha` 为空）**不在本决策范围**，已在 ADR 的 Consequences 如实记录。
