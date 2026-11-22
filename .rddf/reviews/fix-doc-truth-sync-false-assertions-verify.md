# fix-doc-truth-sync-false-assertions 验收报告

**change**: `fix-doc-truth-sync-false-assertions`
**判据来源**: `openspec/changes/fix-doc-truth-sync-false-assertions/proposal.md` 的 `## Acceptance`（AC-1 ~ AC-9）
**已用轮次**: 2（critic 2 轮 + 本验收）

## 逐条判定

| AC | 判定 | 证据 |
|---|---|---|
| **AC-1** 12 组假断言（A1-A12）逐条处置完毕，spec 的每条 Scenario 断言都能核实为真或已显式退役 | **PASS** | 台账「12 组假断言逐条核算」表逐组给了「实测 + 处置 + 证据行号」。逐条复核：`grep -c 'exactly \`bats tests/\`\|15 directories\|"19"\|5 阶段 + 1 退出\|dup unflagged\|skills/foo\.md\|session_v20' openspec/specs/doc-truth-sync/spec.md` ⇒ **0 命中**（`guide-spec` 仅存于 D6 漂移类的合法引用）。Requirement 数 **8 → 7**（退役 `v2-api-ref-path-corrections`） |
| **AC-2** 迁移指南两张表的当前路径全部存在于 disk | **PASS** | 解析三张表的「当前路径（v4.0+）」列并 `Path(p).exists()` ⇒ **14/14 存在**（含 `docs/legacy/skills/execute` / `docs/legacy/skills/status`）。表内另有 `rddf status`（CLI 命令，非路径） |
| **AC-3** README 的 `skills/` 树零 dangling + 零遗漏（占位符不误报） | **PASS** | 树抽取（`├──`/`└──` 条目，前缀 `skills/`）+ `Path.exists()` ⇒ dangling **0**；disk 26 个 `skills/*/SKILL.md` 与树内 26 条 ⇒ 遗漏 **0** |
| **AC-4** README / AGENTS 不再硬编码 `_lib` 的 .sh/.py/schema 构成计数 | **PASS** | 宽口径扫描（`数字 + 个/files/.py/.sh/schema/cases/CLI/subcommand/…`）在两文件上只剩 **豁免项**：README:33 与 AGENTS:98 的 `26 个子技能`（skill 计数，动态守卫锁定）+ AGENTS AUTO 段（自动生成） |
| **AC-5** 4 个新守卫全绿 + 负向验证 | **PASS** | `pytest tests/unit/test_doc_contracts.py -q` ⇒ **24 passed**。负向 5 变体逐个注入并复测：**dangling 条目 ✅抓到 / 遗漏 skill ✅抓到 / 硬编码计数 ✅抓到 / planned 标记被删 ✅抓到 / D5 反向断言 ✅抓到**；2 个豁免**不误报**（占位符 `<skill>/scripts/`、skill 计数） |
| **AC-6** `validate --all --json` issue 多重集只减不增；`very long` 不新增；ERROR 不增 | **PASS** | 用 openspec 自己的 parser 在临时目录比对新旧 specs：**改前 224 条 / 改后 224 条**；`新增 0`；`very long: 62 → 62`；`openspec validate --all` ERROR 计数 **11 → 11**。唯一差异是 `doc-truth-sync` 的 `requirements[N]` 索引位移（退役 Requirement 导致），不是新 issue |
| **AC-7** 残留扫描器命中数不变 | **PASS** | `scan_specs(Path('.'))` ⇒ `未豁免 0/0/0`、`含已豁免 303/159/41`、豁免 303；四诊断 `stale=0 invalid=0 in_fence=0 fence_rejected=0` |
| **AC-8** `pytest tests/unit/` + 相关 bats 全绿；`ruff` 全绿 | **PASS** | `pytest tests/unit/ -q` ⇒ **3522 passed, 3 skipped**（3518 + 4 新守卫）；`python3 -m ruff check skills/_lib/`（CI/门的实际范围）⇒ **All checks passed!** |
| **AC-9** `./test.sh --full --regression` 全绿 | **见下** | 见「全量门」 |

