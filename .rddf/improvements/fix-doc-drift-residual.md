---
优先级: P2
priority: P2
来源: 2026-11-17 文档审查 P1-5 / P1-6 / P2-1 / P2-2 / P2-3 与 critic 第 1 轮
  SHOULD_FIX#3 —— 五项共享同一根因：同一事实只有散文副本，没有断言能发现它过期
阶段: phase-2
分类: tech-debt
类型: tech-debt
状态: draft

生成时间: 2026-11-17
roadmap_ref:
---

# fix-doc-drift-residual

**主题**: 文档即契约

> **P1-7（`skill-role-model/spec.md` 的 v3 命名同步）已拆出**，单独立项为
> `fix-spec-v3-naming-sync`：它需要 spec delta，与其余五项（tech-debt 直改、不产生 delta）
> 生命周期不同，混在一条 change 里会让 archive gate 无从判定。

## 架构依据

### 五项残留的共同根因

本轮已修完文档审查的 P0 与 P1-1~P1-4。剩下这五项**不是五个独立问题**，而是同一模式的五个实例：
**某条事实只以散文形式存在于某个文件里，没有任何断言能发现它过期**。所以它们各自过期、各自沉默，
直到一次人工审查才发现。

| 项 | 事实 | 当前状态（实测） | 为什么沉默 |
|---|---|---|---|
| P1-5 | ADR-0035 双轨边界 + ADR-0060 形态门 | `grep -c "verifier\|ARCH_SHAPE_CHECK\|ADR-0035\|ADR-0060" docs/architecture/gates-and-quality.md` = **0** | 无人断言该文件应提及验收/形态门 |
| P1-6 | 治理状态层（`role.json` / `pair.json`） | `grep -c "role.json\|pair.json" docs/architecture/state-and-events.md` = **0** | `rddf-layout.md` 有，但没人要求 state 主题文档也提 |
| P2-1 | ADR README 散文段（顶部实施状态表 / 主题分类 / 架构演进 / 上次同步） | 生成器只重写 `<!-- ADR_INDEX_START/END -->` 之间的表格 | 散文段无生成器覆盖 |
| P2-2 | 手写版本号与计数 | 本轮手工修正了 `overview.md` 的 skill 计数与 `README` 的版本行 | 靠人读、靠人改 |
| P2-3 | 断链检查 | **仓库内无任何 markdown 链接检查器**（本轮用的是临时脚本 `/tmp/opencode/linkcheck.py`） | 没有任何断言检查链接 |
| critic#3 | verifier 双落点在 `rddf-layout.md` 有一份副本 | `agent-role-alignment.md`（声明层）+ `rddf-layout.md`（速查副本） | 改一处不同步另一处不会红 |

### 为什么先修守卫、再补内容（顺序不能反）

若先补 P1-5/P1-6 的内容、后补守卫，补的过程中没有任何东西阻止它们再次漂移；
下一次漂移依然要等一次人工审查 —— 那正是本轮在做的事。
所以顺序是：**先把「事实过期会被发现」做成断言，再补内容让它变绿**。

### 为什么断链检查器必须入库

本轮用 `/tmp/opencode/linkcheck.py` 查了全仓 markdown 断链（0 处），但脚本在仓库外 ⇒
下一次没人能重跑。而它是 P0-1（5 处失效路径）与 P0-6（5 处断链）**被发现的唯一工具**。
修了 10 处断链、却没有把发现的工具留下来，这是「修症状不修工具」。

## 范围

**In Scope**：
- 新增 `tests/scripts/check_md_links.py` + `tests/integration/test_md_links.bats`
- `docs/architecture/gates-and-quality.md` 补 ADR-0035 双轨 + ADR-0060 形态门（两节）
- `docs/architecture/state-and-events.md` 补治理状态层（指针式，不复制 `rddf-layout.md` 的表）
- ADR README 散文段纳入 `_lib/adr_index_generator.py` 的 `--check` 只读模式
- 文档版本/计数派生化（或 `rddf docs --check`）
- 守卫扩展：guide-* 裸提及正则扩到 `docs/architecture/**`；`docs/architecture` ↔ `docs/adr` 交叉引用一致性
- `rddf-layout.md` 的 verifier 双落点副本收敛为指针（**只动这一处**，见下）

**Out of Scope**：
- **`skills/rdd-verifier/SKILL.md:448-458` 的作者声明保留不删** —— 那是 P1-2 重定向后确立的
  **声明层**（「为什么产品落点不在 owns 里」是 `skill-role-owns-generated-artifacts-only` 在 skill 侧的唯一落地解释），
  不是副本层。把它压成指针等于撤销 P1-2 的整改依据
- `openspec/specs/**` 的 v3 命名（已拆为 `fix-spec-v3-naming-sync`）
- 存量 ADR 形态债（属 `fix-adr-shape-debt-convergence`）
- ADR 索引生成器去重（属 `fix-adr-index-generator-dup`）
- 任何行为/契约变更（本项只改文档与守卫）

## Why

