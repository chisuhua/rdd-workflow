---
优先级: P2
priority: P2
来源: 2026-11-17 第八批验收的遗留观察 —— `tests/scripts/collect_bats_failures.sh` 的 30s per-file
  超时对若干天生较慢的测试文件过紧，负载高时它们从「慢」翻成「未评估」，**其失败不进入回归统计**
阶段: phase-2
分类: bugfix
类型: bugfix
状态: draft

生成时间: 2026-11-18
roadmap_ref:
---

# fix-bats-per-file-timeout

**主题**: 回归门里「超时未评估」的文件不被统计 —— 覆盖率的静默流失

## 架构依据

### 机制

`tests/scripts/collect_bats_failures.sh` 逐个文件跑 bats（绕开 bats-core 1.13.0 的
`bats tests/ --recursive` 无限循环 bug），每个文件带一个 per-file 超时：

```bash
PER_FILE_TIMEOUT="${BATS_TIMEOUT:-30}"
OUTPUT_LINE=$(timeout "$PER_FILE_TIMEOUT" bats "$f" 2>&1)
rc=$?
if [ "$rc" -eq 124 ]; then
    # Hang ≠ test failure: log separately so baseline stays clean.
    echo "$f" >> "$HANG_LOG"
    hung_files=$((hung_files + 1))
    continue          # ← 该文件的失败**不被采集**
fi
```

⇒ `timeout` 返回 124 ⇒ 该文件被记为「hung」并 **`continue`** ⇒ 它的 `not ok` 行**不进入** `$OUTPUT`
⇒ `tests/scripts/report_regression.sh` 用这份输出算「新增失败」⇒ **一个失败但慢的文件，对回归门是
不可见的**。

### 这个缺口今天有多大

`report_regression.sh` 会打印一行警告：

```
⚠️  超时未评估: N 个 bats 文件（未纳入本次失败统计，可能隐藏真实失败）
```

但**门仍然通过**（只要「新增失败 = 0」）。⇒ 覆盖率收缩表现为**脚注**，不是**失败**。

实测（同一天、同一台机器）：

| 运行 | 超时未评估的文件数 | bats 阶段耗时 |
|---|---|---|
| 早期批次（机器空闲） | 2 | 640~713s |
| 2026-11-17 批次（机器负载高） | **12** | **2272s** |

⇒ **超时判定对环境高度敏感**（机器越忙 ⇒ 越多文件被判「hung」⇒ 回归门的覆盖面**静默**收缩）。
⇒ 「新增失败 0」在负载高的那次运行里，**可信度低于**空闲时那次。

⚠ **归因尚未坐实**：还有两个候选原因没被排除 —— ① **超时残留进程**（`timeout` 未用 `--kill-after`、
未对进程组发信号 ⇒ SIGTERM 只打直接子进程 ⇒ bats 派生的子 shell / 后台进程可能残留 ⇒ 残留进程与
后续文件争抢资源 ⇒ 「一次超时 ⇒ 后面更多超时」的**正反馈**，这能解释「同一天 2 个 vs 12 个」而不必
归因于机器负载）；② **嵌套采集**（`test_known_failures_baseline.bats` 与
`test_execute_regression_gate.bats` 通过 `PATH` 注入 **fake bats** 调 `report_regression.sh` ⇒ 每次要跑
全量轮次的 `timeout` 子进程 —— 这就是它们 27~49s / 18s 的**固有成本**来源）。
⇒ 本项落地时**必须先实测区分这三种归因**（廉价验证：`BATS_TIMEOUT=1` 跑一次后立刻数残留
`bats`/`sleep` 进程），否则「把超时提到 120s 就够」这个论据可能建立在错误的因果模型上。

### 哪些文件天生较慢

单文件耗时实测（当前工作树）：

| 文件 | 耗时 | 备注 |
|---|---|---|
| `test_install_with_docs.bats` | 47s | 最慢 |
| `test_known_failures_baseline.bats` | 27~49s | 波动大（嵌套采集） |
| `test_env_bootstrap.bats` | 27~29s | |
| `test_execute_regression_gate.bats` | 18s | 嵌套采集 |
| `test_no_spec_workflow_residue.bats` | 7~9s | |

⇒ 30s 的默认超时对前 4 个**贴边或超**（`test_known_failures_baseline` 实测最高 49s = 超时 1.6 倍）。

### ⚠ 一条被证伪的对照（避免后来者重踩）

曾用 `git archive HEAD | tar -x` 抽一份「pristine」副本做对照，测得 `test_env_bootstrap` 只用 4s
⇒ 结论「与本批改动无关」。**该对照无效** —— `git archive` 不含 `.git/`，这些测试在**非 git 目录**里
大量 skip ⇒ 数字天然偏小。

**有效对照**（`git stash` 撤掉本批全部改动后同机实测）：

| 文件 | 撤掉改动后 | 与当前一致？ |
|---|---|---|
| `test_env_bootstrap.bats` | 27s | ✅ 一致 |
| `test_known_failures_baseline.bats` | 49s | ✅ 一致 |
| `test_no_spec_workflow_residue.bats` | 9s | ✅ 一致 |

