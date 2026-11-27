---
优先级: P1
来源: 2026-11-27 CppTLM `rddf status` 实测（U4 `fix-rddf-status-terminal-markers` 归档后的第一次真实使用）—— 标题报「6 improvement issue(s)」但只列 5 条，第 6 条仍隐身
阶段: phase-3
分类: cli-tooling
类型: improvement
状态: 已批准·待立项（planner 2026-11-27 · W3 = U10 · 独立 change · 7 条 AC 含 TDD 三段）
主题: status 视图不得截断 issue 列表 —— 陈旧/破损信号必须逐条可见（+ 状态摘要不再硬切在引号中间）
---

**优先级**: P1 | **来源**: 2026-11-27 CppTLM 实测（U4 上线后的第一次真实使用） | **阶段**: phase-3 | **分类**: cli-tooling | **类型**: improvement

**主题**: status 视图不得截断 issue 列表 —— 陈旧/破损信号必须逐条可见

## 架构依据

U4（`fix-rddf-status-terminal-markers`，已归档）把「已归档/已批准但状态行非终态」的 improvement
从**完全隐身**变成 `snap.errors` 里的**可诊断条目**。但 2026-11-27 在 CppTLM 实测发现：**输出层把新信号又截断了**。

实测（`rddf status`，CppTLM 仓，77 份 improvement）：

```
⚠️  6 improvement issue(s) (unreadable / invalid front matter / stale status lines)
   - cep-ssp-batch2: stale status — …
   - cep-ssp-cp-q1b-landing: stale status — …
   - cpptlm-cep-mesh-e2e-carrier: stale status — …
   - cpptlm-module-param-read-declares: stale status — …
   - cpptlm-spec-purpose-batch3: stale status — …
                                  ← 第 6 条（cpptlm-spec-scenario-level-fix）没有出现
```

根因：`_lib/cli/status_cmd.py:370` 的 `for err in snapshot.errors[:5]:` —— **标题报真实条数，
正文只列前 5 条** ⇒ 「计数与列出不一致」＝ 被截断的那条与看不见没区别。

⇒ 这正是 U4 要消灭的**同一类缺陷**（静默失效）：U4 把「状态行陈旧 ⇒ 完全看不见」修成了
「状态行陈旧 ⇒ 列出来（但只列前 5 条）」。**修复不能只落在产生信号的一侧** —— 消费侧也必须保真。

两条相邻缺陷（同一次实测暴露）：

1. **计数与列出不一致**（`[:5]` 硬截断，无任何「还有 N 条」提示）；
2. **状态摘要硬切在引号中间**：摘要在 40 字处截断，落在 `「🟢 **已批准·待立项**(2026-11-26 · 用户批准 5 段设计 · 」`
   的引号中间 ⇒ 读者看到半截引号。

## delta 载体（P0 生成输入）

**delta**: added status-issue-visibility
**语义要求**: Status issue lists SHALL NOT be silently truncated | `rddf status` SHALL list every improvement issue it reports: the count in the heading SHALL equal the number of listed entries, and any entry not shown SHALL be announced by an explicit remainder line naming the count and pointing at the full view (`rddf dashboard`). Status snippets SHALL be trimmed at a safe boundary and end with an ellipsis, so markdown emphasis or quotes are never cut in half. Snippet cleaning SHALL reuse the classifier's existing markdown stripping — one implementation, no second copy. | Six reported issues are all listed | six improvements carry stale status lines and `rddf status` runs | the heading states six issues, six issue lines are printed, and no remainder line appears

## 范围

**In Scope**:

- `_lib/cli/status_cmd.py`：issue 列表**不再静默截断** —— 逐条列出；超过显式阈值时给出
  「还有 N 条未展开」的**明示**行（明示 ≠ 静默），并指明全量在 `rddf dashboard`；
- `_lib/cli/status_cmd.py`：状态摘要改为「清洗后截断 + 省略号」（不在引号/强调标记中间硬切）；
- 计数与列出的一致性：标题条数 == 实际列出条数（未展开时标题旁明示未展开数）；
- 回归用例：issue 数 > 截断阈值时，标题/正文不出现「计数 ≠ 列出」的静默缺口；
  状态摘要带 `…` 且不落在引号中间。

**Out of Scope**:

