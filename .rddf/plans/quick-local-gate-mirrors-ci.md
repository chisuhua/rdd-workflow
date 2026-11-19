# quick-local-gate-mirrors-ci

**Goal**: 让 `./test.sh` 成为「本地门」—— 镜像 CI 的静态门（ruff / mypy strict / doctor structural），
并把 lint 口径从「工具版本的默认规则集」拿回到配置里（master 的 CI 因 ruff 版本漂移一直是红的，
而本地全绿 ⇒ 变红无人发现）。

**Architecture**: 三块 ——
① `pyproject.toml` 显式 `select` + `requirements.txt` 钉版（口径与工具版本解耦）；
② doctor 新增 `--gate structural`（10 类清单从 CI yml 下沉到 `doctor_main.py`）⇒ CI 与本地门调**同一条命令**；
③ `test.sh` 新增 `--gates` 模式与 3 个门函数，`NOT_MIRRORED` 台账 + `tests/unit/test_ci_local_mirror.py` 三层契约防漂移。

**Tech Stack**: bash、Python 3.12 + pytest + PyYAML、ruff 0.15/0.17、mypy 2.3。

---

### Task 1: lint 口径显式化（让 CI 的 Ruff step 转绿）

**Files:** Modify: `pyproject.toml` / `requirements.txt` / `skills/_lib/iteration/__init__.py`
**Test:** `ruff check skills/_lib/`（两个版本都要绿：本地 0.15.22 与 CI 会装的 0.17.5）

- [x] **Step 1: Write the failing test** —— 判据：`ruff check skills/_lib/` 在 **0.17.5** 与 **0.15.22** 下都必须绿。
- [x] **Step 2: Run test to verify it fails** —— 0.17.5 ⇒ `Found 36 errors`（25 I001 / 8 S102 / 1 S603 / 3 UP* / 1 E402）；0.15.22 ⇒ 1 error（E402）。
- [x] **Step 3: Write minimal implementation** —— `select = ["E4","E7","E9","F"]`（= 注释里一直写的意图）+ ruff/mypy 钉版 + `import json as _json` 提到文件顶部。
- [x] **Step 4: Run test to verify it passes** —— 两个版本都 `All checks passed!`。
- [x] **Step 5: Defer commit**

### Task 2: doctor `--gate structural`（清单单一真源）

**Files:** Modify: `skills/rdd-doctor/scripts/doctor_main.py` / `.github/workflows/test.yml`
**Test:** `bash skills/rdd-doctor/scripts/doctor.sh --gate structural`（10 行逐类输出 + 聚合 rc）

- [x] **Step 1: Write the failing test** —— 判据：`--gate structural` 不存在（当前只有 `--category/--check`），且 CI 的 10 类清单只在 yml 里有一份。
- [x] **Step 2: Run test to verify it fails** —— `doctor.sh --gate structural` ⇒ argparse 报 `invalid choice`。
- [x] **Step 3: Write minimal implementation** —— `_GATES`（structural 10 类 / advisory 4 类，advisory 不拦）+ `run_gate()`（逐类一行渲染 + rc>=2 聚合 + `GITHUB_ACTIONS` 时的 `::error/::warning` 注解）+ yml 两段内联循环换成一条命令。
- [x] **Step 4: Run test to verify it passes** —— structural 10 类全绿（arch-audit 5 warning ⇒ ⚠️ 不拦）；advisory 4 类全绿且恒不拦。
- [x] **Step 5: Defer commit**

### Task 3: `test.sh` 镜像 4 道门

**Files:** Modify: `test.sh` / `.gitignore` / `AGENTS.md`
**Test:** `./test.sh --gates`（4 道门 ~4s）、`./test.sh --quick`（105s）

- [x] **Step 1: Write the failing test** —— 判据：`./test.sh --gates` 不存在；且把 ruff 弄红时 `./test.sh` 必须红。
- [x] **Step 2: Run test to verify it fails** —— 改前 `--gates` ⇒ `unknown mode`（参数报错）；ruff 变红时本地门仍绿。
- [x] **Step 3: Write minimal implementation** —— `run_ruff_gate` / `run_mypy_gate` / `run_doctor_structural_gate` / `run_local_gates` + `--gates` mode + `--quick` 加 ruff + `--full` 跑 4 道 + 版本警告 + `SKIP_LOCAL_GATES` 审计旁路 + `FAILED` 自增修复 + `.gitignore` 缓存 + 三处文案。
- [x] **Step 4: Run test to verify it passes** —— `--gates` ALL PASSED（4s）；变异（ruff 报错 / doctor 出 CRITICAL）⇒ 门红，恢复 ⇒ 绿。
- [x] **Step 5: Defer commit**

### Task 4: 防漂移契约

**Files:** Create: `tests/unit/test_ci_local_mirror.py`

- [x] **Step 1: Write the failing test** —— 判据：把 `test.sh` 里一条门命令改掉 ⇒ 契约测试必须红。
- [x] **Step 2: Run test to verify it fails** —— 变异（`ruff check skills/_lib/` → `skills/_lib_other/`）⇒ `test_mirrored_command_present_in_both_files` 红。
- [x] **Step 3: Write minimal implementation** —— 三层：命令镜像（9 条片段同时出现在两文件）/ 覆盖台账（未被覆盖的 CI step 必须进 `NOT_MIRRORED`）/ 反向（`NOT_MIRRORED` 每项必须存在）。
- [x] **Step 4: Run test to verify it passes** —— 12 passed；恢复后也 12 passed。
- [x] **Step 5: Defer commit**

## Acceptance

- [x] AC-1: `ruff check skills/_lib/` 在 0.15.22 与 0.17.5 下**都**绿（口径与工具版本解耦）
- [x] AC-2: `./test.sh --gates` ⇒ 4 道门全绿（隔离门/ruff/mypy/doctor），实测 ~4s
- [x] AC-3: 门能变红：ruff 变异 ⇒ 红；doctor 出 CRITICAL ⇒ 红；恢复 ⇒ 绿
- [x] AC-4: `tests/unit/test_ci_local_mirror.py` 12 passed；破坏门命令 ⇒ 该测试红
- [x] AC-5: `./test.sh --quick` ⇒ 105s ALL PASSED；`./test.sh --full --regression` ⇒ 258/258 · 未评估 0 · 新增失败 0 · ALL PASSED
- [x] AC-6: `rddf doctor` ⇒ 0 CRITICAL / 8 WARNING（基线）；隔离门 exit 0
- [x] AC-7: 三处文案（test.sh 头注释 / print_help / AGENTS.md）一致且耗时为实测值 + 测量日期

## 本次不做（记录）

1. **CI 的两个 shrink-only step 仍红**：`git show origin/master:…` 在 `fetch-depth: 1` 的浅克隆里取不到基线 ⇒ 当前文件全被判「新增」。修它要给 checkout 加 `fetch-depth`，属 CI workflow 变更 ⇒ 另案。
2. **lint/type 门的覆盖漏洞**：`ruff check skills/_lib/` 只查 shim 层（真实实现 `_lib/` 不在任何 lint 门内）；`mypy --strict skills/_lib/core/` 只看到 0-def shim（真实实现 `_lib/core/`）⇒ mypy 门近乎空转。扩大覆盖会改 CI 的检查面 ⇒ 另案。
3. **37 个被推迟的发现**（25 I001 / 8 S102 / 1 S603 / 3 UP*）⇒ `.rddf/improvements/fix-lint-deferred-findings.md`（含「不许用 `ruff --fix` 批量修 shim」的约束）。