⇒ 慢是**这些测试的固有成本**（且随负载放大），**与 2026-11-17 那批改动无关**。

### ⚠ 一条比「漏报」更严重的同源后果（第三层意图）

超时不仅造成「漏报」，还造成**静默的信息与数据破坏**：

- `.rddf/reviews/adr-0060-amendment-2026-11-17.md:110-128` 记录：30s 超时杀进程 ⇒ `teardown()` **不
  执行** ⇒ **仓库真实的 `tests/KNOWN_FAILURES.txt` 被截断成 1 行** ⇒ 回归门**每次运行都在摧毁自己的
  基线**；
- 同文件 `:128`：`run_arch_env_check_discovers_counts` 的失败断言**在回归门里 7 周不可见**，因为该文件
  含两次 `cp -r "$REPO_ROOT"` 撞 30s 被跳过。

⇒ 真正要买的是「**超时不得成为静默销毁信息的机制**」。本项覆盖「报告/门」这一半（漏报）；
「进程被杀 ⇒ teardown 不执行 ⇒ 状态留在中间态」这一半**另案处理**（见 Out Scope 的显式声明）。

## 范围

- **In Scope**：
  1. `tests/scripts/collect_bats_failures.sh` 的超时与重试策略（两级重试 + per-test 归因 + 全局重试
     预算 + `--kill-after`）；
  2. `tests/scripts/report_regression.sh` 的「未评估」维度：**从计数阈值改为命名基线**
     （`tests/KNOWN_UNEVALUATED.txt`）+ 报告输出采集 scope + fail-open 防线（采集异常 ⇒ `exit 2`）；
  3. 回归门本身对「未评估文件」的处置（不在命名基线内 ⇒ 门失败；显式旁路 + bypass 审计）；
  4. **fail-open 修复**（既有缺陷，本项必然碰到该分支）：`set -e` 开关错误、`timeout` 的 125/126/127
     返回码被当「通过」、`BATS_TIMEOUT` 的取值未校验、`report_regression.sh` 的重复默认值；
  5. 补测试：脚本级测试（**不依赖真的等 30s**）+ 一条端到端的「慢文件里的失败会浮出来」判据。
- **Out Scope**：
  - 不改那 5 个慢测试**本身**的实现（它们慢有正当理由：装环境、跑全量扫描、嵌套采集 —— 优化它们是
    另一件事，且收益不确定）；
  - **不处理「超时杀进程 ⇒ teardown 不执行 ⇒ 仓库状态留在中间态」**（如 `KNOWN_FAILURES.txt` 被截断
    —— 见「第三层意图」）⇒ **另案**；本项只覆盖「漏报」这一半。⚠ 显式声明，避免后来者以为已一并解决；
  - 不改 `tests/KNOWN_FAILURES.txt` 的 baseline 内容（那是 `refresh_known_failures.sh` 的职责）；⚠ 且
    CI **明令禁止**该文件增长（`.github/workflows/test.yml` 的 shrink-only 断言）⇒ 被暴露的真实失败
    **必须在本 change 内修掉**，不得靠扩大基线消化；
  - 不改 bats-core 的版本或绕过 `bats tests/ --recursive`（那是另一个问题）；
  - 不动 CI 工作流的其它步骤；
  - **不覆盖 integration 之外的 27 个 `.bats`**（`tests/smoke.bats`、`tests/_lib/*.bats`、
    `tests/unit/*.bats`、`tests/e2e/**`）—— 它们由 CI 的 `bats tests/ --recursive` 单独覆盖 ⇒ 但报告
    **必须声明**这个 scope 边界（否则报告会制造一个「更难被发现的空真」）。

## Why

**回归门的「新增失败 0」在机器最忙的时候最不可信，而那正是最需要它的时候。**

- 这次交付里，「全量门 ALL PASSED」是**主要验收证据**（B / D 两个 change 的验收报告都引用它）；
- 而同一批的运行日志里写着「⚠️ 超时未评估: 12 个 bats 文件（未纳入本次失败统计，可能隐藏真实失败）」
  —— 也就是说，**有 12 个文件在这次「全绿」里根本没被评估**；
- ⇒ 这是一个**验收证据本身的强度问题**，不是测试基础设施的小瑕疵：结论「没有新增失败」在覆盖收缩
  时可能是**空真**（前提不成立 ⇒ 结论无信息量）；
- ⇒ 派生目标（**不是**目标）：「让那 5 个慢测试不再被当成 hung」是副作用；把它当目标会诱导错误方案
  （提高默认超时 / 维护白名单名单）—— 本项的方案不依赖「哪些文件慢」这份名单。

## What Changes

