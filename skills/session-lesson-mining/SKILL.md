---
name: session-lesson-mining
description: |
  从**真实会话历史**里挖教训，并把它们固化成 `rdd-workflow-e2e` 的机械判据。

  Invoke when BOTH:
    1. 需要复盘一次（或一批）真实会话 —— 出过错、或要防止同类错误重犯
    2. 产物落点是**可机判的测试**（bats 用例），不是"总结感想"

  Default: 只产出「候选教训 → 判据 → 判别力证据」；不改产品代码、不改既有判据口径。

  Boundary ownership: see role.boundaries.owns / not_owns.
license: MIT
compatibility: Requires python3 (stdlib only), sqlite3, git, bats
metadata:
  version: "0.1"
  author: sisyphus
  evolved-from: "2026-11-19 收口会话：7 类错误全部发生在记录/判据层，遂把'从会话里挖教训→立判据→用历史快照证明判别力'固化成流程"
  user-invocable: true
---

# 会话教训挖掘 → e2e 判据

## 用途

一次真实会话里，**模型犯的错通常不是"想错了"，而是"记录与判据不自洽"**：AC 里写"逐字"
但字面量不存在、勾了 AC 却没有任何证据指针、勘误只说"此处有误"、观察报告里 pending 与
已确认并存、"门槛已到"没有任何取数指针、用混装 commit 当归因证据……

这些东西**能被机械判据抓住**，但前提是先把它们从会话里**逐条挖出来**。本 skill 就是这条流水线：

```
会话库(sqlite) → 归一化 JSONL → 候选清单 → 候选 → 判据(bats) → 判别力反证 → 接线
```

## 先读：五条硬约束

| # | 约束 | 为什么 |
|---|---|---|
| 1 | **候选 ≠ 结论** | 检测器只认"现象"（命令失败 / 测试红 / 用户纠正）；"这暴露了什么教训"必须人工/AI 复核后判定 |
| 2 | **判据必须在出错当时的状态上变红** | 只在当前 HEAD 绿的判据是"事后诸葛"；用 `git archive` 导出修复前的快照跑一遍，必须红 |
| 3 | **每条判据三件套：反例（必报）+ 正例（不误报）+ 真实仓（干净）** | 缺反例 = 判据恒绿；缺正例 = 到处假红 |
| 4 | **`skip` ≠ `pass`** | 取不到证就明确 skip 并写原因，不许把"没跑"记成"通过" |
| 5 | **判据不得自我满足** | 守卫自己的夹具/文档里含有被判的字面量 ⇒ 自己满足自己；扫描根为空 ⇒ 全判据空转（假绿） |

## 流程

### P0 定位会话

```bash
S=~/.agents/skills/rdd-workflow/skills/session-lesson-mining/scripts
python3 $S/session_export.py --list | head -20          # id / 时间 / 轮数 / 目录 / 标题
```

按 **目录 + 时间窗 + 标题**选，不要"最近一个"就上 —— 复盘对象是**出过错的那次**。

### P1 导出为归一化 JSONL

```bash
python3 $S/session_export.py --since 2026-11-19 --max-text 0 --out /tmp/opencode/s.jsonl
# 或指定会话：--session ses_xxx（可重复）
```

- **`--max-text 0`（不截断）用于挖掘**：失败行常出现在长输出的中段；截断会漏。
- 默认 `--max-text 2000` 保留"头 + 尾"，适合给人看。
- 导出的 JSONL 含绝对路径与命令 ⇒ 写到 `/tmp/opencode/`，**不要入库**。

### P2 挖候选

```bash
python3 $S/mine_lessons.py --in /tmp/opencode/s.jsonl --out /tmp/opencode/lessons.md
# 只看某类：--detector self_correction --detector guard_selfhit
# 只看高频：--min-count 2 --top 20
```

输出按 `(检测器, 归一化证据)` **聚合**（不聚合时一次 red-green 循环就能灌进几百条同类）。

检测器 → 常见教训类型：

| 检测器 | 现象 | 通常对应什么教训 |
|---|---|---|
| `tool_error` | 工具 error / 退出码非 0 | 路径假设、权限假设、命令形态 |
| `failure_signature` | 输出含 `command not found` / `No such file` / `invalid format character` / `Traceback` … | 脚本/夹具本身的 bug（尤其"判据自己的 bug"） |
| `test_failure` | `not ok` / `FAILED` / `AssertionError` / `N fail` | 实现缺口 或 **判据过宽/过窄** |
| `retry_loop` | 同一命令重复 ≥3 次 | "改了没生效"（patch 没打上 / 路径不对 / 判据假绿） |
| `user_correction` | 用户纠正语 | **最有价值**：说明前面的结论站不住 |
| `self_correction` | assistant 自述"我错了/我漏了/又踩了" | 已自知的错误 ⇒ 直接可转判据 |
| `guard_selfhit` | 自匹配 / 空转 / 假绿 / 被求值 / 误报 | 判据自身的缺陷 ⇒ 与主教训同型 |

