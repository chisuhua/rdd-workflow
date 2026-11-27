---
优先级: P1
来源: 2026-11-26 CppTLM `rddf status` 重排会话（session ses_de80d7eb1ffevwsEhjIPZb8MnL）实测 —— 19 条 pending 里 13 条是已落地残留 + 4 条已归档条目完全隐身 + oracle/critic 双审（2026-11-26）
阶段: phase-3
分类: cli-tooling
类型: improvement
状态: 已归档（2026-11-27 · change `2026-11-27-fix-rddf-status-terminal-markers` · 7/7 AC pass · 验收报告 `.rddf/reviews/fix-rddf-status-terminal-markers-verify.md`）
主题: rddf status 的终态词表与陈旧状态可见性 —— 「已落地」不再算 pending + 陈旧状态行不再隐身
---

**优先级**: P1 | **来源**: 2026-11-26 CppTLM rddf status 重排会话实测 | **阶段**: phase-3 | **分类**: cli-tooling | **类型**: improvement

## metis 结论（2026-11-27 · 本轮 1 轮覆盖 9 份草稿 · 载体=头部段）

- **「词表可配置」是过度设计**：根因是**缺 3 个词**（`_TERMINAL_MARKERS` 无 `已落地`/`已拆分`/`已取代`），不是「不可配置」⇒ 可配置化引入配置 schema + 加载 + 优先级 + 一条**红态不可复现**的测试 ⇒ **砍掉**，改为「集中常量 + 注释指向登记册」。
- **告警落点二选一悬空** ⇒ AC3 的断言对象不定 ⇒ **钉死 = `snap.errors`**（dashboard 面）。
- 与既有 `fix-rddf-status-corrupt-message.md`（iteration.json corrupt 诊断分级）**形态相邻** ⇒ 复用其「分级 + 指向位置」写法，不发明第二套诊断形态。
- 已改：范围/技术约束/AC5/Capabilities 全面改写；新增与既有诊断形态的**形态对齐**声明。


**主题**: rddf status 的终态词表与陈旧状态可见性

## 架构依据

`rddf status` 的 Pending 视图来自 `_lib/dashboard/__init__.py:658-698` 的 `collect_pending()`：
逐份 improvement 读 front-matter 的 `状态`，用 `_lib/dashboard/improvement_status.py` 的词表分类。
实测（2026-11-26，CppTLM）暴露两个问题：

1. **词表分歧**（`:27-45` 的 `_TERMINAL_MARKERS` 只认 `已完成并归档/已实施并验收/已归档/已完成/已实施/implemented/completed/已作废/作废/superseded/archived`）
   ⇒ 本仓登记册 §6.8 明确要求的完成态 token「**已落地**」被判为 pending ⇒ 19 条 pending 里 **13 条**是已落地残留
   ⇒ **待办面被高估约 3.2 倍**（agent 的规划输入被污染）。
2. **陈旧状态隐身**（`__init__.py:675` `if name in approved or name in archived_names: continue`）
   ⇒ 已归档 / 已批准的 improvement **先过滤再判状态** ⇒ 状态行陈旧（如仍写「已批准·待立项」）的条目**完全看不见**
   ⇒ 4 条已归档条目因此消失（既不在 pending，也不在任何告警面）。

**注意（事实核对）**：「19 / 13」是当次实测值，**不作为本提案的固定数字**（实施时以实测为准）；
可复现的稳定事实是「`已落地` 不在终态词表」与「先过滤后判状态」这两处机制。

## delta 载体（P0 生成输入）

**delta**: modified proposal-lifecycle-sync
**语义要求**: Dashboard pending filter MUST skip archived changes | The dashboard pending pool SHALL classify each improvement's lifecycle status from its leading marker using a single definition point, and that vocabulary MUST treat the registry's completion tokens — including `已落地`, `已拆分` and `已取代` — as terminal. Archived and approved names SHALL be removed from the pending pool only AFTER classification, and an archived-or-approved entry whose recorded status is not terminal MUST be reported as a stale-status diagnostic rather than disappearing from every view. | Archived improvement with a stale status is reported, not hidden | an improvement has an archived copy, its `状态` is not terminal, and the dashboard snapshot is collected | the name is absent from the pending pool and appears in the snapshot's stale-status diagnostics

## 范围

**In Scope**:

- `_lib/dashboard/improvement_status.py`：终态词表补 `已落地` / `已拆分` / `已取代`；词表**集中为单一常量**
  + 注释指向项目登记册白名单 ⇒ 禁「工具认一批、登记册认另一批」两套判据；
  ⚠ **不做「词表可配置」**（review 判定为过度设计：根因是**缺 3 个词**；可配置会引入配置 schema + 加载 +
  优先级 + 一条红态不可复现的测试）⇒ 原「可配置」相关 AC **已删**；
