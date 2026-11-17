---
优先级: P1
priority: P1
来源: 2026-11-17 第八批 5 项归档过程发现（follow-up C/D 合并）——回归基线被测试中途清空导致
  「新增失败」统计失真（4 次）；另有 1 条僵尸断言红了 7 周而基线注释谎称其通过
阶段: phase-2
分类: bugfix
类型: bugfix
状态: draft（部分已就地修复，见「实施状态」）

生成时间: 2026-11-17
roadmap_ref:
---

> **⚠ 部分已就地修复（2026-11-17，commit 9ec8f22 + b0bf0ec + d322c39）**
> 本项立项后被一次文档审查的回归门实跑撞上并当场修掉了一部分。**本项仍然有效**，
> 剩余范围见文末「实施状态」段 —— 立项时请以那里的「未做」清单为准，不要按原 AC 全量重做。

# fix-regression-baseline-integrity

**主题**: 阶段步骤化执行

## 架构依据

### 缺陷一：回归基线在跑回归的过程中被改写

回归基线 `tests/KNOWN_FAILURES.txt` 被三个脚本以**硬编码路径**读取：

| 脚本 | 行 | 行为 |
|---|---|---|
| `tests/scripts/report_regression.sh` | `:28` | `BASELINE="$REPO_ROOT/tests/KNOWN_FAILURES.txt"`（**无覆盖点**；`:55` 只把 `BASELINE_PATH` 传给内部 Python 比较器） |
| `tests/scripts/refresh_known_failures.sh` | `:40` | 同上（**无覆盖点**） |
| `skills/execute/scripts/run_regression_gate.sh` | `:21` | `if [ -f "$REPO_ROOT/tests/KNOWN_FAILURES.txt" ]` ⇒ 决定走 baseline 对比分支还是 `bats tests/ --recursive` 回退分支（**判定也不认覆盖路径**） |

而**两个测试文件直接对着真实基线文件写**：

| 文件 | 行为 |
|---|---|
| `tests/integration/test_known_failures_baseline.bats` | `:8` 持有真实路径；5 个用例各自 `printf ... > "$BASELINE"` 覆盖它；teardown（`:22-28`）事后还原 |
| `tests/integration/test_execute_regression_gate.bats` | `:8` 持有真实路径；覆盖它，**并两次 `rm -f "$BASELINE"`**（比覆盖更狠：比较器会走 `report_regression.sh:32-35` 的 exit 2 分支） |

对照 `tests/integration/test_regression_baseline_shrink_only.bats:11-12` 用 `$BATS_TMPDIR` —— 那是**正确写法**。前两个文件是同一个反模式的复制粘贴（连变量名 `ORIGINAL_BASELINE` 都一样）。

**触发机制（metis 第 1 轮纠正过一次，此处为核实后的事实）**：
不是「比较器与测试并发读写」—— `report_regression.sh:39` 先把收集跑完，`:55` 才读 baseline，读取发生在收集**之后**。
真正的原因是 **`tests/scripts/collect_bats_failures.sh:48` 的单文件超时**：

```bash
OUTPUT_LINE=$(timeout "$PER_FILE_TIMEOUT" bats "$f" 2>&1)     # PER_FILE_TIMEOUT 默认 30
```

单文件超过 30s 被 kill ⇒ **teardown 不执行** ⇒ 那个文件写进真实基线的 fixture 内容**永久留在磁盘上**。
而上面那两个文件恰好是最容易撞 30s 的两个（各自嵌套跑「全量 integration 收集」，单次约 280 个子进程；`test_arch_env_check_extraction.bats` 还两次 `cp -r "$REPO_ROOT"`）⇒ **4 次偶发命中 + 跑完基线仍是脏的**。

⇒ 修复方向不变（让测试不再写真实文件），但**诊断必须写对**：不是加锁，而是**去掉对 teardown 的依赖**。

**实测（本批 4 次）**：

