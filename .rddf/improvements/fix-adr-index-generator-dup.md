---
优先级: P1
priority: P1
来源: 2026-11-17 文档审查实跑中踩到（.rddf/reviews/adr-0060-amendment-2026-11-17.md §五）——
  仓内有两个 ADR 索引生成器且格式分歧，误用其一会在不报错的情况下破坏 README 索引块；
  配套测试验的不是仓内实现；且被误用的那个生成器 docstring 里印着一条**指向不存在路径的复现命令**
阶段: phase-2
分类: bugfix
类型: bugfix
状态: draft

生成时间: 2026-11-17
roadmap_ref:
---

# fix-adr-index-generator-dup

**主题**: 单一真源

> **本项必须在 `fix-adr-shape-debt-convergence` 之前完成**：它先立「唯一生成器 + 标记计数 + 列数」
> 三条不变量，后者的 `status_class` 改动与索引重建都在该不变量保护下。

## 架构依据

### 缺陷一：两个生成器，格式分歧，且互不报错

| 实现 | 行数 | 列 | 状态取值 | 对 README 标记的处理 |
|---|---|---|---|---|
| `_lib/adr_index_generator.py` | 109 | 4 列（ADR / 标题 / **状态** / **日期**） | 从 Status 行透传（`已采纳 + AMENDED (2026-11-17)` 原样保留） | 只重写 `<!-- ADR_INDEX_START/END -->` 之间，标记保留 |
| `_lib/sync_adr_index.py` | **142** | 3 列（ADR / 标题 / 状态） | 一律落成 `待定` | **删掉** `<!-- ADR_INDEX_START/END -->` 标记 |

两者都在仓内（`_lib/` 下），都带 `__main__`，都能直接跑。README 实际用的是前者
（`tests/unit/test_adr_index_gate.py` 按它断言）。

**「状态一律待定」的根因**：`sync_adr_index.py` 认 `## Status` **标题**格式（`:31-32`），
而本仓 60 份 ADR 用的是 `> **状态**: …` **引用块**格式 ⇒ 一律解析失败 ⇒ 落成 `待定`。
`adr_index_generator.py` 的 `_META_PATTERN` 认引用块 ⇒ 正确。

**2026-11-17 的实际后果**：误调 `sync_adr_index` 后，`docs/adr/README.md` 的索引从
「4 列含日期」退化成「3 列全部 `待定`」，同时 `ADR_INDEX_START/END` 标记被删除。
是 `test_adr_index_gate.py` 的逐字节断言救回来的（4 passed → 2 failed），**脚本自己没有报任何错**。
若那天没有这条测试，3 列表格渲染完全合法，会以「看起来正常」的形态被提交。

### 缺陷二：测试验的不是仓内实现（且有一条僵尸断言）

`tests/unit/test_sync_adr_index.py` 导入 `skills._lib.sync_adr_index`：

```bash
$ ls skills/_lib/sync_adr_index.py
ls: cannot access 'skills/_lib/sync_adr_index.py': No such file or directory
$ python3 -m pytest tests/unit/test_sync_adr_index.py -q
4 passed
```

它通过，是因为 `skills/_lib/` 的 `__path__` 回落到全局安装副本（`~/.agents/skills/_lib/`）——
**而那个副本是不是仓内 `_lib/sync_adr_index.py` 的等价物，没有人验过**。于是：

- 在任何装了全局副本的机器上该测试恒绿，**包括仓内实现完全坏掉的情况**；
- 在没装全局副本的干净 CI 上它红 —— 但红的原因是「找不到全局副本」，与仓内代码无关。

4 个用例里还有一个真·僵尸：

| 用例 | 问题 |
|---|---|
| `test_extract_adr_metadata` | 验全局副本 |
| `test_generate_table` | 验全局副本 |
| `test_sync_dry_run` | 验全局副本（**且它 dry_run 的对象是全局副本的路径解析**） |
| `test_finds_all_adrs` | **僵尸**：`import extract_adr_metadata` 后从不调用，只数 `ADR-*.md` 个数 ≥23。删掉整个 `sync_adr_index` 后它仍然绿 |

### 缺陷三：docstring 里印着一条指向不存在路径的复现命令

`_lib/sync_adr_index.py` 的 docstring（`:8`）写着：

```
python3 skills/_lib/sync_adr_index.py
```

而 `skills/_lib/sync_adr_index.py` **不存在**。任何人照抄这条命令会得到
`No such file`；若他把路径「修对」成 `_lib/sync_adr_index.py`，就会**成功复现上面那次索引破坏**。

这条误导指令比「两个生成器并存」更直接 —— 它是事故的复现脚本。

### 为什么是 P1

