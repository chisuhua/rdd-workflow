# quick-fix-gate-flaky-tests

> 手工写的 rdd-quick 计划（未用 scaffold：三条修复的形状差异太大，骨架模板反而会掩盖它们）。

**Goal**: 修掉三个让**回归门随机变红**的测试缺陷 —— 它们都不是「代码错了」，而是「测试跑不完 / 跑得随机」，
门一旦判成「未评估」就会失败（`KNOWN_UNEVALUATED.txt` 是空的，且 CI 是 shrink-only ⇒ 不能靠豁免）。

**Architecture**: 三处都只动 `tests/`，不动任何产品代码：

1. `test_arch_env_check_extraction.bats`：原来两次 `cp -r "$REPO_ROOT"`（整个仓 208M / 17973 文件，含
   `.git`）+ 11 次在**真仓**里跑 helper ⇒ 空闲 66s、机器一忙就 >150s（门的 per-file 上限
   30s + 120s 重试）⇒ 判「未评估」⇒ 门红。改法：`setup_file()` 建一份**最小拷贝**
   （skills / _lib / docs / .rddf/roadmap / openspec = 24M / 2802 文件 / 2s），helper 在拷贝里 1s。
2. `test_regression_gate_evaluation.bats` 的 `collect()` 辅助函数写的是
   `BATS_TIMEOUT="${BATS_TIMEOUT:-1}"` ⇒ **继承外层 env**。谁在机器忙的时候把 `BATS_TIMEOUT`
   调大（`report_regression.sh` 头部就是这么建议的），这个文件就变成 661s 的慢文件 ⇒ 又一次「未评估」。
   改法：辅助函数里**固定** 1s（需要特定值的用例本来就在 `run env` 那行显式传）。
3. `test_concurrent_update_serializes`：用 `time.sleep(0.3)` 当同步手段（等第一个子进程写完再起第二个）。
   子进程冷启动 ~0.05s，余量看似够，但**满载时**（全量门自己就在压机器）0.3s 不够 ⇒ 第二个子进程
   撞 `LOCK_NB`（fail-fast）直接退出 1 ⇒ 用例随机红。改法：两个子进程**同时**起，**子进程自己**
   在锁冲突时重试（真实调用方就是这么做的）⇒ 结果不再依赖调度。

**Tech Stack**: bash / bats 1.13、Python 3.12 + pytest。

---

### Task 1: `test_arch_env_check_extraction.bats` 改用最小拷贝

- [x] **Step 1: Write the failing test** —— 判据就是这个文件本身跑不完：
      `time bats tests/integration/test_arch_env_check_extraction.bats` 的耗时必须 ≤ 30s
      （门的 per-file 预算），否则它会被判「未评估」⇒ 门红。
- [x] **Step 2: Run test to verify it fails** —— 改前：空闲 **66s**；负载下 >150s
      （实测 `rc=124 elapsed=180s last_tap=8 kind=slow`）⇒ 判据不成立。
      逐用例计时定位：9 个「在真仓跑 helper」各 ~3s（`orchestrator_run` 两次 ≈ 1.9s 是大头），
      2 个「整仓拷贝 + 拷贝里跑 helper」各 26~47s（拷贝 18k 文件 + helper 在拷贝里也慢）。
- [x] **Step 3: Write minimal implementation** —— `copy_minimal_repo()`：只拷 helper 会读的子树
      （skills / _lib / docs / .rddf/roadmap / openspec = 24M / 2802 文件 / 2s）；
      `setup_file()` 建一份共享拷贝，9 个用例在拷贝里跑 helper，2 个会改树的用例各自建一份。
- [x] **Step 4: Run test to verify it passes** —— 13/13 ok，**66s → 23s**（进 30s 预算 ⇒ 不再触发重试）。
      反向变异：把 helper 的 `📋 活动 changes:` 标签改掉 ⇒ 用例 7 红 ⇒ 拷贝里的环境仍然真的在测那段代码；
      恢复后 13/13 绿、产品文件零 diff。