| 时间 | 现象 |
|---|---|
| 2026-11-16（第 2 项） | 「已知 11 / 新增 0」正常 |
| 2026-11-17（第 4 项第 1 轮） | 「已知 0 / 新增 10」—— 10 条全部在主仓复现，人工逐条归属才确认零回归 |
| 2026-11-17（第 4 项第 3 轮） | 「已知 0 / 新增 11」 |
| 2026-11-17（第 5 项） | 「已知 0 / 新增 11」 |

代价：每次全量回归的「新增失败」清单都不可用，零回归判定退化成**人工逐条比对**（本批累计 3 轮 × 10~11 条，约 30 分钟/轮）。

**二阶风险**：基线被 fixture 覆盖后只剩 1 行，而 CI 的 shrink-only 门（`test.yml:121-134`）**只禁止增长** ⇒ 脏基线可以被静默提交，提交后「已知失败」永久为 0。

### 缺陷二：一条僵尸断言红了 7 周，基线注释还宣称它通过

`tests/integration/test_arch_env_check_extraction.bats:58-64`：

```bash
@test "run_arch_env_check_discovers_counts" {
  output=$(... run_arch_env_check ...)
  echo "$output" | grep -q '现有 ADR'
  echo "$output" | grep -q 'Roadmap'
  echo "$output" | grep -q '架构差距分析'      # ← 指向已删除的输出
  echo "$output" | grep -q '活动 changes'
}
```

`架构差距分析` 这行输出在 **2026-09-30** 被 `9acfb09 fix(rdd-arch): gap-analysis protocol removal per ADR-0057` **有意删除** —— ADR-0057 的标题即「rdd-arch 简化为 ADR + theme doc 双工件；**删除 gap-analysis 协议**」，理由是 YAGNI（运行 6 个月后三条证据）。现行输出（`skills/rdd-arch/scripts/arch_env_check.sh:109-119`）是：

```
📋 现有 ADR: N     📋 Roadmap: …     📋 主题架构文档: N     📋 活动 changes: N
```

⇒ **该断言是测试陈旧，不是产品回归** —— 正确处置是**修测试**（改断言 + 同步文件头注释 `:14` 的 “gap/change counts”），**不是**把用例重新登记进 baseline。（ADR-0057 自己的「待更新测试清单」只列了 `test_arch_audit_check.py` / `test_arch_quality_gate.py`，漏了这个文件。）

**更糟的是 `tests/KNOWN_FAILURES.txt:82` 的注释**：

```
#   - "run_arch_env_check_discovers_counts" → passes (arch env-check output drift resolved)
```

即基线在 2026-11-04 refresh 时**认为它已修好并从登记中移除**，而它其实一直是红的 —— 这正是同文件 `:84-88` 警告的那件事的反向版本：**它把一个仍在失败的用例标成了已修好**。

## 范围

- **In Scope**：① 给 `report_regression.sh` / `refresh_known_failures.sh` / `run_regression_gate.sh` 增加 baseline 路径的环境变量覆盖（默认仍是仓库路径）；② **两个**写真实基线的测试文件改为在临时副本上运行，并加运行期守卫；③ 修正僵尸断言 + 该文件头注释 + 基线第 82 行失效注释；④ 可观测性：比较器打印解析后的 baseline 路径。
- **Out Scope**：不改基线的**登记内容**本身（哪些用例算已知失败，仍由 `refresh_known_failures.sh` 决定）；不改 `report_regression.sh` 的**判定逻辑**（只改「读哪个文件」与「打印哪个路径」）；不改三个 baseline 解析器之间的**归一化不一致**（`report_regression.sh:73-74` 的 `rsplit " # "` vs `refresh_known_failures.sh:88` 的 `sed 's/[[:space:]]+#.*$//'` vs `_lib/cli/regression_diff_cmd.py:13`）—— 另开提案；不改 `collect_bats_failures.sh` 的 30s 超时策略（另议）；不改 `test_regression_baseline_shrink_only.bats` 等既有基线契约测试；**本 change 内不得对真实基线执行 `refresh_known_failures.sh`**（归一化不一致 ⇒ 可能注入重复条目）。