三个缺陷都在 ADR 索引这条路径上，而索引是：`docs/adr/README.md` 的唯一机读入口
（`test_adr_index_gate.py` 依赖它）、每次新增 ADR 都要重建一次的高频操作、
一旦误用破坏是**静默**的（表格渲染合法）。高频 + 静默破坏 + 守卫自身不可信，三项叠加。

## 范围

**In Scope**：
- 删除 `_lib/sync_adr_index.py`（142 行，唯一消费者是 `test_sync_adr_index.py` 与它自己的 `__main__`；
  `_lib/cli/` 无引用 —— 已核实）
- 重写 `tests/unit/test_sync_adr_index.py`：把仍有价值的断言迁到 `test_adr_index_generator.py`，删除僵尸
- 加守卫：标记计数、列数、被测模块位置、行数配套计数
- 修 `docs/adr/README.md`：写明索引块只能由 `_lib/adr_index_generator.py` 重建 + 具体命令

**Out of Scope**：
- `test_adr_index_gate.py` 里 `if len(cells) < 4: continue` 的洞**要修**（见 What Changes #3），
  但**不改** `render_table` 的列结构
- 状态词表分类（`status_class`）属 `fix-adr-shape-debt-convergence` P2-5
- README 散文段纳入生成（属 `fix-doc-drift-residual` P2-1）
- `skills._lib.*` 回落到全局副本的**全面**治理（100+ 导入点）—— 本项只修 `sync_adr_index` 这一实例，
  通用治理另立一项

## Why

索引重建是高频操作，破坏静默，而守卫自己验错了对象（验全局副本）+ 有一条 continue 洞
（3 列表格的行被跳过）。三个问题叠在一起，意味着**当前这条路径上没有任何一层是可信的**：

- 想用生成器 → 有两个，选错会静默破坏
- 想看测试保不保险 → 测试验的是全局副本，不看仓内
- 想看断言严不严 → `if len(cells) < 4: continue` 把 3 列退化整行跳过

本项的目标是让误用**无法静默发生**：另一个入口不存在，测试验仓内实现，断言没有跳过分支。

## What Changes

1. **删除 `_lib/sync_adr_index.py`**：`git rm`。删前确认 `_lib/cli/` 零引用（已核实）+
   `grep -rn "sync_adr_index" --include=*.sh --include=*.py --include=*.bats` 的其余命中逐个处理。
2. **迁移测试**：`tests/unit/test_sync_adr_index.py` 里真正有价值的断言（`extract_adr_metadata` 返回
   number/filename/title、`render_table` 表头、全量 ADR 发现）迁到 `test_adr_index_generator.py`
   （若已有等价断言则直接删除并注明「已由 X 覆盖」）。**`test_finds_all_adrs` 直接删**（僵尸）。
   全文件删除后，`skills._lib.sync_adr_index` 的回落路径也随之消失。
3. **修 `test_adr_index_gate.py` 的 continue 洞**：`test_readme_index_rows_have_status_and_date` 当前
   `if len(cells) < 4: continue` ⇒ 3 列表格的行整行跳过。改为：列数不符直接计入 `bad`，
   并新增配套计数断言「参与检查的行数 == 索引块内的 ADR 行数」（防任何形式的静默跳过）。
4. **守卫加固**（`test_adr_index_gate.py` + `tests/integration/test_adr_index.bats`）：
   - 标记计数：`ADR_INDEX_START` / `ADR_INDEX_END` 各恰好 1 次
   - 列数：索引表头必须是 `| ADR | 标题 | 状态 | 日期 |`（4 列）
   - 被测模块位置：`_lib.adr_index_generator` 的 `__file__` 必须在 `PROJECT_ROOT` 内（防回落）
   - 逐字节相等（已有，保留）
5. **修 docstring 误导命令**：`_lib/adr_index_generator.py` 的 docstring 若含路径命令，必须是可执行的
   （`python3 _lib/adr_index_generator.py`）；在 `docs/adr/README.md` 新增「索引维护」小节写明唯一命令。
6. **删除可逆性**：删文件前先落一份变更说明进该 ADR README 小节或 commit message（记录删了什么、
   为什么、原格式差异），使这次删除可被未来考古。

## Acceptance