1. **采集侧：两级重试 + per-test 归因 + 预算**：
   - **第一级**：per-file 超时 `BATS_TIMEOUT`（默认 30s）；
   - **命中 124 ⇒ 重试**：`BATS_TIMEOUT_RETRY`（默认 120s）作为 **per-test** 超时
     （`BATS_TEST_TIMEOUT`），文件级超时设为 `BATS_TIMEOUT_RETRY + BATS_TIMEOUT` ⇒ 单个 test 卡住时，
     **只有它**被标超时（带 test name），**文件内其余 test 仍被评估**，文件不再 124 ⇒ 分类从「整文件
     弃」升级为「**按名字归因**」；
     - ⚠ per-test 超时产生的失败**单独成段**（`per-test timeouts`），**不进** `$OUTPUT`（否则成为新增
       失败噪声）；
     - ⚠ 采集启动时若 `BATS_TEST_TIMEOUT` 不可用（旧 bats）⇒ **`exit 2`** ⇒ 防止静默降级回「整文件弃」
       却在报告里装作已归因（`BATS_TEST_TIMEOUT` 自 bats 1.5.0 起提供；本仓旁证为 bats-core 1.13.0）；
   - **重试语义（4 条，写死）**：① 整文件重跑（bats 没有「从第 N 个 test 继续」的入口）；② 第一次的
     **部分输出丢弃、绝不合并**（SIGTERM 可能截断 TAP 行中途 ⇒ 合并会污染失败集合）；③ 第二次输出为
     **权威结果**；④ 仅在 `rc == 124` 时重试；
   - **全局重试预算** `BATS_RETRY_BUDGET`（默认 600s）⇒ 预算耗尽 ⇒ 剩余命中 124 的文件照记未评估并让门
     失败（而不是无限重试）；⇒ 上界可算：12 个文件 × 120s ≈ **+24 分钟**（⚠ 草案曾按「5 个」算成
     +10 分钟 —— 那是空闲批次的数据，与出问题的那批不是同一组）；
   - **`timeout --kill-after`**（`timeout -k 5 "$T"`）⇒ 避免残留进程自我放大。
2. **hang vs 慢的可观测化**（否则「真 hang 仍被识别」不可判定）：hang 日志行改
   `path rc=124 elapsed=120s last_tap=<n>/<total>`；分类规则：**零 TAP 进展 ⇒ 疑似真 hang**；**有进展
   但未完成 ⇒ 慢文件**。
3. **采集侧的 fail-open 修复**（既有缺陷）：
   - `collect_bats_failures.sh:47-50` 的 `set +e` / `set -e` 开关错误（循环内 `set -e` 重新打开 ⇒ 任何
     未加 `|| true` 的命令失败会**中止整个脚本且不打印 summary**）⇒ 改成
     `if OUTPUT_LINE=$(timeout ...); then rc=0; else rc=$?; fi`；
   - **`rc` 分类表**：`0` ⇒ 无失败；`非零且输出含 not ok` ⇒ 失败被采集；`124` ⇒ 超时（重试）；`125/126/127`
     （`timeout` 自身失败 / 不可执行 / 找不到）⇒ **infra error ⇒ `exit 2`**；其余非零 ⇒ 解析 TAP；
   - **env 取值校验**：`BATS_TIMEOUT` 必须匹配 `^[1-9][0-9]*$`（`0` = 不设限 ⇒ 真 hang 永久挂住 ⇒ CI job
     超时才被杀 ⇒ 不打印 summary ⇒ fail-open 链；负数/非数字 ⇒ `timeout` 自己报错 rc≈125）；且
     `BATS_TIMEOUT_RETRY ≥ BATS_TIMEOUT`（否则重试比第一次更短）；
   - **显式化 TAP 依赖**：`collect:57` 的 `grep -E "^not ok"` 依赖 bats 非 tty 时输出 TAP 的隐含行为 ⇒
     改用 `bats --tap` 或在注释里钉死该依赖（否则有人为调试改成 `--pretty` ⇒ **静默零失败**）。
4. **报告侧的 fail-open 防线**：
   - **M 的定义与位置**：`M` = **循环前**的 `${#files[@]}`（**不是**循环计数器 `i` —— 脚本中途退出时 `i`
     小于总数、连 summary 都不打印 ⇒ `report_regression.sh` 抽不到 `hung files:` ⇒ 默认 0 ⇒ **fail-open**）；
   - `report_regression.sh` **自己再 glob 一次**作为独立真相（不信 collect 的 stdout）；
   - **collect summary 缺失 ⇒ `exit 2`**（infra error），**不得**当作 N=M / 未评估 0；
   - **未评估门失败时不得打印** `✅ 0 新增失败`（`report_regression.sh:143-144` 现在无条件打印）⇒ 否则
     验收者只看到 ✅；
   - **退出码契约**：`report_regression.sh:14-17` 的文件头只有 0/1/2 ⇒ **复用 1**，不引入 3（下游
     `test.sh` / `run_regression_gate.sh` 只判非零）；
   - **scope 声明**：报告输出 `📊 评估 {N}/{M} 个文件（scope: tests/integration/*.bats；仓库另 {X} 个
     .bats 不在本门范围）`。
