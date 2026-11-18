# fix-path-anchoring-residue — 验收报告

- **change**: `openspec/changes/fix-path-anchoring-residue/`（`openspec/` 在本仓是 gitignored，工件不入库）
- **基线**: `deab479`（`origin/master`）
- **判据来源**: `proposal.md` 的 `## Acceptance`（AC-1…AC-12）为第 2 优先级；第 3 优先级为本 change 自己声明的契约
- **角色**: builder 自查（verifier 契约 1–5 步）；未委托 `rdd-verifier` skill（本 change 不是 rdd-builder pipeline 产物，
  无 P3 archive gate 触发 ⇒ 分流三条件不满足，走本地验收）
- **已用轮次**: 1（`needs-revision` 0 次 / `ac-fail` 0 次）

## 逐条判定

| AC | 结论 | 证据 |
|---|---|---|
| AC-1 三个 gate check 读 `ctx["project_root"]` | **pass** | `tests/unit/test_gate.py::test_changes_committed_reads_project_root_not_cwd` / `::test_artifacts_complete_reads_project_root_not_cwd` / `::test_deps_analyzed_reads_project_root_not_cwd`。改前实测 `_check_changes_committed` 在 `project_root=<假仓>`、`cwd=真仓` 时返回 `(False, None)`；改后 `(True, None)`。`pytest tests/unit/test_gate.py` ⇒ 24 passed |
| AC-2 `project_root` 缺省时行为不变 | **pass** | `::test_artifact_checks_default_to_cwd_when_project_root_absent`（ctx 不含 `project_root`，cwd 有 artifact ⇒ 两个 check 均 `(True, None)`）；`pytest tests/integration/test_gate_transition.py` ⇒ 15 passed（全部传 `{}`） |
| AC-3 planner_stage_* 不再 rc=2 报 not found | **pass** | `tests/integration/test_root_anchoring_residue.bats` 用例 1/3（`PROJECT_ROOT=<假仓>`、`cwd=真仓`）；反向对照用例 2（cwd 有该 change 而 `PROJECT_ROOT` 没有 ⇒ 仍 rc=2 + not found）证明它不再读 cwd |
| AC-4 门控1 认 `$PROJECT_ROOT/.rddf/roadmap.md` | **pass** | 用例 4（cwd 无 roadmap、`PROJECT_ROOT` 有 ⇒ 输出含「门控2」且不含「门控1」）+ 用例 5（`PROJECT_ROOT` 无 roadmap，真仓有也不放行 ⇒ rc=2 + 门控1） |
| AC-5 `roadmap_migrate.sh` 既有测试全绿 + diff 只有前缀 | **pass** | `bats tests/integration/test_roadmap_migrate.bats` ⇒ 6/6 ok；`git diff skills/roadmap/scripts/roadmap_migrate.sh` 只有 5 个常量 + 4 处路径前缀（无控制流变化，`cd "$PROJECT_ROOT"` 保留） |
| AC-6 审计落 `${state_root:-$tasks_root}` | **pass** | 用例 6：`cwd`=真仓、`tasks_root`=假 worktree ⇒ 假**主仓**新增恰好 1 条 `SKIP_RDD_VERIFIER`；真仓行数不变；worktree 无该文件。手工复现同结论 |
| AC-7 `test_rdd_quick_isolation.bats` 全绿（含 recapture） | **pass** | `bats tests/integration/test_rdd_quick_isolation.bats` ⇒ 4/4 ok；`LOCKED_ARCHIVE_SH` 由 `420baf4…` → `91820f2…`，附第 10 次 recapture 注记 |
| AC-8 单 check 在默认扫描根下 exit 0 | **pass** | `RDDF_ISOLATION_ONLY=check_no_unanchored_repo_paths bash tests/scripts/check_test_isolation.sh` ⇒ exit 0（默认根含新增两个目录） |
| AC-9 隔离门全套 exit 0 | **pass** | `bash tests/scripts/check_test_isolation.sh` ⇒ `✅ No test isolation violations`，exit 0 |
| AC-10 新契约测试全绿 | **pass** | `bats tests/integration/test_root_anchoring_residue.bats` ⇒ 6/6 ok |
| AC-11 全量门 | **pass（含环境修正，见下）** | 见「全量门」段 |
| AC-12 不动 `KNOWN_FAILURES` / `.github/**` | **pass** | `git status --short` 无 `tests/KNOWN_FAILURES.txt`、无 `.github/**` |

## 反向变异（证明契约测试不是空转）

