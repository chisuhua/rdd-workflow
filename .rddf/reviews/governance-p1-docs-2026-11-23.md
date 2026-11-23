# 治理面 P1 文档漂移修正 —— 审稿报告（2026-11-23）

> **本文件是 `~/.config/opencode`（治理面仓）的改动审稿记录**，由 `architect` 角色在收口时
> 从 oracle / critic 输出誊写。**落点说明**：审稿报告的既有惯例是
> `~/.config/opencode/.rddf/reviews/<topic>.md`，但该路径**不在** `architect.allow`
> （= `.rddf/config/arch-docs.json` · `.rddf/config/governance-paths.json` · `.rddf/reviews`，
> 相对 **cwd** 解析；cwd 是本仓根目录）内 ⇒ 本报告落在
> **本仓的 `.rddf/reviews/`**（跨仓审计台账的同一落点）。**这是已知偏差，不是惯例变更。**

## 元数据

| 项 | 值 |
|---|---|
| 主题 | 治理面 P1 文档漂移（计数 / 委派矩阵 / 角色表写集投影 / 悬空引用 / 陈数） |
| 日期 | 2026-11-23 |
| 角色 | `architect`（用户口令切自 `builder`） |
| 改动文件 | `~/.config/opencode/prompts/build.md` · `docs/MULTI-AGENT-DESIGN.md` · `docs/SUBAGENT-ORCHESTRATION.md`（3 份 / +56 −22，**纯文档**） |
| 审查链 | **oracle（治理面审查域）→ critic（`review_profile: arch`）** |
| 关联台账 | `.rddf/reviews/docs-alignment-debt-audit-2026-11-23.md` §三（#11–20） |
| 关联 ADR | ADR-0016/0018/0019/0025/0031/0043/0048（本仓）· `ADR-governance-paths-ownership` / `ADR-front-knowledge-capability` / `ADR-plan-multi-session-collaboration`（治理面仓） |

## 一、意图检查点处置（oracle 前）

按 `prompts/build.md`「oracle 调用前的意图检查点」：

| 步 | 处置 |
|---|---|
| 意图是否可判定 | **是** —— 用户选定「治理面 P1」，范围由台账 §三 逐条给定（#11–20），边界 = 不改 `lib/**` / `plugins/**` / `opencode.jsonc` / 守卫测试 / ADR |
| 是否存在 ≥2 种合理解读 | **是**（矩阵 `plan-worker` 列填法、悬空引用修法、architect 行补什么粒度为 3 处主要歧义） |
| 处置 | **先单独调 `metis`**（不与 oracle 并行），其六节输出作材料进 oracle 输入 |
| 是否有「只有用户知道」的隐藏意图 | **否** —— 范围由用户选定的选项描述 + 台账给定 |

## 二、oracle（治理面审查域）

**判定：`治理面判定: PASS-WITH-NOTES`**

### 采纳的意见

| # | oracle 意见 | 采纳情况 |
|---|---|---|
| 1 | 矩阵 `build → plan-worker` 填 **✅**（**不是** metis 建议的 ❌）—— 理由：矩阵自称「只回答允许调谁」；`build → general = ✅` 是纯权限填充；`plan → context-builder = ❌` 是**矩阵填充分裂的受害者**，不是「按流程填」的先例；填 ❌ 会与守卫 AC4 直接矛盾 | ✅ 采纳（与 metis 相反，理由成立） |
| 2 | 角色表**只补 architect / verifier 两行**，不做六行统一改路径清单（仓内原则「散文不复述机读值」，`:461-463`） | ⚠️ **部分采纳**：最终连两行的表内改动也撤回（见§四「执行约束」），改为**表尾整块投影** |
| 3 | `:554` 语序：**流程层在前**、机器层降级为尾注并立即闭环（防首读成「可以改」） | ✅ 采纳 |
| 4 | SO `:174` 用**双锚点**，不做「v2.20+ 全是治理面改动」的未核实断言 | ✅ 采纳 |
| 5 | SO `:172` **删裸计数**（裸数字必然再漂），不是换成新数字 | ✅ 采纳 |
| 6 | **不动** build.md 治理面作用域表的机制面两行（`role-policy.ts` 注释引用着） | ✅ 遵守 |
| 7 | **不归一化** `plan → context-builder` 格（范围外，记 follow-up） | ✅ 遵守 |
| 8 | follow-up：五角色写集**机读块化**（`delegate-core.ts` 渲染函数 + 守卫精确比对） | ✅ 已记入 §六 |