## Why

回归门是这套工作流的**唯一自动化安全网**。安全网自己失真时，「全绿」和「有新增失败」都不再可信 —— 本批 3 轮回归的判定因此退化成人工比对，而人工比对恰恰是最容易放过真回归的环节。

metis 指出草稿漏掉的一层：**「已知失败 0」会让人误以为「没有已知失败」**，从而把真实回归当成已知问题放行 —— 这比「统计失真」严重，是**放行真回归**的风险。

缺陷二则是安全网自己失明的实例：一条 7 周的红用例被基线注释宣称为已修好，任何人读基线都会得出错误结论。

两条缺陷同源：**「基线」这个单一事实源被多方无保护地读写**。

## What Changes

1. **路径覆盖**（三个脚本）：
   - `tests/scripts/report_regression.sh:28`、`tests/scripts/refresh_known_failures.sh:40` ⇒
     `BASELINE="${RDDF_KNOWN_FAILURES_FILE:-$REPO_ROOT/tests/KNOWN_FAILURES.txt}"`（默认逐字不变）；
   - `skills/execute/scripts/run_regression_gate.sh:21` 的 `-f` 判定**也认覆盖路径**（否则接口半吊子：读哪个文件可覆盖、要不要用 baseline 不可覆盖）；
   - 环境变量说明写进 `refresh_known_failures.sh` **头部第 2~30 行窗口内**（`--help` 是 `sed -n '2,30p' "$0"`，`refresh_known_failures.sh:56`）⇒ 否则新变量等于不存在；同步 `tests/README.md` 与 `report_regression.sh` 头注释。
2. **两个测试文件改为在副本上运行**（`test_known_failures_baseline.bats` + `test_execute_regression_gate.bats`），每处两件事：
   (a) 文件内的 `BASELINE=` **重指** `$BATS_TEST_TMPDIR/known-failures.txt`（否则用例体内 `grep -Fq ... "$BASELINE"` 之类的断言读的仍是真实文件，AC 自我矛盾）；
   (b) `export RDDF_KNOWN_FAILURES_FILE=<同一路径>` 供被调子脚本使用。
3. **运行期守卫（不是独立用例）**：守卫必须放在 **`setup()`（写入前算 hash）+ `teardown()`（无条件比对，不一致即 fail）**。
   ⚠ 写成「跑完该测试后另起一个用例断言 sha256 一致」是**零判别力**的 —— 独立用例观察不到别的用例的中途写入。
   断言对象用**绝对路径** `$REPO_ROOT/tests/KNOWN_FAILURES.txt`（避免 `export` 泄漏进嵌套子进程时被间接影响）。
4. **确定性复现测试**（取代「已知失败数 > 0」这种采样式判据）：
   在临时副本上 —— 先 `cp` 真实基线到 tmp、`export RDDF_KNOWN_FAILURES_FILE=$tmp`、**中途把 tmp 内容替换成单条 fixture**（模拟「另一个写者」/「teardown 被 kill」）、再跑 `report_regression.sh` ⇒ 断言「已知失败 == tmp 里当时仍失败的条目数」「新增失败 == 0」「**真实文件 hash 不变**」。
   这条同时证明「读的确实是覆盖路径」与「真实文件不被写」。
5. **仓库级卫生检查**：跑完 `bats tests/integration/` 后 `git status --porcelain tests/KNOWN_FAILURES.txt` 必须为空（比源码 grep 强，且能顺带抓到漏网的文件）。
6. **僵尸断言修正**（`tests/integration/test_arch_env_check_extraction.bats`）：
   - 把 `grep -q '架构差距分析'` 换成 `grep -q '主题架构文档'`（`arch_env_check.sh:111` 的现行输出行；**不**用 `工件发现 (ADR-0016)` —— 它已被同文件 `:70` 的用例断言，换过去等于没新增约束）；
   - 同步该文件头注释 `:14` 的 “7. Helper prints ADR/roadmap/**gap**/change counts”；
   - 注释里注明依据：ADR-0057 删除了 gap-analysis 协议（YAGNI），现行输出为 ADR + theme doc 双工件。
   ⇒ `grep -rn '架构差距分析' tests/` 应零命中。
