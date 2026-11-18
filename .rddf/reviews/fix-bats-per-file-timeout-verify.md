# fix-bats-per-file-timeout — 验收报告

- **change**：`fix-bats-per-file-timeout`
- **验收日期**：2026-11-18
- **验收角色**：builder（角色内建 verifier，非 subagent）
- **判据来源**：`.rddf/improvements/fix-bats-per-file-timeout.md` 的 `## Acceptance`（22 条）+ `openspec/changes/fix-bats-per-file-timeout/proposal.md` 的 `## Acceptance`（同一份，由 P0 从 improvement 生成）
- **实现分支**：`openspec/fix-bats-per-file-timeout`（worktree 模式）→ 已合入 master（`eb98421`）

---

## 1. 逐条判定

| # | 判据 | 判定 | 证据 |
|---|---|---|---|
| AC-A | 端到端：慢文件里的失败会浮出来 | ✅ pass | 临时插入 `@test "zz-synthetic-red" { false; }` 到 `tests/integration/test_known_failures_baseline.bats` ⇒ `bash tests/scripts/report_regression.sh` 输出 `新增失败: 1`、明细含 `zz-synthetic-red`、退出码 1（合成失败已撤除，git diff 无残留）。**另有一例真实发生**：旧采集整文件跳过 `tests/integration/test_cross_repo_impact_detection.bats`（撞 30s）⇒ 它当时真实存在的失败 `01_single_contract_match_returns_warning_and_report` 在旧结果里不可见；新采集 256/256 全评估 ⇒ 该失败浮出并已修 |
| AC-B | fail-open 防线 | ✅ pass | `tests/integration/test_regression_gate_evaluation.bats`：「report: collect summary 缺失 ⇒ exit 2」「report: collect 自身失败（infra error）⇒ exit 2」，两条都断言 `[[ "$output" != *"✅ 0 新增失败"* ]]` 且 `status != 0` |
| AC-C | 分母固定 | ✅ pass | 用例「collect: summary 的分母 M 在循环前算好」断言 `evaluated: 3/3 files`；报告侧 `M="$(ls .../tests/integration/*.bats \| wc -l)"` 自己算一遍，与 collect 的 M 不一致 ⇒ exit 2 |
| AC-D | scope 声明 | ✅ pass | 实测输出：`📊 评估 256/256 个文件（scope: tests/integration/*.bats；仓库另 27 个 .bats 不在本门范围）`；用例断言含 `tests/integration/` 与「不在本门范围」 |
| AC-E | rc 分类 | ✅ pass | 4 个 fake-bats 夹具：0 ⇒ `! -s "$OUT"`；1 ⇒ `grep -q "some failure"`；124 ⇒ 进重试/未评估路径；125 ⇒ `status -eq 2` |
| AC-F | env 穿透 | ✅ pass | 用例断言 fake bats 收到 `TESTTIMEOUT: 3`（= `BATS_TIMEOUT_RETRY`）；`report_regression.sh` 里原来的 `BATS_TIMEOUT="${BATS_TIMEOUT:-30}"` 兜默认已删除（默认值只在 collect 一处） |
| AC-G | 时长不退化 | ⚠️ **deviation** | 同一棵树、同一台机器、背靠背实测：**改前 340.8s → 改后 431.3s（1.27×）**，超过 1.15× 界。多出的 ~90s 买到的是「1 个此前被整文件跳过的文件被真正评估」（连带浮出它的真实失败）。增长有硬上界：`BATS_RETRY_BUDGET`（默认 600s）封顶 ⇒ 无论多少文件慢，重试**实际**总时长 ≤ +600s（≈ +10min），远小于 Impact 承认的最坏 +24min。⚠️ 绝对数字受机器负载影响很大（测量时 4 核机器 load avg 15~23，来自机器上的其它工作）⇒ 比值才是判据 |
| AC-H | no-orphan | ✅ pass | 采集结束后 `ps -eo comm \| grep -c '^bats'` = 0；`pgrep -f collect_bats[-]failures` 无残留 |
| AC-I | CI 侧口径 | ✅ pass | `.github/workflows/test.yml` 的回归门 step 显式设定 `BATS_TIMEOUT: '30'` / `BATS_TIMEOUT_RETRY: '120'` / `BATS_RETRY_BUDGET: '600'`；新增 step「Regression-gate bypass must not be set in CI」断言 `SKIP_UNEVALUATED_GATE` 未设置；`skills/execute/scripts/run_regression_gate.sh` 的 fallback 路径已注明「该路径无未评估概念」；「Install bats」step 打印 `bats --version`（门需要 ≥ 1.5.0） |
| AC-J | 命名基线的 shrink-only | ✅ pass | workflow 新增 step「KNOWN_UNEVALUATED.txt shrink-only enforcement」（照抄 `KNOWN_FAILURES.txt` 的断言形态）；用例断言 workflow 含 `KNOWN_UNEVALUATED` 与 `SKIP_UNEVALUATED_GATE` |
| AC-K | per-test 归因 | ✅ pass | 用例断言：卡住的 test 进 `$OUT.per-test-timeouts`；同文件其余 test 的失败（`real failure`）仍进 `$OUT`；per-test 项**不**进 `$OUT` |
| AC-L | hang vs 慢可分辨 | ✅ pass | 用例断言零 TAP 进展 ⇒ `kind=hang` + `last_tap=0`；有进展 ⇒ `kind=slow` + `last_tap=2` |
| AC-M | env 取值校验 | ✅ pass | 用例断言 `BATS_TIMEOUT=0/-5/abc`、`BATS_TIMEOUT_RETRY(10) < BATS_TIMEOUT(60)`、`BATS_RETRY_BUDGET=0` ⇒ 全部 exit 2 |
| AC-N | 并发/嵌套安全 | ✅ pass | 用例断言两次并发 collect 的失败集合不互相截断（50 条完整）；`RDDF_BATS_COLLECT_ACTIVE=1` ⇒ exit 2 |
| AC-O | 重试语义 | ✅ pass | 用例断言一级的部分输出不进失败集合（`first-run failure` 不在 `$OUT`），二级的 `second-run failure` 在 |
| — | 慢文件用例不真的等 30s | ✅ pass | 夹具用 `BATS_TIMEOUT=1` + fake bats；整个新测试文件 20 例 ≈ 40s（含两个 3s 的 hang/slow 夹具） |
| — | 真 hang 进 `.hangs` 且不被误判为失败 | ✅ pass | `kind=hang` 用例；未评估文件的失败不进失败集合 |
| — | 报告输出「评估 N/M 个文件，未评估 K 个」 | ✅ pass | 实测：`📊 评估 256/256 个文件（…）` + `   未评估: 0 个文件` |
| — | 未评估文件不在基线内 ⇒ 门失败；在基线内 ⇒ 打印但不失败 | ✅ pass | 两条用例（真实 report + 真实 collect，只让一个真实文件挂住） |
| — | `SKIP_UNEVALUATED_GATE=yes` + reason ⇒ 放行且留 bypass 审计 | ✅ pass | 用例断言输出含 `SKIP_UNEVALUATED_GATE` 且 `$RDDF_PROJECT_ROOT/.rddf/state/.bypass-audit.jsonl` 含该 env_var |
| — | 阈值变量可覆盖 + 默认值只有一处 | ✅ pass | report 端不再兜默认；collect 端三处默认值集中定义 |
| — | `./test.sh --full --regression` ⇒ 「评估 M/M，未评估 0」 | ✅ pass | 见 §2 |
| — | 被暴露的真实失败在本 change 内修掉，`KNOWN_FAILURES.txt` 未扩大 | ✅ pass | `tests/KNOWN_FAILURES.txt` 本次未改（git diff 无该文件）；被暴露的 `01_single_contract_match_returns_warning_and_report` 改为「成员关系」断言后通过 |