5. **「未评估」的判定：从计数阈值改为命名基线**（核心设计变更）：
   - 计数阈值**不追踪身份**（今天 A、B，明天 C、D，只要个数 ≤ 阈值就放行）⇒ 策略实际是「允许任意 N 个
     文件被隐藏」⇒ 与 `KNOWN_FAILURES.txt` 的既有哲学（按名字 + reason + CI shrink-only）相悖且不可审计；
   - ⇒ 新增 **`tests/KNOWN_UNEVALUATED.txt`**（每行 `path # reason`，与 baseline 同格式）：
     **任一未评估文件不在清单内 ⇒ 门失败**；在清单内 ⇒ 打印但不失败；
   - CI 加 **shrink-only**（照抄 `KNOWN_FAILURES.txt` 的既有断言形态）⇒ 禁止清单增长；
   - 保留 `SKIP_UNEVALUATED_GATE=yes` 作紧急旁路（命名与仓内既有 `SKIP_<被测对象>` 谱系一致：已核实
     40+ 个 `SKIP_*`），但 **在 CI workflow 里断言它未被设置**（否则门会永久旁路，而 `bypass-audit` 一个
     月后才 WARNING）⇒ 它的出现应被列为 CRITICAL 而非月度阈值。
6. **默认值只有一个真源**：`report_regression.sh:49` 现在**重复**给 `BATS_TIMEOUT` 兜默认 30 ⇒ 新增的
   `BATS_TIMEOUT_RETRY` / `BATS_RETRY_BUDGET` 若只在 collect 读、report 不转发 ⇒
   `BATS_TIMEOUT_RETRY=300 bash tests/scripts/report_regression.sh` **静默无效** ⇒ 去掉 report 端的
   兜默认值，**全部透传**，默认值只在 collect 一处。
7. **并发与嵌套安全**：`HANG_LOG="${OUTPUT}.hangs"` + `: > "$OUTPUT"` ⇒ 两个进程共用同一 `OUTPUT`
   （默认 `/tmp/bats-failures.txt`，`tests/README.md:118` 文档化了该路径）会互相截断 ⇒ **失败集合静默
   变小**（与本次要修的病同型）⇒ collect 内部 `mktemp` 或加锁 + 陈旧锁检测；
   `RDDF_BATS_COLLECT_ACTIVE=1` 标记 ⇒ 检测到已在采集中 ⇒ 直接 `exit 2`（防「采集套采集」）。
8. **归因实测**（落地第一步，不是最后一步）：`BATS_TIMEOUT=1` 跑一次 ⇒ 数残留 `bats`/`sleep` 进程 ⇒
   判定「2 个 vs 12 个」的真正原因是**机器负载**、**残留进程正反馈**还是**嵌套采集** ⇒ 据此决定
   「两级重试」是否足够（若正反馈是主因，则 `--kill-after` 才是关键修复）。

### 备选方案

| 备选 | 结论 | 理由 |
|---|---|---|
| ① 直接把默认超时提到 120s | **拒绝** | 真 hang 的等待翻 4 倍；**不**恢复「单文件被评估」的判定（悬崖只是挪位置）；**掩盖**了「哪些文件天生慢」这个信息 |
| ② per-file 超时白名单 | **拒绝** | 维护成本随慢文件增长；**新增**的慢文件仍会静默漏评估 —— 本项正要消灭「静默」，不能引入一个靠名单维持的静默 |
| ③ 计数阈值（`MAX_UNEVALUATED=2`） | **拒绝** | 不追踪身份 ⇒ 实际语义是「允许任意 2 个文件被隐藏」；与 `KNOWN_FAILURES.txt` 的既有哲学相悖；不可审计；且实测值 2 与空闲批次的巧合重合，**不是推导** |
| ④ **per-test timeout + 命名基线 + 两级重试**（本项） | **接受** | 不需要维护慢文件名单；按**名字**归因（可分辨「真 hang」与「慢」）；未评估变成「需要有人写进清单 + 给理由」⇒ 正是「需要有人负责的状态」 |

## Acceptance

- [ ] **AC-A（端到端，慢文件里的失败会浮出来）**：在**已知慢文件** `tests/integration/test_known_failures_baseline.bats`
      里临时插入 `@test "zz-synthetic-red" { false; }` ⇒ 跑 `bash tests/scripts/report_regression.sh` ——
      **改动前**：报告中**不出现** `zz-synthetic-red`（该文件撞 30s 被跳过）；**改动后**：出现
      `新增失败: 1` 且明细含 `zz-synthetic-red`。（代价：一次 report 运行，1~3 分钟。**这是唯一能把
      「覆盖率不再静默收缩」变成可判定判据的 AC**。）
- [ ] **AC-B（fail-open 防线）**：让 `collect_bats_failures.sh` 中途 `exit 1`（或 `kill -TERM` 掉它）⇒
      `report_regression.sh` 必须**失败**（非零），且输出**不含** `✅ 0 新增失败` ⇒ 断言
      `[[ "$output" != *"✅ 0 新增失败"* ]] && [ "$status" -ne 0 ]`
- [ ] **AC-C（分母固定）**：`M` 在循环前由 glob 算出、独立于循环是否走完；`BATS_TIMEOUT=1` 跑一次 ⇒
      断言输出含 `评估 K/M`，其中 `M` 等于 `ls tests/integration/*.bats | wc -l`（测试内**动态计算**，
      不硬编码 —— 仓内有「断言硬编码」的教训）