7. **基线注释修正**（`tests/KNOWN_FAILURES.txt:82`）：删除或改写「→ passes」的失效声明。
8. **可观测性**：`report_regression.sh` **打印解析后的 baseline 路径**；baseline 缺失时的报错（`:32-35`）打印**覆盖后**的路径而非常量拼接路径（否则排查会走错方向）。
9. **最小守卫（shrink-only 盲点）**：CI 的 shrink-only 门只禁增长 ⇒ 脏基线（塌成 1 行 fixture）能被静默提交。补一条最小断言：基线**不得**塌成只有一行 fixture 形态（`grep -c '^known failure: baseline fixture' == 0`）。更完整的「基线完整性」检查（条目数下限、格式校验）可另开 follow-up。
10. **默认路径逐字不变**：无 env 时 `bash tests/scripts/report_regression.sh` 的输出与改动前**逐字节 diff 为空**（不是「行为不变」这种不可判的说法）；`refresh_known_failures.sh --dry-run --scope <单文件>` 同理。

## Acceptance

- [x] `report_regression.sh` / `refresh_known_failures.sh` / `run_regression_gate.sh` 三者都认 `RDDF_KNOWN_FAILURES_FILE`；不设该变量时**输出逐字节不变**（diff 为空，不只是「行为不变」）
- [ ] `RDDF_KNOWN_FAILURES_FILE` 在仓库内**零冲突**（`grep -rn 'RDDF_KNOWN_FAILURES_FILE'` 在改动前零命中，实施后只出现在预期的位置）
- [ ] 环境变量说明写在 `refresh_known_failures.sh` 头部第 2~30 行窗口内（`--help` 可见）+ `tests/README.md` + `report_regression.sh` 头注释
- [x] `test_known_failures_baseline.bats` 与 `test_execute_regression_gate.bats` **两个文件**都在临时副本上运行（文件内 `BASELINE` 重指副本 **且** 导出 env），不再 `printf >` / `rm -f` 真实基线
- [x] 运行期守卫放在 `setup()` + `teardown()`（非独立用例）；断言对象是绝对路径 `$REPO_ROOT/tests/KNOWN_FAILURES.txt` 的 hash
- [ ] 确定性复现测试：tmp 副本中途被替换成 fixture ⇒ 「已知失败 == tmp 当时仍失败的条目数」「新增失败 == 0」「真实文件 hash 不变」
- [x] 仓库级卫生：`bats tests/integration/` 跑完后 `git status --porcelain tests/KNOWN_FAILURES.txt` 为空
- [ ] `report_regression.sh` **在基线缺失时**的报错打印**覆盖后的路径**（已实现）；成功路径**不打印** baseline 路径 —— 与上一条「不设该变量时输出逐字节不变」冲突，已裁定以上一条为准（输出格式是既有消费者契约，诊断性打印不得改动默认输出）
- [ ] `test_arch_env_check_extraction.bats` 的断言改为 `主题架构文档`（不再用已被同文件覆盖的 `工件发现 (ADR-0016)`），文件头注释同步，注释注明 ADR-0057 依据
- [ ] `grep -rn '架构差距分析' tests/` 零命中
- [ ] `tests/KNOWN_FAILURES.txt` 中「`run_arch_env_check_discovers_counts` → passes」的失效声明被修正
- [x] 最小守卫：基线不得塌成只有一行 fixture 形态（shrink-only CI 盲点）
- [ ] `./test.sh --unit` 全绿 + `bats tests/integration/test_known_failures_baseline.bats` + `bats tests/integration/test_execute_regression_gate.bats` + `bats tests/integration/test_regression_baseline_shrink_only.bats` + `bats tests/integration/test_arch_env_check_extraction.bats` 全绿
- [x] **本 change 内未对真实基线执行过 `refresh_known_failures.sh`**（归一化不一致，见 baseline `:84-88`）