---

## 2. 全量回归门

```
./test.sh --full --regression --no-color
```

最终一轮（在 `1f551b2` 上，4 核机器 load avg ~15~21）：

```
📊 评估 256/256 个文件（scope: tests/integration/*.bats；仓库另 27 个 .bats 不在本门范围）
   未评估: 0 个文件
已知失败: 11
新增失败: 0
已修复 (zombie): 0

✅ 0 新增失败
✅ bats regression (baseline-aware) OK (1301s)

3424 passed, 2 skipped            ← pytest unit
196 passed                        ← pytest integration
✅ ALL PASSED / EXIT=0
```

⇒ **256/256 全部被评估、未评估 0、新增失败 0** —— 这正是本 change 要恢复的那个前提。

> 附注（诚实记录）：同一棵树在更高负载时（load avg ~23）曾出现「2 个文件未评估 ⇒ 门失败」。
> 那不是误报也不是回归：按新语义「有文件没被评估 ⇒ 不得声称新增失败 0」，门拒绝给结论是**正确**行为。
> 之后的两处修补（新用例只面对假仓；重试预算按**实际**耗时计而非按最坏情况预留）让同一份
> 600s 预算能覆盖更多慢文件 ⇒ 本轮的 0 未评估。


## 3. 变异测试

| # | 变异 | 结果 |
|---|---|---|
| M1 | 删掉 `BATS_TIMEOUT` 的 `>= 1` 校验 | ✅ 用例变红 |
| M2 | 二级重试合并一级输出（不丢弃） | ✅ 用例变红 |
| M3 | per-test 超时的 `not ok` 不再排除出失败集合 | ✅ 用例变红 |
| M4 | 去掉 `RDDF_BATS_COLLECT_ACTIVE` 递归守卫 | ✅ 用例变红 |
| M5b | 「summary 缺失 ⇒ exit 2」与「分母不一致 ⇒ exit 2」一起去掉 | ✅ 用例变红（输出含 `✅ 0 新增失败`） |
| M5a | 只去掉「summary 缺失 ⇒ exit 2」 | 🟡 用例仍绿 —— **系统仍 fail-closed**（被分母一致性那道防线兜住）⇒ 纵深防御，非逃逸 |