### P3 候选 → 判据（**复核在这里**）

对每条候选问四问（答不上来就丢弃，不许硬凑）：

1. **可机械判定吗？** 判据要能表达成"扫描产物 + 正则/结构断言"。表达不了 ⇒ 记为**人工纪律**，不进测试。
2. **反例来自真实会话吗？** 反例必须能引用真实片段（会话/文件/提交）。**不许编**。
3. **有正例吗？** 描述同一概念的**正确写法**必须不被报（否则判据会咬正常文档）。
4. **触发面够窄吗？** 例如"含 `未改` + 路径"还要**同时**含提交语境；否则性质句会被误判。

判据草图（bats，三态）：

```bash
@test "CN 反例：<坏形态> ⇒ 必须报违规" { ... [ -n "$out" ] || fail }
@test "CN 正例：<好形态> ⇒ 不报"      { ... [ -z "$out" ] || fail }
@test "CN 真实仓：<当前仓> 干净"       { ... [ -z "$out" ] || fail }
```

**判据写成纯函数**（`cn_xxx() { local root="$1"; ... }`），这样反例/正例可以喂假树，真实仓喂真树。

### P4 判别力反证（本 skill 的核心，不许省）

```bash
# 1) 找到"出错当时"的提交（修复前）
git -C <repo> log --oneline -20

# 2) 导出快照（不碰工作树）
rm -rf /tmp/opencode/prefix && mkdir -p /tmp/opencode/prefix
git -C <repo> archive <pre-fix-sha> | tar -x -C /tmp/opencode/prefix

# 3) 用同一套判据跑快照：必须红，并应点名具体文件/行
TARGET_REPO=/tmp/opencode/prefix EVIDENCE_EPOCH=1970-01-01 bats tests/integration/<new>.bats
```

- **红要红得准**：只报"有违规"不够，要能指出是哪个文件哪条断言 —— 否则分不清是判据有效还是到处乱咬。
- **快照红了、当前仓绿** ⇒ 判据有判别力。
- 某些类别的错误形态发生在会话**之后**（无快照）⇒ 用反例证明判别力，并在报告里**如实写"无快照回归"**。

### P5 接线与记录

- e2e 侧：把用例并入 `rdd-workflow-e2e/tests/integration/`，跑**全仓** `bats -r tests/`（不许只看新文件）。
- 如果同类判据也进本仓提交门（`bun test tests/`），**只做薄包装**（照 `tests/arch-docs-scope.test.ts` 的先例），避免双份实现漂移。
- 报告落 `.rddf/reviews/<topic>-session-lessons.md`，必含：
  1. 判据 ↔ 真实事故对照表（每条给会话定位或文件行）
  2. **判别力证据**（快照 SHA + 红在哪几条 + 当前仓绿）
  3. 写判据时**自己又犯的错**（几乎必然有，如实记 —— 它们与主教训同型）
  4. 已知边界（判据覆盖不到什么，为什么）
- 历史记述不回改：已归档的 proposal/报告里的旧数字**只追加勘误**（权威源 + 原文位置）。

## 验收清单

- [ ] 每条判据都有反例（必报）+ 正例（不误报）+ 真实仓（干净）
- [ ] 判别力反证跑过，快照上**点名**报红；当前仓绿
- [ ] 无快照回归的类别已在报告里写明
- [ ] `--selftest`/反例用例是真跑，不是 `skip`
- [ ] 判据不自我匹配（守卫自身文件被排除 / 扫描根非空）
- [ ] 全仓测试跑过（不只新文件），失败数为 0
- [ ] 报告含"写判据时自己犯的错"

## 已知边界

1. **只覆盖产物层**：会话里"agent 是否真的会这样做"要真实模型 + 额度；本 skill 不跑模型。
2. **推理可能被截断**：自述式教训常在 `reasoning` 里，导出默认包含；但模型未写出的判断挖不到。
3. **文本启发式**：检测器靠正则，会漏（换一种说法）也会多报（引用了错误原文）。**多报由 P3 人工收敛**。
4. **会话库 schema 会变**：脚本按 `session_message`（V2）/`message`+`part`（V1）探测；新增表结构需同步。
5. **不可用于"追责"**：候选清单是**工程输入**，不是对人或模型的评价。