## Capabilities

- 回归结论重新可信：「新增失败」不再依赖人工逐条比对
- 「已知失败 0」不再被误读成「没有已知失败」⇒ 真回归不会被当成已知问题放行
- 基线文件**只被 refresh 流程写**，测试与比较器不再写它
- 僵尸断言与失效注释被清理，基线注释不再宣称未证实的结论
- 脏基线塌成 1 行时会被最小守卫拦住，不再能借 shrink-only 门静默提交

## Impact

- **影响面**：`tests/scripts/report_regression.sh`、`tests/scripts/refresh_known_failures.sh`、`skills/execute/scripts/run_regression_gate.sh`（各 1~2 行 + 注释/帮助文本）、`tests/integration/test_known_failures_baseline.bats`、`tests/integration/test_execute_regression_gate.bats`（隔离改造 + `setup`/`teardown` 守卫）、`tests/integration/test_arch_env_check_extraction.bats`（1 条断言 + 1 行头注释）、`tests/KNOWN_FAILURES.txt`（1 行注释）、`tests/README.md`。
- **风险**：
  - 环境变量若与既有 CI 变量撞名 ⇒ 已在 AC 中固化为「改动前零命中」的验证项；
  - 覆盖路径指向目录/无读权限时 Python 会抛 `IsADirectoryError`/`PermissionError` ⇒ 退出码非 0/1 会被 `report_regression.sh:121-124` 归为 internal error 但不提示是 env 的锅 ⇒ 可接受（实施时若顺手，加一句 env 相关的错误提示）；
  - `export` 会传进嵌套子进程（`test_execute_regression_gate.bats` 会调 `run_regression_gate.sh` → `report_regression.sh` → `collect_bats_failures.sh` → 另一层 bats）⇒ 守卫已改为对**绝对路径**取 hash，不受该泄漏影响。
- **兼容性**：默认路径不变 ⇒ 现有调用方（`./test.sh --bats --regression`、CI）无需改动。
- **副作用预期**：修好之后，全量回归会重新显示真实的「已知失败」条数（当前有效登记 **11** 条）⇒ **某些历史运行的「新增失败」结论需要重新审视**（本批已逐条人工归属，结论为零回归）。
- **后续（不塞进本 change）**：① 三个 baseline 解析器的归一化不一致（应统一到一处「单一事实源」，反证是 `_lib/cli/regression_diff_cmd.py:13` 的第三份实现）；② `collect_bats_failures.sh` 的 30s 单文件超时（慢文件被 kill ⇒ teardown 不跑，是本缺陷的**放大器**，也是其它测试污染的通用成因）；③ 审计「还有哪些测试直接写 `$REPO_ROOT` 下的 tracked 文件」，并考虑给 `rdd-doctor` 加一个 category。

## 审稿记录

metis 1 轮（2026-11-17）。逐条处置：

