---
优先级: P2
priority: P2
来源: 2026-11-17 文档审查 P2-4 + P2-5，与 ADR-0060 后续待办「等存量清零后再启用
  ARCH_SHAPE_CHECK」——形态门已能判定，但判定结果无人消费
阶段: phase-2
分类: tech-debt
类型: tech-debt
状态: 待立项（2026-11-24 已按磁盘实测重算基线数字：63 份 ADR / 163 findings / missing_verification 56；本项为多 commit 重实施，立项后分批推进）

生成时间: 2026-11-17
roadmap_ref:
---

# fix-adr-shape-debt-convergence

**主题**: 文档即决策

> **依赖**：必须先完成 `fix-adr-index-generator-dup`（它先立「唯一生成器 + 标记 + 列数」不变量，
> 本项后续任何索引重建都在该不变量保护下）。两者都改 `docs/adr/README.md`，**必须串行**。

## 架构依据

### 现状（2026-11-24 实测，`adr_shape_check.sh --all`）

语料 **63** 份正式 ADR（不含 `ADR-0000-template.md`），**163** 项 findings 分布在 62 个文件，9 个信号：

| 信号 | 计数 | 性质 |
|---|---|---|
| `missing_verification` | 56 | 存量债（事后无法补，见下） |
| `missing_section` | 25 | 机械可修 |
| `alternatives_table_no_conclusion_column` | 24 | 机械可修 |
| `shape_sprawl_heading` | 19 | 需逐份判断 |
| `line_budget`（250 口径） | 17 | 机械可修（拆分/外移） |
| `alternatives_table_missing` | 10 | 与 `missing_section` 互斥（见边界） |
| `process_log_heading` | 9 | 需逐份判断 |
| `verification_section_empty` | 2 | 机械可修 |
| `process_log` | 1 | 已知假阳性（ADR-0060 自身，Consequences 已声明可接受） |

> 该表随语料漂移，**不是判据**：判据只有「基线冻结 + 增量只报新 finding」。
> 立项时若数字已变，以 `adr_shape_check.sh --all` 的实测为准，不要拿本表当断言。

### 为什么不能靠「豁免」解决（本项的核心判断）

一个自然的想法是：形态门读 Status，对 `已替代为 …` 的 ADR 豁免 `missing_verification`。

实测否掉了它：**全仓 Status 含「已替代」的只有 2 份真实 ADR**（`ADR-0001`、`ADR-0046`，
另 1 命中是模板）。豁免写完 ⇒ 56 降到 54，噪音照旧；CI 一开仍会红。

进一步，改门的判定逻辑等于修改 ADR-0060 `## Decision` 的「一律检查」与「Out Scope 不追溯」两句，
需要一份新 ADR 走 `rdd-arch` —— 为 2 份 ADR 的收益开一条契约变更，不成比例。

### 真正的杠杆：区分「存量」与「新增」，而不是消灭存量

`missing_verification` 的 56 份**不该被补**：Verification 章的定义是前瞻验收判据
（「如何观察 ⇒ 通过条件」），对已经实现固化的 ADR 事后补写，等于伪造当时不存在的判据 ——
而且 ADR-0060 的 Out Scope 已明写「既有 ADR 的存量改写（不追溯）」。

所以目标不是「162 项归零」，而是让形态门**能作为门使用**：

1. **存量不阻断**（基线冻结，ratchet 只降不升）
2. **新增必干净**（本项落地后新写的 ADR findings = 0）
3. **判据一条不放宽**（不改 `adr_shape_findings` 的信号集与预算 ⇒ 不需要新 ADR）

这三条合起来，才让 `ARCH_SHAPE_CHECK` 有机可接：门检的是「你有没有新增债务」，不是「历史债务还在不在」。

## 范围

**In Scope**：
- 形态检查的**基线机制**：per-file × per-signal 冻结清单 + 只报增量 + ratchet 守卫
- `adr_shape_check.sh` 的 CLI 语义补全（`--baseline` / `--diff-baseline` / `--summary`）
- `ARCH_SHAPE_CHECK` 接入 CI（按增量模式，存量不阻断）
- 机械可修类与散文形态类的**分批**收敛（可选，见 What Changes #4 —— 它不是达成目标的前提）
- P2-5 状态可机读：`extract_metadata` 增 `status_class`（枚举 6 值）+ `status_raw`（原文保留）

**Out of Scope**：
- 为存量 ADR 补写 Verification 判据（伪造证据）
- 修改 `adr_shape_findings` 的信号集 / 预算 / warning 级别（**它们是 ADR-0060 的已签批决策**）
- 修改 ADR-0060 的 Decision（本项不改判据 ⇒ 无需 ADR-0061）
- `docs/adr/README.md` 散文段纳入生成（属 `fix-doc-drift-residual` P2-1）