## 全量门

`BATS_TIMEOUT=120 BATS_TIMEOUT_RETRY=240 ./test.sh --full --regression`

结果：见「全量门」段。

## 遗留清扫

| 项 | 结果 |
|---|---|
| 本次范围内的 TODO / 半截实现 | 无 |
| 注释掉的代码 | 无新增 |
| 临时调试日志 | 无（实施脚本在 `/tmp/opencode/`，不入仓） |
| 被 skip 的测试 | 无新增 skip（2 个 spec 守卫在 `openspec/` 缺失时 skip —— 与既有 `requires_general_spec` 同模式） |
| 未替换的 mock | 不涉及 |
| 临时 fallback 分支 | 无 |
| 未采纳的 finding | critic 第 2 轮 NIT-1（`doc-truth-sync` 的 Requirement 主题划分）—— **不采纳**：改结构会再次移动 `very long` 序号 + 需再动冻结清单 + 应重新过审，而 **critic 预算已满 2 轮** ⇒ 记 tail |

## 实施期教训

1. **「改判据」必须整块改，不只是被点名的那一行。** A7 我改了 D5 的 **bullet**（`:132-134`），
   漏了 **Scenario**（`:198-204`）里的 `stderr reminds: "npm test MUST only run bats"` ——
   **守卫 #1 在实施中抓到它**。⇒ 上一批的教训「改写一个 Requirement 必须保证内部自洽」
   在同一批里复发了一次；**守卫是唯一可靠的对冲手段**。
2. **上一批漏的「同类文本」会在下一批立刻暴露。** 上批修了 `general/spec.md` + 7 份文档，
   漏了 `doc-truth-sync/spec.md` ⇒ 两个 spec 互相矛盾。⇒ 「判据 surface 必须覆盖同类文本」
   不是一次性的检查动作，而是**要写进守卫**的常驻约束。
3. **「去掉计数两个字」不等于「去掉计数」。** critic 第 2 轮抓到 `README.md:161-162`
   我只删了「个 / 子命令」，**数值 36 还在**（实测 41）。⇒ name-free 化要连**数值**一起去掉，
   并且守卫的后缀表要覆盖该数值的**所有表述形态**（`CLI` / `subcommands` / `子命令` / `commands`）。
   补齐后缀表又立刻抓出第三处（`README.md:406`）。
4. **name-free 化计数可能连带删掉别的守卫依赖的字面量。**
   第一次全量门 **GATE_RC=1**（`新增失败: 1`）：
   `tests/integration/test_doc_contracts.bats:53` 断言 `AGENTS.md` 出现
   `ADR-0001`/`0010`/`0019`/`0020` **字面量**；我把 `docs/adr/` 行从
   `ADR-0001~0053 (53 个 ADR 编号, …)` 改成「编号与数量以 disk 为准」时，
   **把 `ADR-0001` 这个字面量一起删了** ⇒ 守卫红。
   ⇒ 改文档前先 grep「这份文档被哪些测试引用」，区分守卫依赖的是**计数**还是**字面量**。
   ⇒ 修法：保留字面量、只去计数（`ADR-0000 模板 + ADR-0001 起；编号与数量以 disk 为准`）。
5. **「守卫能抓到什么」必须用负向验证证明，不能靠读代码。** 本批对 5 个变体逐个注入并复测，
   5/5 抓到；第一次跑时 **负向4 没抓到**（planned 标记的豁免词「手动」太松 ——
   那一行的「手动验证」指的是手工步骤，不是 CLI 未实现）⇒ 收紧到 `规划中|planned|未实现`。
   **豁免词本身就是判据的一部分。**

## 路由建议

无需返工。本批可归档。tail 的 2 条实现缺口（`rddf status` 缺 `review` 渲染、
`rddf archive` 缺交互确认门）属 `implementation_gap`，独立立项。