- **采纳 P0-1（漏了第二个写真实基线的测试文件）**：原草稿只点名 `test_known_failures_baseline.bats`；实测 `tests/integration/test_execute_regression_gate.bats:8` 持有同一真实路径、覆盖它并**两次 `rm -f`** ⇒ 只修一个文件时「跑完后真实基线逐字节一致」这条 AC **根本不可能成立**。已把它加入 In Scope / Impact / AC。
- **采纳 P0-2（守卫写法零判别力）**：原草稿把 sha256 守卫写成「新增一个独立用例，跑完后断言一致」—— bats 的独立用例观察不到别的用例的中途写入 ⇒ 该用例无论隔离是否生效都会通过。已改为守卫放在 **`setup()`（写前快照）+ `teardown()`（无条件比对）**，且断言对象用**绝对路径**（避免 `export` 泄漏进嵌套子进程时被间接影响）。
- **采纳 P0-3（AC「已知失败 > 0」不可判定）**：该判据是「对环境现状的采样」而非「对修复的检验」（将来这些已知失败全被修好时它会自然变成 0）。已替换为**确定性复现测试**（tmp 副本中途被替换成 fixture ⇒ 「已知失败 == tmp 当时仍失败的条目数」「新增失败 == 0」「真实文件 hash 不变」）+ **仓库级卫生检查**（`bats tests/integration/` 后 `git status --porcelain tests/KNOWN_FAILURES.txt` 为空）。
- **采纳 P0-4（触发机制诊断写错了）**：原草稿断言「比较器与测试并发读写」，但 `report_regression.sh:39` 先收集、`:55` 才读 baseline ⇒ 并非并发。真正机制是 `collect_bats_failures.sh:48` 的 `timeout 30` 把慢文件 kill 掉 ⇒ **teardown 不执行** ⇒ fixture 内容永久留在真实基线上。已改写「架构依据」的机制描述，并加 AC「修复不依赖 teardown」。
- **采纳 P0-5（修测试还是登记回 baseline）**：原草稿没写依据。已引 ADR-0057（标题即「删除 gap-analysis 协议」，理由为 YAGNI）+ `arch_env_check.sh:109-119` 的现行输出 ⇒ 结论是**测试陈旧、应修测试**，不是产品回归。
- **采纳 P1-6（删除不可实现的源码 grep 守卫）**：原 AC「断言 `KNOWN_FAILURES` 不出现在测试的写入路径里」既不可实现（setup 必须从真实路径 `cp`）又必然误报。已删除，替换为运行期证据。
- **采纳 P1-7（替换断言选错字符串）**：原草稿用 `工件发现 (ADR-0016)` 替换 `架构差距分析`，但该串已被同文件 `:70` 的用例断言 ⇒ 等于没新增约束。已改为 `主题架构文档`（`arch_env_check.sh:111`）。
- **采纳 P1-8（可观测性）**：已加 AC「`report_regression.sh` 打印解析后的 baseline 路径；缺失时打印覆盖后的路径」+「env 说明写进 `refresh_known_failures.sh` 头部第 2~30 行窗口内（`--help` 可见）」+ `tests/README.md` 同步。
- **采纳 P1-9（`run_regression_gate.sh` 的判定）**：原草稿只当「风险」留白。已改为**明确纳入**（它的 `-f` 判定也认覆盖路径，否则接口半吊子）。
- **采纳 P2-11（数字写错）**：原 Impact 写「14 条有效登记」，实测是 **11** 条（`:62-72`）。已更正。
- **采纳 P2-12（禁止在本 change 内 refresh 真实基线）**：三个解析器的归一化不一致（`rsplit " # "` vs `sed 's/[[:space:]]+#.*$//'` vs `split(" #")`）⇒ 一次 refresh 就可能注入重复条目。已写入 Out Scope 的显式禁令。
- **采纳 P2-13（shrink-only 盲点）**：脏基线塌成 1 行属「缩小」⇒ CI 放行 ⇒ 已加最小守卫 AC（基线不得塌成只有一行 fixture 形态）。
- **采纳 P1（AC 二分与「已知失败 0」的误读风险）**：已把「统计失真」与「**让人误以为没有已知失败 ⇒ 把真回归当已知问题放行**」分开写明（后者是更严重的风险）。
- **记录未采纳**：metis 建议把「守卫写成 `setup_file`/`teardown_file`」—— 本项采用 `setup()`/`teardown()`（`BATS_TEST_TMPDIR` 是 per-test，`setup_file` 会把「单副本被多个用例串改」带进来）。

---

## 实施状态（2026-11-17 就地修复，非本 change 实施）

### 已完成（6 项，见上方 `[x]`）