把三处修复**退回改前形态**（`archive.sh` 去掉 `RDDF_PROJECT_ROOT` 前缀；两个 planner 脚本的路径退回 cwd 相对；
门控1 退回相对路径），跑同一个 bats 文件：

```
变异后：not ok 1 … not ok 6      （6/6 全红）
恢复后：ok 1 … ok 6              （6/6 全绿）
```

第一次写用例时用例 4 是**假绿**（它只断言「输出不含门控1」，而改前 cwd 恰好有 roadmap 也会满足）——
变异测试把这条抓出来了，改成「cwd 无 roadmap、PROJECT_ROOT 有 ⇒ 必须走到门控2」后才真正有判别力。
同理用例 1 加了「handoff 落在假仓、真仓那份不得被碰」的写方向断言。

## 全量门（三次运行，逐次说明 —— 不合并成一句「全绿」）

### 运行 1：`./test.sh --full --regression`（默认参数，= CI 口径）

```
✅ test isolation gate OK (1s)
📊 评估 255/258 个文件 · 未评估 3 个文件
已知失败 11 · 新增失败 0
❌ 未评估文件不在 KNOWN_UNEVALUATED.txt 内 ⇒ 门失败
❌ pytest unit FAILED（1 failed, 3427 passed）
✅ pytest integration OK（196 passed）
```

两个红都不是本 change 引入的失败，分别处置：

1. **`pytest unit`**：`test_no_hardcoded_workspace_paths.py` 报本 change 的 `proposal.md:23`
   写了当前仓库绝对路径。该守卫的 `WHITELIST_PREFIXES` 只含 `openspec/changes/archive/`，
   **不含**活动 change 目录 ⇒ 工件里不能出现仓库绝对路径。改成不带绝对路径的写法后
   `pytest tests/unit/test_no_hardcoded_workspace_paths.py` ⇒ **3 passed**。
2. **`bats regression` 的 3 个未评估文件**（`rc=124 elapsed=30s`）：当时 load average **17**（4 核），
   `collect_bats_failures.sh` 的 per-file 默认上限 30s 不够。逐个单跑（无 per-file 上限）：

   | 文件 | 结果 |
   |---|---|
   | `test_known_failures_baseline.bats` | 9 ok / 0 not ok |
   | `test_no_spec_workflow_residue.bats` | 1 ok / 0 not ok |
   | `test_lightweight_branch_and_archive.bats` | 25 ok / 0 not ok |

### 运行 2：`BATS_TIMEOUT=180 BATS_TIMEOUT_RETRY=300 ./test.sh --full --regression`

```
📊 评估 257/258 个文件 · 未评估 1 个文件
已知失败 11 · 新增失败 0
❌ test_regression_gate_evaluation.bats rc=124 elapsed=661s
❌ pytest unit FAILED（1 failed: test_update_last_seen_offset.py::test_concurrent_update_serializes）
✅ pytest integration OK（196 passed）
```

这次的两个红都是**我的环境调整自己造成的**，不是代码问题：

1. `test_regression_gate_evaluation.bats` 的 `collect()` 辅助函数写的是
   `BATS_TIMEOUT="${BATS_TIMEOUT:-1}"` —— 它会**继承**外层 env。我把外层调到 180 之后，
   它的内部 fixture 每个要等 180s（原本 1s）⇒ 该文件自己被 per-file 上限砍掉。
   单跑（默认 env）⇒ **20 ok / 0 not ok**。
   ⚠ 这是该测试自身的脆弱点（应为 `BATS_TIMEOUT=1` 而不是 `${BATS_TIMEOUT:-1}`），**记录，不修**。
2. `test_concurrent_update_serializes` 用 `time.sleep(0.3)` 当同步手段（等第一个子进程写完再起第二个）。
   全量门把机器压满时 0.3s 不够 ⇒ 第二个子进程撞上 `LOCK_NB` fail-fast ⇒ 断言失败。
   它**与本 change 无关**（`git diff --name-only` 不含 `test_update_last_seen_offset.py`
   与 `rddf_session.py`）；机器空闲后连跑 **8 次全过**；压缩负载时 3 次里失败 1 次。
   ⚠ 记录为本仓的一个既有 flake（`KNOWN_FAILURES.txt` 只管 bats，管不到 pytest），**记录，不修**。

> 关于 `BATS_TIMEOUT`：它是 `collect_bats_failures.sh` 文档化的 per-file 超时，`report_regression.sh`
> 头部明确写了 `BATS_TIMEOUT_RETRY=300 report_regression.sh` 的用法。调大只影响**单文件最长允许耗时**，
> 不改失败判定口径；`SKIP_UNEVALUATED_GATE`（CI 会断言的真正旁路）全程**未使用**。

