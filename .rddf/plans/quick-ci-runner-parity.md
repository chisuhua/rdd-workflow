# quick-ci-runner-parity

**Goal**: CI 从「永远红」走到「全绿」—— 逐层打通 `Python unit tests` → `Python integration tests`
→ `Bats smoke`。三层的失败**没有一条是产品逻辑错**，全部是「runner 是白板机器，而测试假设了
开发机上由 `install.sh --global` 造成的环境」。

**Architecture**: 两类处置 ——
① **补齐 runner 环境**（等价于开发机的全局安装）：job 级 `PYTHONPATH`（代替
`rdd-workflow.pth`）、`skills/cli` 上 PATH（代替 `~/.local/bin/rddf` 软链）、
openspec CLI、git 身份；
② **修正与仓库自身策略冲突的门**：CI 的裸 `bats tests/ --recursive` 与
`KNOWN_FAILURES.txt`（11 条已接受失败）互斥 ⇒ 收窄为 integration/ 之外的范围，
integration/ 交给 baseline-aware 的回归门。

**Tech Stack**: GitHub Actions YAML、bats、pytest。

---

### Task 1: unit tests（33 → 0）

- [x] 见提交 `48e93af`：`_clear_ci_markers()`（6 个 CI marker）、doc 契约缺文件 skip、
  `skills/_lib.__path__` 补仓根 `_lib`、CI 装 openspec CLI + 配置 git 身份。

### Task 2: integration tests（3 → 0）

- [x] **Step 1: failing test** —— 判据：`python3 -m skills._lib.cli` 在临时仓 cwd 下可执行。
- [x] **Step 2: verify fails** —— CI：`ModuleNotFoundError: No module named 'skills'`；本地用
  `python3 -S`（跳过 site-packages 的 `rdd-workflow.pth`）复现同一错误。
- [x] **Step 3: minimal fix** —— 3 个 env 块补 `PYTHONPATH=<repo root>`。
- [x] **Step 4: verify passes** —— 该文件 3 passed；机制验证（`-S` + PYTHONPATH 通过）。

### Task 3: bats（134 → 0 新增失败）

- [x] **Step 1: failing test** —— 判据：非 integration 范围与 integration 范围都应只有
  `KNOWN_FAILURES.txt` 里的已接受失败。
- [x] **Step 2: verify fails** —— CI 134 个失败：113 × `No module named 'skills'/'_lib'`、
  1 × `bash: /skills/rdd-builder/…`、3 × `cd: null directory`，其余是 `KNOWN_FAILURES` 里的
  已接受失败（被裸跑当真错）。
- [x] **Step 3: minimal fix** —— job 级 `PYTHONPATH`；`skills/cli` 上 PATH；
  bats smoke 收窄为非 integration 范围（`find` 派生）；夹具 fixture 路径改为派生。
- [x] **Step 4: verify passes** —— CI run 44488400155 28 个 step 全 OK。

## Acceptance

- [x] AC-1: `Python unit tests` 在 CI 转绿（run 44476608214 step 14 success）
- [x] AC-2: `Python integration tests` 在 CI 转绿（run 44477550479 step 16 success）
- [x] AC-3: doctor structural/advisory 在 CI 转绿（同上 step 17/18 success）
- [x] AC-4: `Bats smoke`（非 integration 范围）在 CI 转绿
- [x] AC-5: baseline 回归门 + e2e smoke + 两个 shrink-only 在 CI 转绿（run 44488400155 全绿）
- [x] AC-6: 本地：非 integration 的 14 个 bats 文件全绿（6s）；`test_arch_env_check_extraction.bats` 13/13；
  `test_ci_local_mirror.py` 11 passed

## 本次不做（记录）

1. **11 条 `KNOWN_FAILURES`**（doc-drift / script-drift）仍存在 —— 它们是基线，不是本轮目标；
   裸跑 bats 把它们当真错才是缺陷。
2. **`tests/e2e/agent/**`** 需要 `RDDF_AGENT_E2E=1`，CI 不跑（nightly 工作流负责）。
3. **`create_skeleton_change` 缺 CLI 时崩溃**（文档说可降级）另案。