- [ ] `ls _lib/sync_adr_index.py skills/_lib/sync_adr_index.py` ⇒ 两者都不存在
- [ ] `grep -rn "sync_adr_index" --include=*.py --include=*.sh --include=*.bats --include=*.md .` 的命中**仅**剩显式允许清单：`openspec/changes/archive/2026-07-24-auto-sync-adr-index/{proposal,design}.md`（历史 change，不改）+ 本次 commit message。其余零命中
- [ ] `grep -rn "skills/_lib/sync_adr_index\|python3 skills/_lib" _lib/ skills/ docs/ --include=*.py --include=*.md` 零命中（误导命令已清）
- [ ] `python3 -m pytest tests/unit/test_adr_index_gate.py tests/unit/test_adr_index_generator.py -q` 全绿
- [ ] **回落守卫**：`python3 -c "import sys;sys.path.insert(0,'.');import _lib.adr_index_generator as m,pathlib;assert pathlib.Path(m.__file__).resolve().is_relative_to(pathlib.Path('.').resolve()), m.__file__"` ⇒ 通过。变异验证：`mv _lib/adr_index_generator.py /tmp/x` ⇒ 相关测试红（不是回落到全局副本变绿）
- [ ] **标记计数**：`python3 -c "t=open('docs/adr/README.md').read();assert t.count('<!-- ADR_INDEX_START -->')==1 and t.count('<!-- ADR_INDEX_END -->')==1"`
- [ ] **列数守卫**：`grep -c "^| ADR | 标题 | 状态 | 日期 |$" docs/adr/README.md` = 1；`grep -c "^| ADR | 标题 | 状态 |$" docs/adr/README.md` = 0。变异验证：把表头改成 3 列 ⇒ `test_readme_index_rows_have_status_and_date` 与列数守卫**都**要红（不停留在 continue 跳过）
- [ ] **无 continue 洞**：`grep -c "if len(cells) < 4:" tests/unit/test_adr_index_gate.py` = 0；且该测试有「参与检查行数 == ADR 行数」的配套计数断言（变异验证：删掉索引块里的一行 ⇒ 红）
- [ ] 逐字节相等仍有效：`python3 _lib/adr_index_generator.py > /tmp/idx.md` 与 README 索引块 `diff` 为空
- [ ] `docs/adr/README.md` 含「索引维护」小节，写明唯一生成器与可执行命令
- [ ] `bats tests/integration/test_adr_index.bats tests/integration/test_adr_directory.bats` 全绿

## Capabilities

- 维护者：重建索引只有一条命令，且误用另一个入口已被物理删除（不存在第二个入口）
- CI：索引相关测试不再有「验全局副本」的假绿，也没有 continue 静默跳过
- 未来维护者：docstring 里不再有指向不存在路径的命令，事故无法按原脚本复现

## Impact

- **受影响文件**：`_lib/sync_adr_index.py`（删除，142 行）、`tests/unit/test_sync_adr_index.py`（删除或重写）、`tests/unit/test_adr_index_gate.py`（修 continue 洞 + 3 条新断言）、`tests/unit/test_adr_index_generator.py`（接收迁移的断言）、`tests/integration/test_adr_index.bats`（标记/列数）、`_lib/adr_index_generator.py`（docstring）、`docs/adr/README.md`（索引维护小节）
- **回归风险**：低 —— 只删一个无产线消费者的脚本 + 加强测试；但删文件属不可逆动作，故 What Changes #6 要求记录删除理由
- **前置依赖**：无。**下游**：`fix-adr-shape-debt-convergence` 依赖本项完成（先立不变量）
- **估算**：~2 小时（含变异验证）

## 审稿记录

**metis 第 1 轮（2026-11-17）**：

| finding | 处置 |
|---|---|
| 「事实前提错了：`_lib/sync_adr_index.py` 在仓内（142 行），只有 `skills/_lib/` 下的不存在」 | ✅ **采纳（我的取证路径错误）**：本稿已全面修正 In Scope —— 从「清理引用」改为「删除 142 行活代码」，并在架构依据里列出两者的列数/状态/标记差异 |
| 「docstring 第 8 行印着 `python3 skills/_lib/sync_adr_index.py`，这正是本次事故的复现脚本，草稿没点出来」 | ✅ 采纳：新增「缺陷三」整节 + What Changes #5 + AC 第 3 条 |
| 「`test_finds_all_adrs` 是僵尸断言（import 后不调用），删掉 sync_adr_index 后仍绿」 | ✅ 采纳：What Changes #2 点名直接删 + 架构依据列 4 个用例逐个定性 |
| 「`test_adr_index_gate.py:55-71` 有 `if len(cells) < 4: continue`，3 列退化会被静默跳过」 | ✅ 采纳（已核实该行存在）：What Changes #3 修洞 + AC 要求「参与检查行数 == ADR 行数」配套计数 |
| 「AC #1『命中只剩历史说明类』无机读定义」 | ✅ 采纳：改为显式允许清单（`openspec/changes/archive/2026-07-24-auto-sync-adr-index/{proposal,design}.md`）+ 其余零命中 |
| 「『为什么是 P1 而不是 P2』整段是说服性文字」 | ✅ 采纳：压成一段，删掉三条理由式列举 |
| 「`skills._lib` 回落是通用缺陷（100+ 导入点），只有 `sync_adr_index` 当前踩中 —— 若要覆盖全部模块另立一条，不要在这条扩 scope」 | ✅ 采纳：Out of Scope 显式排除，AC 只验 `adr_index_generator` 一个模块的位置 |