### 运行 3（最终判定依据，load average 4.7）

```
✅ test isolation gate (anti-pollution) OK (2s)
📊 评估 258/258 个文件 · 未评估 0 个文件
已知失败 11 · 新增失败 0 · 已修复 (zombie) 0
✅ bats regression (baseline-aware) OK (1099s)
✅ pytest unit OK (3428 passed, 2 skipped, 116s)
✅ pytest integration OK (196 passed, 165s)
✅ ALL PASSED   EXIT=0
```

## 遗留清扫

本次范围内**无** TODO / 半截实现 / 注释掉的代码 / 临时调试日志 / 被 skip 的测试 / 未替换的 mock。

范围外记录（不修，已在 `proposal.md` 的「本次不做 / 实施期间的新发现」落盘）：

1. `_check_openspec_validate`（`gate.py:222`）与两处 `openspec validate` 子进程（`:207` / `:239`）
   仍以 cwd 运行 —— 同一类缺陷，但改它会改变门的**判定结果**，需要独立的测试 + 变异验证。
2. `audit_bypass_log` 的 `actor` / `codebase_commit` 仍取自 cwd 的 git（`_lib/bypass_audit.sh:59-64`）。
3. `check_no_unanchored_repo_paths` 未纳入 `_lib`（实测 100+ 命中绝大多数是消息文本 / 模板字符串）。
4. **`test_regression_gate_evaluation.bats` 的 `collect()` 会继承外层 `BATS_TIMEOUT`**
   （`BATS_TIMEOUT="${BATS_TIMEOUT:-1}"`）—— 它假定「默认 1s」，外层一旦调大就变成分钟级
   （实测 661s ⇒ 被它自己的 per-file 上限砍掉）。应写成固定 `BATS_TIMEOUT=1`。**记录，不修。**
5. **`test_concurrent_update_serializes` 用 `time.sleep(0.3)` 当同步手段**（等第一个子进程写完
   再起第二个）⇒ 机器重载时第二个子进程撞 `LOCK_NB` fail-fast ⇒ 随机红。空闲时 8/8 过、
   压缩负载时 3 次里红 1 次。这是本仓**既有** flake（`KNOWN_FAILURES.txt` 只管 bats，
   管不到 pytest）⇒ 全量门会随机红。**记录，不修。** 建议的修法：`p_first.communicate()`
   之后再 `_spawn(314)`（保留「先写先赢、后者不得回滚」的原意，去掉时序假设）。

## 需要如实说明的两点（不夸大成「修了线上 bug」）

1. **`_lib/gate.py` 的修复目前对生产行为零影响**：`verify_transition` 的生产调用点只有
   `gate.py:516`（传 `{}`），`project_root` 缺省即 `"."`。真正在传 `project_root` 的是测试。
   所以这次修的是 **ctx 契约的自洽性**（同文件另外 5 个 check 已经在用它），
   以及给下一个传 `project_root` 的调用方去掉一个陷阱。
2. **`roadmap_migrate.sh` 不是 bug 修复**：改前运行期就是对的（`cd "$PROJECT_ROOT"` 在前）。
   改绝对常量只是让静态门能看见「已锚定」，避免为它开豁免。

## 失败项与路由建议

无失败项。上面第 1 次全量门的两个红都是**可判定的环境 / 工件问题**，已分别处置（工件修正 + 环境修正），
不属于 `implementation_gap`，也不属于 `proposal_drift`（AC 本身没写错）。

## 最终结论

**PASS（AC-1…AC-12 全过）。**

运行 3 是唯一一次「参数 = CI 口径 且 机器不超载」的运行，也是判定依据：
`258/258 评估 · 未评估 0 · 新增失败 0 · ALL PASSED EXIT=0`。

前两次运行的两个红都已被**独立复验**为环境 / 工件问题（守卫拒收工件里的绝对路径、per-file 30s 上限
在 load 17 下不够、一个用 `sleep 0.3` 当同步手段的既有 flake），不是本 change 引入的失败，
且没有任何一项是「修了下游才绿」——改动面（9 个文件，全在 `_lib/`、`skills/*/scripts/`、`tests/`）
在三次运行之间没有变化，只有 `proposal.md` 的一行工件文字被改过。

> 证据的可复核性：三次日志分别为 `/tmp/opencode/fix-path-anchoring-residue-full{,2,3}.log`（临时文件，未入库）。
> 关键数字已在本报告里抄录；如需复核请重跑 `./test.sh --full --regression`。