- `_lib/dashboard/__init__.py`：过滤顺序调整 —— 先判状态，**再**按 archived/approved 过滤；若条目因归档被跳过
  而其状态**非终态** ⇒ 进 `stale_status` 告警列表（**可见**，不再隐身）；
- **告警落点钉死 = `snap.errors`**（dashboard 面）⇒ AC3 的断言对象确定；
  ⚠ 与既有 `fix-rddf-status-corrupt-message.md`（iteration.json corrupt 诊断分级）**形态对齐**：复用其「分级 + 指向位置」
  写法，不发明第二套诊断形态；
- 判据文档化：把词表与优先级写进 `rddf status --help` 或 `docs/`（当前 agent 必须读模块源码才知道判据）；
- 回归用例：`已落地` 判终态 / `已拆分` 判终态 / 已归档但状态非终态 ⇒ 进 stale 列表 / 破损 front matter ⇒ 字段级定位。

**Out of Scope**:

- 不改 `rddf status` 的**视图结构**（Mode A/B/D/E 的渲染不变）；
- 不回填任何既有 improvement 的状态行（**项目侧**行为，由各仓自己修）；
- 不改 `improvement-approved.md` / `improvement-suggestions.md` 的生命周期机制；
- 不引入「自动把状态行改成终态」的写侧逻辑（只读面）。

## 关键场景

1. 状态行 `✅ **已落地**（…）` ⇒ 不出现在 pending（当前：出现）。
2. 状态行 `已拆分` ⇒ 不出现在 pending，且标签为「已作废」。
3. improvement 已归档但状态行仍写「🟢 已批准·待立项」⇒ **出现在 stale 告警面**（当前：完全隐身）。
4. front matter 破损（状态行 YAML 双引号标量内嵌裸 `"`）⇒ 给出**字段级**定位（当前：一句 `meta_parse_error`）。
5. 终态词表只有**一处**定义（常量）⇒ 改一处即同时影响分类与文档（单一真源）。

## 技术约束

- 词表单一真源：禁止「工具认一批、登记册认另一批」的两套判据（现状即由此产生 13 条误报）；
- stale 告警**只读**（不改状态行、不写回 improvement）；
- 告警落点**二选一**并登记（避免两个面各报一半）；
- 分类必须**向后兼容**：既有终态判定结果不变（除新增词表项）。

## 验收标准

- [ ] **AC1（红→绿）** 新增 `tests/unit/test_improvement_status_markers.py`：`已落地` / `已拆分` / `已取代` 三个 token
      ⇒ 修复前红（判为非终态）⇒ 修复后绿（判终态）；
- [ ] **AC2（红→绿）** 同文件用例：既有终态 token 全部**零回归**（`已完成并归档` / `implemented` / `已作废` … 仍判终态）；
- [ ] **AC3（红→绿）** 新增 `tests/unit/test_collect_pending_stale.py`：构造「已归档 + 状态非终态」的 improvement
      ⇒ 修复前红（不在任何输出面）⇒ 修复后绿（进 stale 告警列表，且**不**进 pending）；
- [ ] **AC4（红→绿）** 同文件用例：front matter 破损 ⇒ 输出含**字段级**定位（如指出状态行第 N 行 / YAML 错误上下文）；
- [ ] **AC5（单一真源）** 用例：断言终态词表**只有一个定义点**（分类函数与文档/常量引用同一处）⇒ 复制出第二份即红；
- [ ] **AC6（变异）** 把过滤顺序改回「先过滤后判状态」⇒ AC3 用例必须红（判别力证明）；
- [ ] **AC7（门）** `./test.sh --gates` 与 `./test.sh --unit` 全绿。

## Capabilities

- MUST: 登记册常用的终态 token（`已落地` / `已拆分` / `已取代`）判为终态，不进 pending。
- MUST: 已归档 / 已批准但状态行陈旧的 improvement **可见**（进 stale 告警面）。
- MUST: 终态词表**单一真源**（集中常量 + 注释指向登记册；不做可配置化）。
- MUST NOT: 改写既有 improvement 的状态行（只读面）。
- MUST NOT: 出现「工具判据」与「项目登记册」两套并存。

## Impact

| 面 | 影响 |
|---|---|
| `_lib/dashboard/improvement_status.py` | 终态词表 + 可配置化 |
| `_lib/dashboard/__init__.py` | 过滤顺序 + stale 告警 |
| `rddf status --help` / `docs/` | 判据文档化 |
| `tests/unit/` | 新增 2 个测试文件 |
| 项目侧 | 各仓自行回填状态行（不在本提案范围） |