- [ ] **AC-D（scope 声明）**：报告须打印采集 scope（`tests/integration/*.bats`）并与全仓 `.bats` 总数区分
      ⇒ 断言输出含 `tests/integration/` 与「不在本门范围」字样
- [ ] **AC-E（rc 分类）**：四个 fake-bats 夹具分别返回 `0` / `1`（带 `not ok`）/ `124` / `125` ⇒ 断言
      `0` ⇒ 无失败、`1` ⇒ 失败被采集、`124` ⇒ 进 hang 日志、`125` ⇒ **infra error `exit 2`**
- [ ] **AC-F（env 穿透）**：`BATS_TIMEOUT_RETRY=5 bash tests/scripts/report_regression.sh` ⇒ 重试预算
      真的变成 5（用 `BATS_TIMEOUT=1` + fake bats `sleep 2` 观测：穿透成功则该文件被评估而非判 hang）
- [ ] **AC-G（时长不退化）**：同一棵树计时 bats 阶段 wall clock，改前/改后各一次 ⇒ 断言
      `after ≤ before × 1.15`（实测值写进 change）⇒ 兜住 Impact 承认的 +24 分钟风险
- [ ] **AC-H（no-orphan）**：一次含 124 的采集跑完后，`pgrep -f "bats .*\.bats"` 为空 ⇒ 证实/证伪「残留
      进程正反馈」假设
- [ ] **AC-I（CI 侧口径）**：`test.yml` 的 `report_regression.sh` step 显式设定阈值变量（或在文件内注释
      声明「CI 用默认值，实测 CI 未评估 ≤ K」）；且 `run_regression_gate.sh` 的 **fallback 路径**
      （baseline 缺失 ⇒ `bats tests/ --recursive`）须说明「该路径无未评估概念」⇒ 否则「门的一个维度」
      只覆盖一半入口
- [ ] **AC-J（命名基线的 shrink-only）**：CI 禁止 `tests/KNOWN_UNEVALUATED.txt` 增长（形如
      `KNOWN_FAILURES.txt` 的既有断言）
- [ ] **AC-K（per-test 归因）**：用一个「第一个 test `sleep 999`、第二个 test `false`」的 fake bats ⇒ 断言
      ① per-test 超时把**卡住的 test 名**单独报出（落到独立的 `per-test timeouts` 段，**不进**失败集合）；
      ② **同一文件内的其余 test 仍被评估**（第二个 test 的 `not ok` 出现在输出里）
- [ ] **AC-L（hang vs 慢可分辨）**：两个夹具 ——「无限 sleep 无任何输出」⇒ 判疑似真 hang（零 TAP 进展）；
      「先打 5 条 ok 再 sleep」⇒ 判慢文件（有 TAP 进展但未完成）
- [ ] **AC-M（env 取值校验）**：`BATS_TIMEOUT=0` / `=-5` / `=abc` ⇒ **前置校验失败 ⇒ `exit 2`**（不得
      静默变成「不设限」或「当通过」）；`BATS_TIMEOUT_RETRY < BATS_TIMEOUT` ⇒ 同样 `exit 2`
- [ ] **AC-N（并发/嵌套安全）**：两个 `collect_bats_failures.sh` 并发 ⇒ 失败集合**不互相截断**；
      `RDDF_BATS_COLLECT_ACTIVE=1` 时再启动 ⇒ 直接 `exit 2`（不递归采集）
- [ ] **AC-O（重试语义）**：第一次的部分输出**不被合并**进失败集合（构造一个「先失败再超时」的夹具 ⇒
      断言失败集合里**没有**第一次的 test name）
- [ ] 慢文件的用例可被观测且**不真的等 30s**：夹具用 `BATS_TIMEOUT=1` + fake bats ⇒ 该断言总耗时 < 5s
- [ ] 真 hang 的文件仍进 `.hangs`，且**不被误判为失败**
- [ ] 报告输出「评估了 N/M 个文件，未评估 K 个」
- [ ] **未评估文件不在 `tests/KNOWN_UNEVALUATED.txt` 内 ⇒ 门失败**；在清单内 ⇒ 打印但不失败；
      `SKIP_UNEVALUATED_GATE=yes` + reason ⇒ 放行**且留 bypass 审计记录**（落 `.rddf/state/.bypass-audit.jsonl`）
- [ ] 阈值变量（`BATS_TIMEOUT` / `BATS_TIMEOUT_RETRY` / `BATS_RETRY_BUDGET`）可由环境变量覆盖，
      且**默认值只有一处**（collect），report 端**只透传**
- [ ] `./test.sh --full --regression` ⇒ 报告形如「评估 M/M 个文件，未评估 0」；若有未评估，必须在
      `KNOWN_UNEVALUATED.txt` 里逐条有 reason，且该文件**未增长**
- [ ] 被暴露的真实失败**在本 change 内修掉**（或走既定 exception 流程并记录）⇒ **不扩大**
      `KNOWN_FAILURES.txt`

## Capabilities