本轮审查发现的 10 项 P0/P1 缺陷，**没有一项是被现有测试发现的** —— 全部来自一次性人工审查
（一个 subagent 会话 + 60 份 ADR 逐份扫描）。不补守卫，下一次同样的漂移依然只能等人工审查。

## What Changes

1. **markdown 断链检查器入库**：`tests/scripts/check_md_links.py`，解析相对链接 + 锚点；
   忽略外部 URL、`mailto:`、代码块内的伪链接。扫描根与覆盖目录**显式成清单**
   （本轮实际断链包含跨出 `docs/` 的引用，如 `docs/adr/ADR-0033` → `.rddf/improvements/*`）。
   配 `tests/integration/test_md_links.bats`。
2. **`gates-and-quality.md` 补两节**：ADR-0035 的 verifier / archive-gate 双轨边界；ADR-0060 的
   `ARCH_SHAPE_CHECK` opt-in 形态门。两节只写「是什么 / 在哪 / 怎么开」，真源指向 ADR 与代码。
3. **`state-and-events.md` 补「治理状态层」**：`role.json`（role-v2 的 `sessions` 分区）、`pair.json`
   （派发登记，`required_when=never`）与 rdd 自身状态的关系；**指针**指向 `rddf-layout.md` 的文件级表
   （不复制那张表 —— 复制就是再造一个副本）。
4. **ADR README 散文段加只读校验（P2-1）**：给 `_lib/adr_index_generator.py` 加 `--check` 模式，
   断言「顶部实施状态表 / 主题分类 / 架构演进 / 上次同步」四段与生成结果一致。
   **不接管生成**（接管会改 `.py` 行为，见 AC 末条）—— 只做校验，让漂移变红。
5. **版本/计数派生化（P2-2）**：`docs/architecture/*.md` 的手写版本号与计数改为
   「见 `package.json` / `ls docs/adr` / `ls skills`」，或加 `rddf docs --check` 的巡检断言。
6. **守卫扩展（P2-3）**：`test_v4_doc_drift_contracts.bats` 的 guide-* 正则从「3 种 live invocation 句式」
   扩到「裸提及」，范围限 `docs/architecture/**` 与 `skills/**`（**不含** `openspec/specs/**`）；
   新增 `docs/architecture` ↔ `docs/adr` 交叉引用一致性检查。
7. **双落点副本收敛（critic#3）**：`docs/architecture/rddf-layout.md` 里的双落点表述改为一行指针，
   完整表只保留在 `docs/architecture/agent-role-alignment.md` 的「verifier 双落点」节。

## Acceptance

**守卫有效性（先做，先绿）**

- [ ] `python3 tests/scripts/check_md_links.py --all` ⇒ exit 0；**扫描 0 个文件或 0 个链接 ⇒ exit 1**（不是 exit 0）
- [ ] 覆盖目录清单显式化：脚本内有 `SCAN_ROOTS` 列表，含 `docs/`、`skills/`、`openspec/specs/` 与仓库根 `*.md`；且有文件数下限断言（`--all` 时扫到的 `.md` 数 ≥ 硬下限）
- [ ] 变异验证：把某个链接的 `../` 改错 ⇒ exit 1 且报出该文件与行号
- [ ] `bats tests/integration/test_md_links.bats` 全绿，且该 bats 在 CI 中**实际执行**（`skip` 不算通过）
- [ ] 交叉引用守卫：`docs/architecture/*.md` 里引用的 `ADR-NNNN` 编号在 `docs/adr/` 中存在（变异验证：写一个不存在的 ADR-9999 ⇒ 红）

**内容补齐（守卫就位后变绿）**

- [ ] `grep -c "ADR-0035" docs/architecture/gates-and-quality.md` ≥ 1 **且** `grep -c "ARCH_SHAPE_CHECK" docs/architecture/gates-and-quality.md` ≥ 1
- [ ] `grep -c "role.json" docs/architecture/state-and-events.md` ≥ 1 **且** `grep -c "pair.json" docs/architecture/state-and-events.md` ≥ 1
- [ ] `state-and-events.md` 的治理状态层为指针式：该文件中出现 `rddf-layout.md` 的引用，且**不含** `role.json` / `pair.json` 的完整字段表（避免再造副本）
- [ ] `python3 _lib/adr_index_generator.py --check` ⇒ exit 0；把一个散文段的计数改错 ⇒ exit 1（变异验证）
- [ ] 手写版本号：`python3 tests/scripts/check_md_links.py --versions`（或 `rddf docs --check`）列出 `docs/architecture/*.md` 内所有 `N.N.N` 形态的版本串及其来源；残留项必须为 0 或逐项标注「派生自 package.json」
- [ ] `grep -c "guide-arch\|guide-design\|guide-plan\|guide-ship" docs/architecture/*.md` = 0（裸提及也算）
- [ ] 双落点收敛：`grep -rn "记账落点" docs/ skills/` 中，完整表格只在 `agent-role-alignment.md`；`rddf-layout.md` 的对应表述 ≤ 2 行且含指向 `agent-role-alignment.md#verifier-双落点` 的链接
- [ ] **信息不丢失**：`agent-role-alignment.md` 的双落点节必须同时含 `记账落点`、`产品落点`、`为什么产品落点不在 owns 里` 三段语义（变异验证：删掉其中任一段 ⇒ 红；不是删掉表格某一行就红）