## Why

形态门现在给出 163 项输出，其中 56 项是「预期内、不追溯」的同一种债。后果有两层：

1. **信噪比**：56/63（89%）的 ADR 都报同一项时，人不再逐条看 ⇒ 真正的新问题被淹没（信号习惯化死亡）。
2. **门装成门帘**：ADR-0060 后续待办要求「等存量清零后再启用 `ARCH_SHAPE_CHECK`」，而存量永远不会清零
   （56 份不能补）⇒ 形态门永远 opt-in，等于没有门。

本项把「清零」改成「冻结增量」，两件事同时解决，且不改任何判据。

## What Changes

1. **基线文件**：`docs/adr/.adr-shape-baseline.json`（committed，跟随仓库演进），内容为
   `{file: {signal: {detail, recorded_at}}}` —— **per-file × per-signal 清单，不是标量总数**
   （标量总数在 ADR 增删后无意义）。生成方式：`adr_shape_check.sh --all --write-baseline`。
2. **增量模式**：`adr_shape_check.sh --diff-baseline` 只报「基线中不存在的新 finding」；
   已知存量折叠成一行计数。CI 用这个模式。
3. **ratchet 守卫**（三条，缺一不可）
   - **非空**：基线不得为空文件（本仓刚被 `KNOWN_FAILURES.txt` 截断咬过一次）
   - **单调不增**：新基线 ⊆ 旧基线（`--write-baseline` 只能删除条目或保持不变，不得新增）
   - **单一写路径**：只有 `--write-baseline` 能写它，其余路径只读
4. **存量收敛（可分批推进，非本项完成前提）**：机械可修类（备选表结论列 24 / 缺章节 24 / 超行数 16）
   按批修改后 `--write-baseline` 把条目从基线移除 ⇒ 基线逐批缩小，债务显式可见。
   `missing_verification` 的 56 项**永远留在基线里直到对应 ADR 被替代**，这是预期行为，不是失败。
5. **状态可机读（P2-5）**：`_lib/adr_index_generator.py` 的 `extract_metadata` 增两个键 ——
   `status_class`（枚举：`draft` / `proposed` / `accepted` / `amended` / `superseded` / `rejected`）
   与 `status_raw`（原文不动）。**不修改任何 ADR 的 Status 行**（40 份的自由文本保持原样，
   分类在生成器侧完成）。`ADR-0055` 的 Status 行去掉 commit 号（它在触发 `ARCH_ADR_STATUS_MAX`）。
6. **CI 接入**：`ARCH_SHAPE_CHECK=yes` + 增量模式进 CI；该 step 必须实际执行（不是 skip）。

## Acceptance

- [ ] `docs/adr/.adr-shape-baseline.json` 存在，且为 per-file × per-signal 结构（不是标量总数）；`python3 -c "import json;d=json.load(open('docs/adr/.adr-shape-baseline.json'));assert isinstance(d,dict) and all(isinstance(v,dict) for v in d.values());print(len(d),'files')"`
- [ ] **非空守卫**：基线文件条目数 > 0，否则 `adr_shape_check.sh --diff-baseline` exit 2（变异验证：清空基线 ⇒ exit 2，不是「全绿」）
- [ ] **单调守卫**：`--write-baseline` 在「新结果含基线中不存在的 finding」时拒绝写入并 exit 1（变异验证：手工加一条不存在的 finding ⇒ 拒绝）
- [ ] **增量模式有效**：`--diff-baseline` 在当前语料上 exit 0；人为在某个 ADR 里加一节 `## v9 修订日志` ⇒ exit 1 且只报这一条
- [ ] **新增 ADR 必洁**：新建一份缺 Verification 的 ADR ⇒ `--diff-baseline` exit 1（它不在基线里）
- [ ] **判据未被放宽**：`git diff` 对 `_lib/arch_quality_gate.py` 的改动**不含**信号集 / 预算 / severity 的修改（只有基线读写与 Status 解析分类）
- [ ] `status_class`：对全部 63 份正式 ADR 运行分类，取值集 ≤ 6 个；`status_raw` 与原文逐字符相等（不丢信息）
- [ ] `grep -cE "commit|@[0-9a-f]{7}" docs/adr/ADR-0055-*.md` 在 Status 行内为 0（该行可用 `python3 -c` 精确取 Status 行再匹配，不用 `grep -c` 数全文）
- [ ] CI：`ARCH_SHAPE_CHECK=yes` 在 `.github/workflows/` 可见，且该 step 在 PR 中**实际执行**（`skip` 不算通过）
- [ ] `pytest tests/unit/test_arch_quality_gate.py -q` 全绿，且新增用例覆盖：① 基线非空 ② 增量只报新 finding ③ `--write-baseline` 拒绝新增条目
- [ ] **负例夹具**（每条新信号配一份「精确踩它」的 ADR 夹具 + 一份「形似但不该报」的夹具，双向断言）—— 沿用 ADR-0060 V-11 的模式