### 未预见到的约束（执行时才被 guard 抓到）

oracle 未预见：`prompts/build.md` 的角色列表表被
`.rddf/rollback/governance-paths-config.json` 的 `edits[13].find` **整表 pin**
（表头 → `general` 行，2914 字符）⇒ 改任何单元格都判漂移；而 `.rddf/rollback/**`
**不在 `architect.allow`** 内。**故 oracle 意见 #2 的表内改法无法执行**。

## 三、critic（`review_profile: arch`）

**结论：APPROVE_WITH_CONDITIONS** · `mergeable: yes` · `scope_exceeded: true`（仅 SF-3 与两条清单外矛盾）
· **0 BLOCKER**

### SHOULD_FIX 处置

| # | finding | scope_exceeded | 处置 |
|---|---|---|---|
| SF-1 | MAD `:101` §2.2 标题「Primary Agents（**3 个**…）」 vs 本轮新增的口径「**4 primary**」—— 同一文档相邻两节两个数字 | false | ✅ **已修**：标题改「3 个直接交互 + `title`(hidden)，共 4 个 primary」+ 加一段与 §2 口径的关系说明 |
| SF-2 | 矩阵填法**双轨**：`plan → context-builder = ❌`（按流程填）vs 本轮 `build → plan-worker = ✅`（按权限填）—— 同型情形相反裁决，两条旁注并排会放大困惑 | false | **记 follow-up**（归一化该格属范围外）。critic 明示「靠旁注仍可判断，不阻断」 |
| SF-3 | `.rddf/rollback/governance-paths-config.json` 的 `edits[13].find` pin 住整表 ⇒ 任何单元格修改都触发漂移；范围远超机制特有片段 | **true** | **记 backlog**（清单 `find` 应窄化到机制锚点，散文留给正常编辑） |

### NITS 处置

| # | finding | 处置 |
|---|---|---|
| NIT-1 | 表尾「机读块目前只有 `verifier` 有一块」**字面不成立**（上方 `:482-487` 就有 `capability:build` 块） | ✅ **已修**：改为「**写集**机读块目前只有 `verifier` 有一块（能力面机读块 `capability:build` 在上方，两者不是同一种块）」 |
| NIT-2 | SO `:174` 「当前最新 v2.67」是时点值 | ✅ **已修**：改「本行撰写时最新为 v2.67 —— **2026-11-23 快照**，后续版本以该文件为准」 |
| NIT-3 | MAD 的 4+8 拆分明示出现**三处**（§1.1 / §2 口径 / §2.3 口径） | ✅ **已修**：§2.3 口径改为「与 §2 标题口径同源，**枚举只在 §1.1 列一处**」；§2 口径已指回 §1.1 |
| NIT-4 | 表尾投影与 `role-class-write-set:verifier` 机读块对 verifier 是**两份无守卫副本** | 记 follow-up（与 SF-3 的机读块化同一批） |

### critic 的 focus 逐条结论（要点）

- **A（矩阵填法）**：`build → plan-worker = ✅` **正确**（与自声明 + 守卫 AC4 一致）；
  `plan → plan-worker` **不应升 ✅✅**（`plan.md:209` 明言只在「任务大到单会话放不下时」才派，
  不是优先出口）；新旁注与 context-builder 旁注**同判据**、不构成第二套判据；
  双轨会放大困惑但**不阻断**。
- **B（表尾投影）**：**可接受** —— 表尾已声明表内散文「不承担写集判据」并给逐字投影 + 真源指针，
  信息已补齐；**不构成第二套判据**；v3 编号注记属「**修复中的临时标注**」而非合法化。
- **C（口径 / 未决）**：MAD `:49` 的口径**够用**（点名符号链接目标 + 「换目标需同步」）；
  SO `:174` 的 v2.67 已核实为真但确为时点值（→ NIT-2）；SO `:172` 删裸计数是**消除漂移非丢信息**；
  MAD 三处口径重复是真实漂移面（→ NIT-3）。

## 四、改动清单与执行约束