- [x] **Step 5: Defer commit**

### Task 2: `test_regression_gate_evaluation.bats` 的 `collect()` 不再继承外层超时

- [x] **Step 1: Write the failing test** —— 判据：带外层 `BATS_TIMEOUT=180 BATS_TIMEOUT_RETRY=300`
      跑这个文件，耗时必须 ≤ 30s。
- [x] **Step 2: Run test to verify it fails** —— 改前 **661s**（门判「未评估」）。定位：`collect()` 里的
      `${BATS_TIMEOUT:-1}` 把外层值吃了，而 fake bats 的 fixture 本来只要 1s。
- [x] **Step 3: Write minimal implementation** —— 辅助函数里固定 `BATS_TIMEOUT=1 BATS_TIMEOUT_RETRY=1`
      （需要特定值的用例在自己的 `run env` 行显式传，不受影响）。
- [x] **Step 4: Run test to verify it passes** —— 带同样的外层 env 跑 ⇒ **20s**，20/20 ok。
- [x] **Step 5: Defer commit**

### Task 3: `test_concurrent_update_serializes` 去掉 sleep 同步

- [x] **Step 1: Write the failing test** —— 判据：这个用例在**负载下**必须稳定通过
      （16 个忙循环 / 4 核，连跑 15 次 0 失败）。
- [x] **Step 2: Run test to verify it fails** —— 改前同条件 **pass 7 / fail 8**。定位：
      `time.sleep(0.3)` 是时序假设；子进程冷启动 ~0.05s，满载时超过 0.3s ⇒ 第二个子进程撞
      `LOCK_NB`（`_store.with_file_lock` 是 fail-fast）⇒ 子进程退出 1 ⇒ 用例红。
- [x] **Step 3: Write minimal implementation** —— 两个子进程**同时**起；**子进程**在
      `Could not acquire lock` 时重试（最多 200 次 × 50ms，真实调用方就是这么做的）。
- [x] **Step 4: Run test to verify it passes** —— 同条件连跑 15 次 ⇒ **pass 15 / fail 0**；
      空闲 5/5 ok；最终 offset 仍是 314（单调守卫 ⇒ 谁先写都不影响结论）。
- [x] **Step 5: Defer commit**

## Acceptance

- [x] AC-1: `bats tests/integration/test_arch_env_check_extraction.bats` ⇒ 13/13 ok 且**耗时 ≤ 30s**
      （实测 23s；改前 66s）
- [x] AC-2: `bats tests/integration/test_regression_gate_evaluation.bats` ⇒ 20/20 ok；
      带 `BATS_TIMEOUT=180` 跑仍 ≤ 30s（实测 20s；改前 661s）
- [x] AC-3: `pytest tests/unit/test_update_last_seen_offset.py` ⇒ 5/5 ok；
      负载下连跑 15 次 0 失败（改前同条件 8/15 失败）
- [x] AC-4: 三处都**只改 tests/**（`git diff --stat` 不含 `_lib/`、`skills/`、`.github/`）
- [x] AC-5: 隔离门 `bash tests/scripts/check_test_isolation.sh` ⇒ exit 0
- [x] AC-6: `./test.sh --full --regression` ⇒ `未评估 0` + `新增失败 0` + `ALL PASSED`

## 本次不做（记录）

1. **`KNOWN_UNEVALUATED.txt` 仍然保持为空** —— CI 断言它只减不增（shrink-only），所以「把慢文件列进去」
   这条路被门本身堵死；唯一的解法是让文件跑得完（本项做的就是这个）。
2. **`collect_bats_failures.sh` 的 per-file/per-test 超时值不改**（30s / 120s 是 CI 口径，
   改它会改变全仓的失败判定面）。
3. **其它慢文件未排查** —— 本项只处理「已经让门红过」的三个；下次门红时按同一方法定位。