## 实施纪律（非验收项）

- 存量收敛分批推进，每批 ≤10 文件、每批单独 commit —— 避免单次 PR 变成 50+ 文件重写（ADR-0060 明确反对）
- 每批修改后必须 `--write-baseline`，否则下一批的 diff 会把上一批的修改当成新 finding
- 改 Status 行（第 5 项只影响 `ADR-0055`）后必须重建 ADR 索引，否则 `test_adr_index_gate.py` 的逐字节断言红

## Capabilities

- 作者：新增 ADR 时形态门给出的 findings **全部是真实问题**（存量折叠为一行计数）
- CI：形态门可以真正启用 —— 检「是否新增债务」而非「历史债还在不在」
- 维护者：基线文件是**显式的债务账本**，缩小它的进度可见（ratchet 只降不升）

## Impact

- **受影响文件**：`docs/adr/.adr-shape-baseline.json`（新增）、`_lib/arch_quality_gate.py`（基线读写 + Status 分类，不改判据）、`skills/rdd-arch/scripts/adr_shape_check.sh`（4 个新 flag）、`_lib/adr_index_generator.py`（`status_class`）、`docs/adr/ADR-0055-*.md`（去 commit 号）、`.github/workflows/`（CI 接入）、`tests/unit/test_arch_quality_gate.py`
- **回归风险**：中 —— 基线机制本身是新的「可被掏空的数据」（本仓两次教训），故 AC 里三条守卫（非空/单调/单一写路径）都是必须项，不是加分项
- **与 `fix-adr-index-generator-dup` 的耦合**：那项先立 README 索引不变量；本项第 5 项的 `status_class` 会改索引内容，必须在其之后
- **估算**：基线机制 + CLI + 守卫 ~3 小时；CI 接入 ~30 分钟；存量收敛视批次而定（不计入本项完成判据）

## 审稿记录

**metis 第 1 轮（2026-11-17）** —— 判定：本项初稿的 Path A（Status 感知豁免）**方向错误**，已据其结论重写：

| finding | 处置 |
|---|---|
| 「Path A 收益只有 2 项（已替代的 ADR 仅 2 份）」⇒ 57 → 55，CI 一开就红（数字为 2026-11-17 当时值；2026-11-24 重测为 56 → 54） | ✅ **采纳，方案作废**。改为「增量门 + 冻结清单」，判据一条不放宽 ⇒ 无需 ADR-0061 |
| 「改门的判定逻辑等于改 ADR-0060 的两句决策 ⇒ 须走 rdd-arch」 | ✅ 采纳：重写后本项**不触碰** `adr_shape_findings` 的信号集/预算 |
| AC「总数 ≤ 豁免后基线」是自反命题（基线定义为自己） | ✅ 采纳：删除该 AC，改为三条可判定命题（非空 / 单调 / 增量只报新 finding） |
| AC「`missing_verification` 降到 X，实施首日填值」= 事后自证 | ✅ 采纳：改为「新增 ADR 必洁 + 存量永留基线」 |
| AC 里 `grep -c … 在 Status 行窗口内` 不可执行（`grep -c` 数全文） | ✅ 采纳：改为 `python3 -c` 精确取 Status 行后匹配 |
| 词表一行式有 bug（KeyError / glob 含模板）且隐含改 40 份 ADR | ✅ 采纳：改为生成器侧 `status_class` 分类，**不动任何 ADR 的 Status 行** |
| 「`alternatives_table_too_few_rows` 也在输出里，基线表漏了它」 | ❌ **不采纳**（metis 事实错误：实测该信号 0 命中，当前信号集就是表里 9 个） |
| 「每批 ≤10 文件 + 单独 commit」写进 AC 无法机读验证 | ✅ 采纳：移入 `## 实施纪律` |
| 「`为什么不能机械补 Verification` 占全文 60%、300vs250 对照是复述」 | ✅ 采纳：压缩为一节结论，删掉 300/250 对照表 |
| 缺「守卫本身不能是假保证」类 AC | ✅ 采纳：三条守卫 + 每条新信号配负例夹具 |
| `alternatives_table_missing` 与 `missing_section` 互斥（补章节会换成另一个信号，净收益 0） | ⚠️ **部分采纳**：本项不再以「计数下降」为判据（改判据是增量与基线），故净收益为 0 的问题消解；但产出表格时须在 `adr_shape_check.sh` 的 `--help` 写明这对信号的互斥关系，避免实施者用「造假备选表」凑数 |
