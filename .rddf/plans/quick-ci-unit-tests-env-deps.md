# quick-ci-unit-tests-env-deps

**Goal**: CI 第一次跑到 `Python unit tests` 后暴露 33 个失败 —— 全部是「测试假设了开发机
才有的环境」（openspec CLI / git 身份 / CI marker / gitignored 的 openspec 目录 / 依赖
全局安装的 `skills._lib`）。让这些用例在干净 runner 上也能成立，CI 才可能真的绿。

**Architecture**: 分两类处置 ——
① **环境前提**（runner 白板）：openspec CLI 与 git 身份补进 CI，并在 `test.sh` 的
`NOT_MIRRORED` 登记（本地开发机本来就有）；
② **测试/解析缺陷**（不该依赖机器）：CI marker 清全量、缺文件时 skip、`skills._lib.__path__`
补上仓根 `_lib`（shim 仍优先 ⇒ 身份合并不变）。

**Tech Stack**: GitHub Actions YAML、pytest、Python import machinery。

---

### Task 1: CI 环境前提（openspec CLI + git 身份）

**Files:** Modify: `.github/workflows/test.yml` / `test.sh`

- [x] **Step 1: Write the failing test** —— 判据：干净 runner 上 `create_skeleton_change` 相关用例应通过。
- [x] **Step 2: Run test to verify it fails** —— CI run 44471724723：16 个 `FileNotFoundError: 'openspec'`、4 个 `git commit` exit 128。
- [x] **Step 3: Write minimal implementation** —— 新增两步：`npm install -g @fission-ai/openspec@1.14.3` + `git config --global user.{email,name}`；`NOT_MIRRORED` 加两条。
- [x] **Step 4: Run test to verify it passes** —— 本机有 CLI/身份时这些文件全绿；白板克隆补上 git 身份后 4 个 branch 用例 6 passed。
- [x] **Step 5: Defer commit**

### Task 2: 测试侧环境假设

**Files:** Modify: `tests/unit/test_post_flow_analysis.py` / `tests/unit/test_doc_contracts.py`

- [x] **Step 1: Write the failing test** —— 判据：`CI=true GITHUB_ACTIONS=true` 下 6 个 should_auto_submit/report_flow_bug 用例与 4 个 spec 契约用例应通过。
- [x] **Step 2: Run test to verify it fails** —— 实测：marker 用例 `assert False is True`（`is_ci_environment()` 认 6 个 marker）；spec 用例 `FileNotFoundError: …/openspec/specs/general/spec.md`。
- [x] **Step 3: Write minimal implementation** —— `_clear_ci_markers()` 统一清 6 个 marker；`requires_general_spec` skipif（`openspec/` 是 gitignored 本地工件）。
- [x] **Step 4: Run test to verify it passes** —— `test_post_flow_analysis.py` 31 passed（CI 环境）；`test_doc_contracts.py` 本地 13 passed / 无 `openspec/` 时 9 passed + 4 skipped。
- [x] **Step 5: Defer commit**

### Task 3: `skills._lib.X` 不再依赖机器级全局安装

**Files:** Modify: `skills/_lib/__init__.py`

- [x] **Step 1: Write the failing test** —— 判据：`HOME` 下无 `~/.agents/skills/_lib` 时 `import skills._lib.workflow_synthesizer` 应成功。
- [x] **Step 2: Run test to verify it fails** —— 旧代码在白板克隆里 `ModuleNotFoundError: No module named 'skills._lib.workflow_synthesizer'`（monitor 子进程因此拿不到 child progress）。
- [x] **Step 3: Write minimal implementation** —— `__path__` 依次为 `skills/_lib/`（shim，**必须第一**）→ 仓根 `_lib/` → 全局 fallback。
- [x] **Step 4: Run test to verify it passes** —— `HOME` 无全局安装时解析到 `<repo>/_lib/workflow_synthesizer.py`；`test_p1_1_identity_merge.py` 12 passed（身份合并未受影响）。
- [x] **Step 5: Defer commit**

## Acceptance

- [x] AC-1: 白板克隆 + `CI=true GITHUB_ACTIONS=true` + 无 gitconfig + 无 openspec CLI 下，剩余失败只剩两类（openspec CLI 依赖 / git 身份），均已由 CI 步骤覆盖
- [x] AC-2: 本机 `pytest tests/unit/` ⇒ 3443 passed / 3 skipped（无回归）
- [x] AC-3: `./test.sh --gates` 4 道门全绿；`test_ci_local_mirror.py` 12 passed（两个新 step 已登记）
- [x] AC-4: `test_post_flow_analysis.py` 在 `GITHUB_ACTIONS=true` 下 31 passed
- [x] AC-5: 无 `openspec/` 时 `test_doc_contracts.py` 4 skipped（其余照跑）
- [x] AC-6: push 后 CI 的 `Python unit tests` 步骤实际转绿（本地无法替代）

## 本次不做（记录）

1. **`test_guide_close_can_read_project_root_in_trap_context` 的 30s 超时**：本地（含白板克隆 + CI 环境变量）1.2s 通过，无法复现 ⇒ 观察项，复现再查。
2. **68 个 `_lib/` 模块没有 `skills/_lib/` shim**：本次只让解析不再依赖全局安装；是否补 shim / 是否统一 import 风格属另一案。
3. **`create_skeleton_change` 在缺 CLI 时直接崩溃**（文档说「CLI 不可用则手写」）：产品侧降级行为另案，本次只补环境。