**边界**

- [ ] 本项**不修改** `_lib/**` 的既有行为：`git diff --stat _lib/` 只允许 `adr_index_generator.py`（新增 `--check` 分支）出现在变更列表，且该分支不改变默认输出
- [ ] `git diff --stat skills/*/SKILL.md` 为空（作者声明保持原样）

## 实施纪律（非验收项）

- 守卫扩展（裸提及正则 + 断链）上线时先以 warn 运行一批，确认既有残留清单后再升级为 block —— 否则一次暴露大量历史残留，会把本项变成「修 48 份文档」
- `tests/scripts/check_md_links.py` 必须零外部依赖（stdlib only）

## Capabilities

- 作者：新增文档时断链与 guide-* 残留会在提交前被拦（不再依赖人工审查）
- 读者：`gates-and-quality.md` / `state-and-events.md` 可独立读懂，不必跳去读 ADR
- 维护者：断链检查器入库 ⇒ 下一次同类问题可自行复现，而不是依赖某次审查的临时脚本

## Impact

- **受影响文件**：`tests/scripts/check_md_links.py`（新增）、`tests/integration/test_md_links.bats`（新增）、`docs/architecture/gates-and-quality.md`、`docs/architecture/state-and-events.md`、`docs/architecture/rddf-layout.md`（副本收敛）、`_lib/adr_index_generator.py`（`--check` 分支）、`tests/integration/test_v4_doc_drift_contracts.bats`（守卫扩展）
- **回归风险**：中 —— 守卫扩展可能一次暴露既有残留，故设「先 warn 后 block」纪律
- **前置依赖**：无。**但** P2-1 的 `--check` 分支会改 `adr_index_generator.py`，与 `fix-adr-index-generator-dup` 同文件 ⇒ 建议在其之后
- **估算**：断链检查器 ~2 小时；两节文档 ~1 小时；守卫扩展 + 残留清理 ~2 小时；双落点收敛 ~30 分钟

## 审稿记录

**metis 第 1 轮（2026-11-17）**：

| finding | 处置 |
|---|---|
| 「P1-7 需要 spec delta，与其余 10 条 AC 生命周期不同 ⇒ 混在一条 change 里，archive gate 会要求整条 change 有 spec delta，而 10 条不产生 ⇒ 永远 archive 不干净」 | ✅ **采纳**：P1-7 拆出为 `fix-spec-v3-naming-sync` |
| 「AC #6 要求 `openspec/specs/` 零命中 = 223 处 / 48 份文件，比 P1-7 的描述大两个数量级；且与 AC #5（仅 skill-role-model）互斥」 | ✅ **采纳（实测 48 份，确认）**：AC #6 删除；守卫扩展范围限 `docs/architecture/**` + `skills/**` |
| 「item 8 压掉 `skills/rdd-verifier/SKILL.md:448-458` 等于撤销 P1-2 的整改理由（那是声明层不是副本层）」 | ✅ **采纳**：Out of Scope 显式排除；item 7 只动 `rddf-layout.md` |
| 「AC #11『不修改任何 .py 行为』与 P2-1（把散文段交给生成器）冲突」 | ✅ **采纳**：P2-1 改为 `--check` 只读校验（不接管生成），AC 末条限定为「不改变默认输出」 |
| 「AC #8『手写版本号数量较本项开始时下降』无基线定义、正则误命中 ADR 编号/端口」 | ✅ **采纳**：改为产出清单 + 「残留为 0 或逐项标注派生来源」 |
| 「AC #10『删掉双落点表一行 ⇒ 至少一条断言变红』极易随排版误红，应改语义级」 | ✅ **采纳**：改为三段语义齐备（记账落点/产品落点/为什么不在 owns 里）|
| 「`check_md_links.py` 缺『扫到 0 链接 ⇒ 红』，且本轮断链实际跨出 `docs/`（指 `.rddf/improvements/`）」 | ✅ **采纳**：AC 加扫描下限 + `SCAN_ROOTS` 显式清单 |
| 「三条都写『bats 在 CI 可见』，但本仓有 skip-not-fail 先例 ⇒ 要断言实际执行非 skip」 | ✅ **采纳**：AC 改为「实际执行（skip 不算通过）」|
| 「缺『守卫本身不能是假保证』类 AC（本仓两次教训）」 | ✅ 采纳：每条新守卫都配变异验证；交叉引用守卫同样配 |
| 「item 2/3 在增加内容、item 8 在删除内容，方向相反且无详略原则」 | ✅ 采纳：立原则 —— **声明层详写，副本层只留指针**；并在 Out of Scope 写明哪些不删 |