三个脚本统一认 `RDDF_KNOWN_FAILURES_FILE`（此前的 `KNOWN_FAILURES_BASELINE` 命名已收敛，无外部消费者）；
两个测试文件全部改用 `$BATS_TEST_TMPDIR` 隔离基线；`setup()` + `teardown()` 守卫（`diff -q` 快照，
比 hash 更严格且同样可判定）；shrink 守卫（按形态判定「基线含 `known failure` 开头的行」，
不依赖计数，故不随语料漂移误红）；实测跑完全量 bats 后基线仍 87 行。

变异验证（均已还原）：塞 fixture 行 ⇒ 守卫红；`run_regression_gate` 改回硬编码 ⇒ fallback 用例红；
`report_regression` 忽略 override ⇒ 两用例红。

### 部分完成（2 项）

| AC | 现状 | 缺口 |
|---|---|---|
| `:142` 环境变量说明三处 | `report_regression.sh` 头注释已写（含「另两个脚本也认此名」） | `refresh_known_failures.sh` 头部窗口 + `tests/README.md` 未写 |
| `:147` 打印解析后的 baseline 路径 | 缺基线时的报错**已**打印覆盖后路径 | 成功路径不打印 —— 与 AC `:140`「不设变量时输出逐字节不变」**直接冲突**，需先裁定二选一 |

### 未做（4 项）

| AC | 内容 |
|---|---|
| `:145` | 确定性复现测试（tmp 副本中途被替换成 fixture ⇒ 三数断言） |
| `:148` | `test_arch_env_check_extraction.bats` 断言改为 `主题架构文档`（`架构差距分析` 已按 ADR-0057 删除） |
| `:149` | `grep -rn '架构差距分析' tests/` 零命中 |
| `:150` | 基线 `:82` 的失效声明修正（`run_arch_env_check_discovers_counts` → passes） |

### 本轮新发现（不在原范围，但同根因）

**「超时掩盖失败」是 teardown 不执行的另一面。** `test_arch_env_check_extraction.bats` 的
`run_arch_env_check_discovers_counts` 实测**单独跑必红**（输出已无 `架构差距分析`，ADR-0057 删了
gap-analysis），但它**不在基线有效条目里** ⇒ 全量门若跑到它应报「新增失败」。
实际全量门报「新增 0」，原因是该文件含两次 `cp -r "$REPO_ROOT"`，撞
`collect_bats_failures.sh` 的 30s 单文件超时被整文件跳过。

⇒ 同一条 30s 超时既让 teardown 不执行（基线被污染），又让慢文件整个被跳过（失败被隐藏）。
修 AC `:145`/`:148`/`:150` 时应一并处理：**慢文件超时不得静默跳过**（至少报出「N 个文件超时未评估」）。

### 教训（供后续同类项参考）

本轮修复的第 1 版引入了两处**假保证**，是变异测试发现的，不是代码审查发现的：

1. `BASELINE=` 变量被误删（当时判「未使用」）⇒ teardown 守卫与 shrink 守卫都在对空路径求值 ⇒ 恒真；
2. 「override 生效」用例只看「基线对比 vs recursive」，无判别力（真实基线存在时两条路径都走 baseline 分支）。

⇒ 凡新增守卫，必须做**变异验证**（造出它该抓的形态，确认真的会红），否则守卫本身可能就是第二个缺陷。

### 立项核查（2026-11-17，planner）

本项与另 5 项 P1 一并做了逐条事实核查（`file:line` 断言全部落到实际代码上验）：

- ✅ 三个脚本的基线路径硬编码位置、两个测试文件的真实基线写入与 `rm -f`、30s 单文件超时机制、
  `run_arch_env_check_discovers_counts` 的僵尸状态 —— **全部与立项描述一致**
- ⚠️ **AC `:147` 与 AC `:140` 自相矛盾**（打印解析路径 vs 输出逐字节不变），已裁定保 `:140`
- 📌 新发现（已写入上文「本轮新发现」）：同一 30s 超时还让慢文件整文件被跳过 ⇒ 僵尸断言在全量门里不可见