| 文件 | 改动 |
|---|---|
| `docs/MULTI-AGENT-DESIGN.md` | `:49` 3/12 → **5/13** + 口径；`:62` 11 → **12** + 口径；`:101` §2.2 标题（3 → 3+title / 共 4 primary）+ 关系说明；`:158` 7 → **8** + 口径（改指针）；`:391` 11 → **12** + 补 `plan-worker`；§3.1 矩阵**新增 `plan-worker` 列**（11 列）+ 各行填值 + 旁注 |
| `prompts/build.md` | `:411` `§4.2` → 「工件归属规则」；表**之后**新增**表尾声明**（6 角色机器层写集逐字投影 + 「禁止列的流程约束机器层不拦」+ `§4.2`/`§4.4` 映射说明 + 写集机读块缺口）；`:554` 后新增「机器层语义」尾注 |
| `docs/SUBAGENT-ORCHESTRATION.md` | `:1` 日期 → 「最后更新：2026-11-23」；`:30` 悬空「链路分档」→「模型选择策略」（**不带编号**）；`:172` 删裸计数；`:174` 双锚点 + 日期锚 |

### 执行约束（表格 pin）与由此产生的未闭环项

`.rddf/rollback/governance-paths-config.json::edits[13].find` pin 住角色列表**整表**，
而 `.rddf/rollback/**` 不在 `architect.allow` ⇒ **表内单元格一个字都不能改**。因此：

| # | 未闭环项 | 补偿 |
|---|---|---|
| 1 | architect 行「允许」列**仍不提** `.rddf/reviews` | 表尾投影列出 `architect.allow` 全三项 |
| 2 | verifier 行「允许」列**仍不提** `.rddf/state/verifier` | 同上 |
| 3 | `:455` 的 `§4.4` **仍留在表内** | 表尾声明给出映射（「`§4.4` = 本表 `builder` 行」） |

## 五、验证

| 项 | 结果 |
|---|---|
| `bun test tests/`（治理面仓，32 文件 / 1134 测试） | **1133 pass / 1 skip / 0 fail** |
| 其中 `rollback-manifests.test.ts`「在场性 + 可执行性」 | ✅（本轮两次抓到真漂移后修回） |
| 其中 `config-guards.test.ts`「汇总文档不得用编号式章节引用」 | ✅（本轮曾因写 `（§5.2）` 红了一次，已去掉） |
| 矩阵列数一致性（表头 12 格 = 1 标签 + 11 数据列，10 行全 12 格） | ✅ |
| 角色列表表列数一致性（8 行全 4 格） | ✅ |
| `grep '链路分档' docs/ prompts/` | **0 命中** |
| 计数复核（`opencode.jsonc.opencode-go`） | providers **5** / models **13** / agents **12** / subagent **8** ✅ |

## 六、follow-up —— ✅ 已全部立项（2026-11-23）

落点：`~/.config/opencode/.rddf/improvements/`（4 份 5 段草稿，opencode 仓 commit `5b3b051`）。

| 原 follow-up | 立项文件 | 优先 | 依赖 |
|---|---|---|---|
| 2. 回滚清单 `find` 窄化（SF-3 根因） | `rollback-manifest-find-narrowing.md` | **P1** | — （C 的硬前置） |
| 1. 五角色写集机读块化（NIT-4 同批） | `role-write-set-machine-block.md` | P2 | 依赖上一行 |
| 3. 矩阵填法归一化（SF-2） | `delegation-matrix-fill-semantics.md` | P2 | 依赖「librarian」那条 |
| 4. 清单外同型矛盾 —— **`librarian` 三向互斥**（最严重） | `librarian-delegate-contradiction.md` | **P1** | — |
| 4. 清单外同型矛盾 —— ASCII 图「general 不能被任何 agent 调」 | 并入 `delegation-matrix-fill-semantics.md` | P2 | — |

**metis 审**：4 份同批 1 轮（2026-11-23）。据其建议的主要修订见各草稿头部的
`> planner 审查：**metis 1 轮**` 行（要点：AC 改闭集字面 · B 的普查剥离出 P1 ·
C 删「汇总块」退让并缩范围 · D 的落点写死 `tests/` + 位置解析闭集化）。

⇒ **本节原列的 4 条 follow-up 已全部有归属，无静默遗留。**