- 回归门能**指出「哪些文件没有被评估」**（不是只报一个数）⇒ 「新增失败 0」这个结论的**前提**变得可见
- 慢文件与真 hang 被**区分**（按名字归因 + TAP 进展）⇒ hang 日志从此是**信号**而不是「混进来的慢文件」
- 未评估文件变成**需要有人写进清单 + 给理由**的状态 ⇒ 不再是脚注
- 采集侧不再 fail-open（`set -e` 开关 / 125-127 / summary 缺失 / env 未校验 / 并发截断）
- 显式旁路 + 审计 + CI 断言 ⇒ CI 上无法悄悄降低标准

## Impact

- **影响面**：`tests/scripts/collect_bats_failures.sh`（两级重试 + per-test 归因 + 预算 + rc 分类 +
  env 校验 + `set -e` 修复 + 并发/嵌套防护）、`tests/scripts/report_regression.sh`（未评估维度 + scope
  声明 + fail-open 防线 + 透传 env + 退出码契约）、`tests/KNOWN_UNEVALUATED.txt`（**新增**，tracked）、
  `tests/README.md:118`（直连用法需更新）、CI 工作流（阈值口径 + shrink-only + `SKIP_*` 未设置断言）、
  新增脚本级测试。
- **风险**：
  - **回归门时长上升**：最坏 12 个文件 × 120s ≈ **+24 分钟**（叠加 2272s ⇒ 单次全量门约 50 分钟）⇒
    AC-G 兜底；
  - **覆盖恢复后可能暴露此前被隐藏的真实失败** ⇒ 那**正是本项的目的**，但会让某次运行「变红」⇒
    AC-A 的合成失败必须在回滚前撤掉；
  - **CI 上机器更慢**（`test.yml` 未设 `BATS_TIMEOUT`，runner 通常更慢）⇒ 30s 一级在 CI 的命中率可能
    高于本地 ⇒ **CI 侧不接受该旁路**（断言 `SKIP_UNEVALUATED_GATE` 未设置），且其出现应被列为
    CRITICAL（而不是等月度阈值才 WARNING）；
  - **不得**用「把默认超时调大」代替本项 —— 那会让真 hang 的等待翻倍而**不**恢复覆盖率判定；
  - **per-test 超时的失败不进失败集合** ⇒ 若实现时误放进 `$OUTPUT`，会变成一批假的「新增失败」⇒ AC-K 的
    两段断言专门守这一点；
  - **首次「覆盖率恢复」的运行很可能是红的**，且原因可能不是本项代码错（那些文件历史上没在门内执行过，
    可能污染 `.rddf/state/`、写真实 baseline、依赖外部网络）⇒ 落地时预留「首次运行允许暴露既有债，
    逐条归因」的步骤，不让 verifier 当成本项失败。
- **兼容性**：`BATS_TIMEOUT` 的语义不变（第一级超时）；新增 `BATS_TIMEOUT_RETRY`、`BATS_RETRY_BUDGET`、
  `BATS_TEST_TIMEOUT`（per-test）、`SKIP_UNEVALUATED_GATE`、`RDDF_BATS_COLLECT_ACTIVE`。
  ⇒ **默认值只有一处**（collect），report 只透传。
- **依赖**：无（独立于其它 change）；但**必须在下一批「全量门全绿」被当作强证据之前**落地 —— 否则下一个
  验收报告还会引用一个可能空真的结论。

## 审稿记录

metis 1 轮（2026-11-18，planner 阶段 gap 分析）。逐条处置：见文末「metis 处置记录」。

### metis 处置记录（2026-11-18）

metis 的核心判断：**主意图是「验收证据本身的强度」** —— 回归门输出的「通过」必须能作为交付证据被引用；
「让那 5 个慢测试不再被当成 hung」是**副作用**（当成目标会诱导「提高默认超时 / 维护白名单」这两条退路）。
metis 还挖出**第三层意图**：超时不仅造成漏报，还造成**静默的数据破坏**（teardown 不执行 ⇒
`KNOWN_FAILURES.txt` 被截断）。