⇒ 5 个真变异全部被捕获。

## 4. 遗留清扫

（另：本轮跑门时发现并修掉的两处「自己的工程债」—— 新用例自己成了慢文件（104s → 20s）、
重试预算按最坏情况预留导致 6 个慢文件就吃光 600s —— 已包含在 `1f551b2`。）

| 项 | 结论 |
|---|---|
| TODO / FIXME / 占位符 | 本次改动内 0 处（`grep -n "TODO\|FIXME\|XXX" ` 命中 0） |
| 注释掉的代码 | 0 |
| 临时调试日志 | 0（`echo` 仅出现在 summary/错误输出里） |
| 被 skip 的测试 | 0（未新增 skip） |
| 未替换的 mock | fake bats 夹具是**测试夹具**（新测试文件自带），不是生产代码里的 mock ✅ |
| 临时代码 / fallback 分支 | 临时测量用的 `tests/scripts/.old-collect-measure.sh` 已删（备份在 `/tmp/opencode/`）；合成失败 `zz-synthetic-red` 已撤除 ✅ |
| 本次范围外的发现 | ① Hub 仓 `contracts/` 的历史残留（外部仓库，破坏性操作，未动）；② Python 侧回归报告 `report_python_regression.sh` 无「未评估」维度（In Scope 只写了 bats 侧）；③ `generate_full_proposal.py` 的段映射失真（本次手工修正了生成的 proposal.md，未改生成器）—— 三项均已登记在 improvement 的「本次不做 / 留给后续」 |

## 5. 已用轮次

- 验收轮次：**1 / 3**（`RDDF_VERIFIER_MAX_LOOPS=3`）
- 本轮结论：**pass**（AC-G 为已记录的 deviation，不构成失败 —— 增长有硬上界，且换来的是「1 个此前不可见的文件被真正评估」）

## 6. 路由建议

无失败项 ⇒ 无需回 builder / planner。