- **不**改 issue 的**产生**侧（哪些条目算 stale / 哪些算 metadata problem —— U4 已定，本次不动）;
- **不**改 `rddf dashboard` 的渲染（本来就全量列出，本次只是让 status 侧与它一致）;
- **不**回填任何仓的 improvement 状态行（项目侧行为）;
- **不**引入「按严重度排序 / 分级」的新机制（顺序保持现状：文件名字典序）;
- **不**改 pending 表的渲染。

## 关键场景

1. CppTLM 实测的 6 条 stale ⇒ **6 条全部列出**，标题写 6，列出 6（当前：写 6、列 5）。
2. issue 数远超阈值（> 20）⇒ 列出前 20 + **明示**「还有 N 条未展开（见 `rddf dashboard` 看全量）」，
   标题不再暗示「共 N 条已全部列出」。
3. 状态摘要超长 ⇒ 以 `…` 结尾，且不落在 `「…」` 或 `**…**` 的中间（可机判：摘要里引号成对）。
4. issue 数为 0 ⇒ 该段整体不出现（现状不变）。

## 技术约束

- **不静默**：任何未列出的条目都必须有明示的计数说明（禁止「标题说 N、只列 M < N」且无提示）；
- 与 `rddf dashboard` 的一致性：dashboard 全量列出 ⇒ status 侧至少不得比它**更少**且无提示；
- 阈值必须**有测试钉住**（避免以后被随手调小而无人察觉）；
- 摘要清洗复用既有 markdown 清洗能力（`_lib/dashboard/improvement_status.py` 已有 `_strip_markup`），
  **不新建**第二份清洗实现。

## 验收标准

- [ ] **AC1（红→绿）** 新增 `tests/unit/test_status_issue_list_not_truncated.py`：构造 **6** 条 stale issue
      ⇒ 修复前 `rddf status` 只列 5 条（红）⇒ 修复后 6 条全部出现，且标题里的计数与实际列出条数**一致**；
- [ ] **AC2（红→绿）** 同文件用例：issue 数 **> 阈值**（构造 30 条）⇒ 输出含**明示**的「还有 N 条未展开」行，
      且标题/正文不再出现「计数 ≠ 列出且无提示」的静默缺口；
- [ ] **AC3（红→绿）** 同文件用例：状态摘要超长 ⇒ 以 `…` 结尾，且 `「`/`」`（及 `**`）**成对**
      （⇒ 不再硬切在标记中间）；
- [ ] **AC4（回归）** 既有 status / dashboard 用例**零回归**
      （`python3 -m pytest tests/unit -k "status or dashboard or improvement_status" -q` 全绿）；
- [ ] **AC5（单一真源）** 摘要清洗**复用** `_lib/dashboard/improvement_status.py` 的既有清洗函数
      （对象身份断言：status 侧引用的清洗函数 == improvement_status 里的那个）⇒ 复制第二份即红；
- [ ] **AC6（变异）** 把截断改回 `[:5]` 且去掉明示行 ⇒ AC1/AC2 必须红（判别力证明）；
- [ ] **AC7（门）** `./test.sh --gates` 与 `./test.sh --unit` 全绿。

## Capabilities

- MUST: status 视图的 issue 列表**逐条可见**；未展开的部分必须有**明示**的计数说明。
- MUST: 标题里的 issue 计数与实际列出条数一致（或明示差值）。
- MUST: 状态摘要以省略号收尾，且不在 markdown 标记（引号/强调）中间截断。
- MUST: 摘要清洗与状态分类**同源**（同一实现，禁第二份）。
- MUST NOT: 改 issue 的产生侧判据（哪些条目算 stale / 破损）。
- MUST NOT: 让 status 视图比 `rddf dashboard` 展示得**更少**且无提示。

## Impact

| 面 | 影响 |
|---|---|
| `_lib/cli/status_cmd.py` | issue 列表渲染（去 `[:5]` 硬截断 + 明示未展开行）；状态摘要截断形态 |
| `_lib/dashboard/improvement_status.py` | 复用其既有清洗函数（**不改实现**） |
| `openspec/specs/` | 新 capability `status-issue-visibility`（1 requirement） |
| `tests/unit/test_status_issue_list_not_truncated.py` | 新增 4–5 例 |
| CppTLM / 其他仓 | 无需改动（只读受益） |