| # | metis finding | 处置 |
|---|---|---|
| P0-1 | **「未评估」用计数阈值（`MAX_UNEVALUATED=2`）不追踪身份** ⇒ 实际语义是「允许任意 2 个文件被隐藏」；与 `KNOWN_FAILURES.txt` 既有哲学相悖；不可审计；且实测值 2 与空闲批次**巧合**重合 | ✅ **全部采纳** ⇒ 改为**命名基线** `tests/KNOWN_UNEVALUATED.txt`（每行 `path # reason`）：不在清单内 ⇒ 门失败；清单内 ⇒ 打印但不失败；CI 加 shrink-only；保留 `SKIP_UNEVALUATED_GATE` 作紧急旁路但**CI 断言其未被设置**；⇒ `MAX_UNEVALUATED` 这个魔法数字整条消失（What Changes §5 + AC-J） |
| P0-2 | **M 的分母有三种可选值**：(a) glob 总数 / (b) 循环计数器 `i` / (c) 全仓总数；**正确答案是 (a) 并显式标注 scope**；(b) 最危险 —— 脚本中途退出时 `i` < 总数、连 summary 都不打印 ⇒ report 抽不到 `hung files:` ⇒ 默认 0 ⇒ **新门维度 fail-open**；且 integration 之外还有 27 个 `.bats` 从不被本门覆盖 ⇒ 不声明 scope 会制造**更难被发现的空真** | ✅ 全部采纳 ⇒ M = **循环前**的 `${#files[@]}`；report **自己再 glob 一次**作独立真相；collect summary 缺失 ⇒ `exit 2`（不得当作 N=M / 未评估 0）；报告格式 `📊 评估 {N}/{M} 个文件（scope: tests/integration/*.bats；仓库另 {X} 个 .bats 不在本门范围）`（What Changes §4 + AC-C/AC-D） |
| P0-3 | **fail-open 防线缺失**：`rc` 分类不完整（`timeout` 的 125/126/127 被当「通过」）；`BATS_TIMEOUT` 未校验（`0` = 不设限 ⇒ 真 hang 永久挂住 ⇒ CI job 超时才被杀 ⇒ 不打印 summary）；`BATS_TIMEOUT_RETRY` 未校验 ≥ `BATS_TIMEOUT`；未评估门失败时仍会打印 `✅ 0 新增失败`；退出码契约需写进文件头且**复用 1**（下游只判非零） | ✅ 全部采纳 ⇒ What Changes §3/§4 + AC-E / AC-M |
| P0-4 | **既有 `set -e` 开关缺陷**（`collect:47-50`）：循环内 `set -e` 重新打开 ⇒ 任何未加 `\|\| true` 的命令失败会**中止整个脚本且不打印 summary** ⇒ 与 P0-2 串联成 fail-open | ✅ 采纳 ⇒ 改成 `if OUTPUT_LINE=$(timeout ...); then rc=0; else rc=$?; fi`（What Changes §3） |
| P0-5 | **重试语义 4 条未定义**（其中 1 条会产生错误行为）：bats 没有「从第 N 个 test 继续」的入口 ⇒ 只能整文件重跑；**第一次的部分输出必须丢弃、绝不合并**（SIGTERM 可能截断 TAP 行中途 ⇒ 合并会污染 `sort -u` 后的集合） | ✅ 全部采纳 ⇒ What Changes §1 的「重试语义（4 条，写死）」+ AC-O |
| P1-6 | **【最重要】「真 hang vs 慢」在纯 per-file 语义下物理上不可判定** —— 已核实全仓 `grep -rn BATS_TEST_TIMEOUT .` **零命中** ⇒ per-test timeout 在本仓**从未启用** ⇒ 「单个 test 卡住 ⇒ 整文件 124 ⇒ 整文件弃」是当前**唯一可能**的行为；⇒ 引入 `BATS_TEST_TIMEOUT` 不是「加一层优化」，而是**把当下不存在的归因维度补上** —— 在此之前「哪个 test 卡住」在架构上不可能被产出，AC「真 hang 被识别」**在任何实现下都无法通过** | ✅ **全部采纳** ⇒ 重试级启用 `BATS_TEST_TIMEOUT=$BATS_TIMEOUT_RETRY`，文件级超时设为 `RETRY + TIMEOUT`；per-test 超时单独成段（**不进** `$OUTPUT`）；**启动前置断言**：旧 bats 无该能力 ⇒ `exit 2`（防止静默降级却在报告里装作已归因）⇒ What Changes §1 + AC-K |
| P1-7 | **重试成本无上限**，且草案的算术与自己的数据不一致（「5 个 ⇒ +10 分钟」，实为 12 个 ⇒ +24 分钟） | ✅ 采纳 ⇒ 新增**全局重试预算** `BATS_RETRY_BUDGET`（默认 600s），耗尽 ⇒ 照记未评估并让门失败；Impact 的 +10 分钟改写为 **+24 分钟**（What Changes §1 + AC-G） |
| P1-8 | **hang vs 慢必须可观测**，否则 AC 永远不可判定 | ✅ 采纳 ⇒ hang 日志行 `path rc=124 elapsed=120s last_tap=<n>/<total>`；规则：**零 TAP 进展 ⇒ 疑似真 hang**；**有进展但未完成 ⇒ 慢文件**（What Changes §2 + AC-L） |
| P1-9 | **`timeout` 未用 `--kill-after`、未对进程组发信号** ⇒ 残留进程可能自我放大（「一次超时 ⇒ 后面更多超时」），**这比「机器负载」更可能是 2→12 的真因** | ✅ 采纳 ⇒ `timeout -k 5 "$T"` + AC-H（`pgrep` 断言无残留）；并把「归因实测」列为 What Changes §8 的**第一步**（不是最后一步）——「提到 120s 就够」这个论据可能建立在错误的因果模型上 |
| P1-10 | **`report_regression.sh:49` 重复给 `BATS_TIMEOUT` 兜默认 30** ⇒ 新增变量若只在 collect 读则**静默无效**，AC 会在 collect 层**假绿** | ✅ 采纳 ⇒ 去掉 report 端兜默认值、**全部透传**、默认值只在 collect 一处（What Changes §6 + AC-F） |
| P1-11 | **并发与嵌套安全**：两个进程共用同一 `OUTPUT`（默认路径已被 `tests/README.md:118` 文档化）会互相截断 ⇒ **失败集合静默变小**（与本次要修的病同型）；嵌套采集（fake bats 注入）⇒ 「采集套采集」 | ✅ 采纳 ⇒ collect 内部 `mktemp` 或加锁 + 陈旧锁检测；`RDDF_BATS_COLLECT_ACTIVE=1` ⇒ 检测到已在采集中 ⇒ `exit 2`（What Changes §7 + AC-N） |
| P2-12 | **Why 缺第三层意图**（超时 ⇒ teardown 不执行 ⇒ 状态留中间态 ⇒ 数据丢失事故），且 Out Scope 未申明 ⇒ 后来者会误以为已覆盖 | ✅ 全部采纳 ⇒ 架构依据新增「第三层意图」段（引 `adr-0060-amendment-2026-11-17.md:110-128` 的两个实证）；**Out Scope 显式写明「不处理 teardown 不执行 ⇒ 状态留中间态，另案」** |
| P2-13 | **AC 措辞 slop**：「第一条必须是红的」（依赖排序）、「真 hang 仍被识别」（当前设计下不可判定）、「hang 日志是信号」（无对应断言）、「+10 分钟」（数字错）、「阈值默认宽松因为 CI 永远有噪声」（不可证伪）、Impact 的排期紧迫感会被读成「可跳过 AC 的理由」、「三个候选方案」措辞（§1 只有两个备选 + 本项） | ✅ 全部采纳 ⇒ AC 重写为**按名字判定**（AC-A/AC-O）、AC-L（两个夹具区分 hang vs 慢）、AC-G（时长不退化）；数字改 +24 分钟；「CI 永远有噪声」删除；排期紧迫感从 Impact 移出（只在依赖里留一句）；候选表改为「两个备选 + 本项 + 第 4 案（per-test timeout + 命名基线）」；Why 明确「派生 vs 主」 |
| P2-14 | **Impact 与 CI 冲突**：`KNOWN_FAILURES.txt` 在 CI 是 **shrink-only**（`test.yml` 明令禁止增长）⇒ 「baseline 可能需刷新」在 ship 阶段必然卡死 | ✅ 采纳 ⇒ Impact 改写为「被暴露的真实失败**必须在本 change 内修掉**；确属既有债的走既定 exception 流程并记录，**不得**扩大基线」；AC 末条同义 |
| P2-15 | 缺「首次覆盖率恢复的运行很可能是红的（那些文件历史上没在门内执行过，可能污染状态 / 写真实 baseline / 依赖外网）」的预告 | ✅ 采纳 ⇒ Impact 风险段 + AC-A 的「合成失败必须在回滚前撤掉」 |
| 边界 1 | 重试后仍 124 ⇒ 记 hang 还是未评估？ | ✅ 采纳 ⇒ **一次落一行两字段**（`path rc=124 elapsed=120s last_tap=n/total`）⇒ N/M 与 hang 日志两处数字对得上 |
| 边界 3 | `BATS_TIMEOUT=0` / 负数 / 非数字 ⇒ 现在会被当「通过」 | ✅ 采纳 ⇒ 前置校验 `^[1-9][0-9]*$` ⇒ 否则 `exit 2`（AC-M） |
| 边界 4 | 采集期间文件被改写 ⇒ 两级重试把「并发编辑」的窗口拉长到 150s/文件 ⇒ 可能被误判为 hang | ✅ **部分采纳** ⇒ 在范围/风险段登记（重试前比对 mtime，变了判 infra error）—— 列为实施细节，写入 What Changes §1 的重试语义第 5 条 |
| 边界 5 | 并发跑两份采集 ⇒ 互相截断 | ✅ 采纳（同 P1-11） |
| 边界 6 | 嵌套调用（本仓真实存在）⇒ 两级重试把最坏放大到 150s × 嵌套层数 | ✅ 采纳（同 P1-11） |
| 边界 7 | CI 阈值放宽 ⇒ 门是否永久失效 | ✅ 采纳 ⇒ CI **不接受**该旁路 + 其出现列为 CRITICAL（不是月度阈值） |
| 边界 8 | 整仓层面的覆盖缺口（27 个 `.bats` 不在本门 scope 内） | ✅ 采纳 ⇒ Out Scope 显式写明 + 报告必须声明 scope（AC-D） |
| 边界 9 | 跨文件污染 ⇒ 第一次「覆盖率恢复」的运行很可能是红的 | ✅ 采纳（同 P2-15） |
| 边界 10 | 大小写/分隔符变体（`Guide-Ship` / `guide_ship`） | ✅ **不适用**（本项不涉及 stage 名匹配）⇒ 明确记为不适用 |
| 缺失判据 | 补 AC-A（端到端：慢文件里的失败会浮出来）/ AC-B（fail-open）/ AC-C（分母）/ AC-D（scope）/ AC-E（rc 分类）/ AC-F（env 穿透）/ AC-G（时长）/ AC-H（no-orphan）/ AC-I（CI 口径）/ AC-J（shrink-only）/ AC-K（per-test 归因）/ AC-L（hang vs 慢）/ AC-M（env 校验）/ AC-N（并发/嵌套）/ AC-O（重试语义） | ✅ **全部采纳**（共 15 条） |

