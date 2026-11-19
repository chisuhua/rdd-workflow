# ADR-0063 跨仓治理面对齐 — 审稿报告

- **对象**: opencode 仓（`~/.config/opencode`）治理面 5 处改动
- **日期**: 2026-11-19
- **审稿链**: oracle（治理面判定）→ critic（治理面 + arch 档）
- **review_profile**: `arch`（治理面）
- **上游依据**: rdd-workflow 仓 `docs/adr/ADR-0063-retire-guide-orchestrator.md`（已采纳）

## 意图检查点（oracle 调用前）

| 项 | 处置 |
|---|---|
| 意图是否由用户给出 | 是。用户选「路径 1（切 architect）」，明确要求实施跨仓 T7.1 + T7.2 |
| 是否调 metis | 未调。意图明确（ADR-0063 Decision 5 已规定「治理面先行、本仓 archive 后置」），歧义已在交接单中枚举 |
| 是否存在 ≥2 种合理解读 | 否。D7 的职责划分一字不动是范围冻结项，非歧义 |

## 改动清单（5 处）

| # | 文件 | 改动 |
|---|---|---|
| 1 | `scripts/rdd-skills.sh` | `RDD_SKILLS_BUILTIN` 删 `guide` 一行；顶部注释补「退役 skill 也须手工移除」提醒 |
| 2 | `.rddf/state/adr-front-agent-redesign.md` | D7 段末句改为「原结论（`guide` skill 予以保留）已作废」+ 归档去向 + 职责划分不变 + front 不调用该 CLI 的消歧说明；元数据头新增「被取代条款（2026-11-19）」第 ⑤ 条 |
| 3 | `prompts/build.md` | 角色矩阵 `general` 行：可选增强列 `guide` → `—`（无专属 skill）+ `rddf guide` CLI 指引 |
| 4 | `docs/MULTI-AGENT-DESIGN.md` | 角色→可选增强映射表 `\| general \| guide \|` → 标注 CLI 入口与归档事实 |
| 5 | `.rddf/improvements/front-agent-redesign.md` | 「范围外（本次不做）」段的「skill 保留」加作废标注（追加式，原文保留） |

## oracle（第 1 轮）

**判定原文**：`治理面判定: PASS-WITH-NOTES`

| # | finding | 处置 |
|---|---|---|
| 1 | **高影响**：`prompts/build.md:412` 是 agent 直读点位，`general` 行仍写 `` `guide`（推荐下一 skill）`` —— general 角色会尝试 `skill_use("guide")` 失败 | 已改（改动 3） |
| 2 | 中：`docs/MULTI-AGENT-DESIGN.md:318` 与 `.rddf/improvements/front-agent-redesign.md:240` 同样残留 | 已改（改动 4、5） |
| 3 | 低：D7 注末补半句「front 侧不调用该 CLI」消歧 | 已采纳 |
| 4 | 低：`rdd-skills.sh` 注释补「退役 skill 须手工移除」提醒 | 已采纳 |
| 5 | 低（建议）：V-9 探针将来改上下文感知 | 记录为 backlog（探针在 rdd-workflow 仓，属那边工件；本次以措辞规避） |

## critic（第 1 轮）

**结论**：`APPROVE_WITH_CONDITIONS`，`mergeable: yes`，`scope_exceeded: no`，**BLOCKER 0**

| # | finding | 处置 |
|---|---|---|
| SHOULD_FIX-1 | `prompts/build.md:412`「内置流程」列写入了 `rddf guide` CLI，**违背该列列头契约**（「永远可用，不依赖 rdd-workflow」）与不变式 1 | 已闭合：从内置流程列删去该短语（恢复原样），只保留在「可选增强（装了 + 前置条件满足时）」列 —— 该列语义与 CLI 的依赖条件恰好匹配 |
| SHOULD_FIX-2 | D7 修订只加在正文，未在元数据头「被取代条款」登记 —— 按本文件自身惯例（2026-11-09 已有 ①~④ 四条先例）应在头部登记 | 已闭合：新增「被取代条款（2026-11-19）」第 ⑤ 条 |
| NIT-1 | D7 「推荐能力由 `rddf guide` CLI 承担」的主语边界依赖下一段才明确 | 已闭合：主语改为「推荐能力在**工程 session / 纯命令行场景**由 `rddf guide` CLI 承担」，并把「front 与该 CLI 是两条并行的推荐路径」写进补充说明 |
| NIT-2 | `MULTI-AGENT-DESIGN.md` 与 `build.md` 详略不同但不矛盾 | 无需统一（保持） |

## 验证

| 项 | 命令 | 结果 |
|---|---|---|
| T7.1 判据 | `sed -n '/^RDD_SKILLS_BUILTIN=(/,/^)/p' scripts/rdd-skills.sh \| grep -cE '^\s+guide\s*$'` | **0** |
| T7.1 行为 | `./scripts/rdd-skills.sh --json` | `available[]` 28 项，**不含 `guide`**；JSON 合法 |
| T7.2 判据 | `grep -c 'guide. skill 不删' .rddf/state/adr-front-agent-redesign.md` | **0** |
| 保留项 | `grep -c 'front 吸收'` / `grep -c '新鲜度标注（强制）'` | **1 / 1**（D7 职责划分与新鲜度标注未动） |
| 元数据头 | `grep -c '被取代条款（2026-11-19）'` | **1** |
| 语法 | `bash -n scripts/rdd-skills.sh` | OK |
| 测试 | `bun test tests/` | **931 pass / 1 fail** |

### 关于那 1 个失败

`tests/config-guards.test.ts` 的「agent 模型清单：配置（真源）与两份文档一致」断言失败 —— `MULTI-AGENT-DESIGN.md` 的 metis 行写 `commandcode/deepseek/deepseek-v4.1-flash`，守卫期望 `opencode-go/deepseek-v4.1-flash`。

经 `git stash` 对照**确认为改动前既有失败**（stash 本次全部 5 处改动后，单独跑 `config-guards.test.ts` 仍 118 pass / 1 fail，且失败信息逐字相同）。与本次改动无关，属 opencode 仓的既存漂移，不在本次 scope。

## 遗留（已登记，不阻断）

1. `opencode` 仓的 `cli.json` 与 `opencode.jsonc.opencode-go` 有未提交改动 —— 非本次产生（本次会话开始前即存在），未纳入审查范围。
2. V-9 探针口径偏粗（全文 grep，无法区分「作为当前结论」与「被引述并作废」）—— 本次以措辞规避（把引述改成「予以保留」/「保留 `guide` skill」），探针本身改进留作 rdd-workflow 仓的后续工件。
