---
优先级: P1
来源: "rdd-doctor 内部 SKILL.md 漂移 + check 子目录 _PROJECT_ROOT 算浅一层 bug + 仓库内 /workspace/project/rdd-workflow 硬编码路径大清查"
阶段: v2.2
分类: doc-fix, bug-fix, code-quality
类型: bug
特性: doc-drift-cleanup
---
**优先级**: P1 | **来源**: 用户调研 + rdd-doctor 自身 16 项 bats 集成测试失败根因分析（2026-10-07）
**阶段**: v2.2 | **分类**: doc-fix + bug-fix + code-quality
**类型**: bug | **特性**: doc-drift-cleanup

> **范围定位**: 一次清理三处耦合问题：(a) rdd-doctor SKILL.md 类别表与实际 `_CHECKERS` 字典严重漂移（8→18）；(b) `skills/rdd-doctor/scripts/checks/*.py` 中 4 个文件 `_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent` 少算一层 → 任何在 `<repo_root>` 下运行的 doctor 都立即 `ModuleNotFoundError: No module named '_lib.objective'`；(c) 仓库内 30+ 处活跃代码 hardcode `/workspace/project/rdd-workflow`，项目迁移后全部断链。
>
> **不重复**: 现有 `KNOWN_FAILURES.txt` 标注的"2 doctor_main tests assert ==10"会被本提案自然消解；不在本提案主动碰 `KNOWN_FAILURES.txt` 本身（按 README 流程由 `refresh_known_failures.sh` 处理）。
>
> **不破坏**: 现有 22 个 CLI subcommand / 18 个 doctor category / 27 个 skill / pytest+ bats 既有测试期望。所有 AC 锁定"测试通过且无新增失败"。
>
> **Out of Scope (硬性)**: 历史归档目录 `openspec/changes/archive/**/tasks.md`、`docs/superpowers/plans/*.md`、`.rddf/state/trace/`、`.rddf/wt/<name>/` 等运行产物 / worktree 副本里的 hardcode——按"respect user data"原则保留作历史审计痕迹。

## 架构依据

### 动机（用户调研）

#### A. SKILL.md ↔ _CHECKERS 漂移

| 项 | 实际值 |
|---|---|
| SKILL.md 第 51-62 行类别表行数 | **8**（state / plan-tdd / roadmap-meta / proposal-table / tasks-checkbox / migration-residue / gitignore / arch-audit） |
| `skills/rdd-doctor/scripts/doctor_main.py::_CHECKERS` 字典条目 | **18** |
| `tests/unit/test_doctor_main.py::_CATEGORY_NAMES`（已被同步） | **18** |
| 缺文档：orphan-gates / roadmap-refs / roadmap-feature / docs-consistency / proposal-section / ai-context-bootstrap / bypass-audit / improvement-frontmatter-consistency / objective-lifecycle / objective-structure | 10 |

**用户痛点**: 看 SKILL.md 选 `--category` 时根本不知道还有 `roadmap-feature` / `objective-lifecycle` 等新类别存在；直接调 `bash skills/rdd-doctor/scripts/doctor.sh --help` 也只能看到 argparse 自动生成的 18 个 choice，认知与文档不一致。

#### B. `_PROJECT_ROOT` 算浅一层 bug

```python
# skills/rdd-doctor/scripts/checks/{objective_lifecycle,objective_structure,roadmap_feature,roadmap_refs}_check.py
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
# 文件: skills/rdd-doctor/scripts/checks/<file>.py
# 链: checks/ → scripts/ → rdd-doctor/ → skills/   ← 只到 skills/，不是 repo_root
# 期望链: checks/ → scripts/ → rdd-doctor/ → skills/ → repo_root   ← 需要 5 层 .parent
```

实测：
```bash
$ python3 -c "
from pathlib import Path
p = Path('skills/rdd-doctor/scripts/checks/objective_lifecycle_check.py').resolve()
print(p.parent.parent.parent.parent)        # 4 层 → /workspace/main/rdd-workflow/skills
print(p.parent.parent.parent.parent.parent)  # 5 层 → /workspace/main/rdd-workflow ✓
"
```

**影响面**: 4 个 check 文件全部有同样的 4-层 bug → `_lib` import 全部失败 → 任何访问 `.rddf/roadmap/objectives/` 或 `.rddf/roadmap/features/` 的 doctor 调用（包括 `bash doctor.sh --help`）立即 `ModuleNotFoundError` 退出。

**根因**: 这 4 个 check 文件是后来加的（roadmap-feature 来自 `feat-roadmap-discovery-completion`，objective-* 来自 `add-objective-tracking`），作者复制粘贴了更早 `state_schema_check.py` 等的 4-层模板，但 `state_schema_check` 等早期 check 文件用的是 `Path(__file__).resolve().parent.parent.parent.parent.parent`（5 层）— 复制时少算了一层。

#### C. /workspace/project/rdd-workflow hardcode 大清查

**实证**（2026-10-07 `grep -rln "/workspace/project/rdd-workflow\|/workspace/main/rdd-workflow" .` 过滤归档）：

| 类别 | 文件数 | 必改? |
|---|---|---|
| `tests/conftest.py`（仅 docstring 里 hardcode，代码已正确） | 1 | 必改（文档误导） |
| `tests/unit/*.py` sys.path.insert(0, ...) 或 proj.PROPERTY = Path() | 14 | 必改（cheap fix） |
| `tests/integration/*.bats` `cd /workspace/...` 或 `bash /workspace/.../scripts/...` | 8 | 必改 |
| `tests/e2e/run_external_testbed.sh` 默认变量 | 1 | 必改（影响 e2e） |
| `skills/guide/SKILL.md` snippet | 1 | 必改 |
| `openspec/changes/archive/**/tasks.md` | 100+ | 不改（历史审计） |
| `docs/superpowers/plans/*.md` | 50+ | 不改（历史 plan） |
| `.rddf/state/trace/*.jsonl` | 100+ | 不改（运行产物） |
| `.rddf/wt/test-change/**` | 50+ | 不改（worktree 副本） |

**用户痛点**: 项目从 `/workspace/project/rdd-workflow` 迁到本机 `/workspace/main/rdd-workflow` 后，所有 hardcode 的 `sys.path.insert` / `cd` 全部指向不存在的目录；只有 conftest.py 救场所以 unit test 还能跑通，但 **bats 集成测试多个 127 (Command Not found) 退出**——根因之一是 hardcode 而非别的问题。

### 设计决策（已批准）

| 决策点 | 选择 |
|---|---|
| 范围 | 三类同源问题合并一次清理（统一提案便于 reviewer） |
| 优先级 | P1（影响 11+ 个 test failure + 用户文档误导） |
| SKILL.md 表更新策略 | 8 行扩展为 18 行 + 注明哪些针对 `.rddf/roadmap/*` 文档（回应用户原始问询） |
| `_PROJECT_ROOT` 修复策略 | 4-层 → 5 层；不动其他逻辑 |
| Hardcode 替换策略 | 三档：<br>(1) Python test: `Path(__file__).resolve().parents[3]` 或 conftest 已注入 → 直接删 sys.path.insert<br>(2) Bash bats: `$(git rev-parse --show-toplevel)` 或保留现有 `$REPO_ROOT` 变量<br>(3) e2e / guide SKILL: 保留 `RDD_E2E_DIR` / `RDD_WORKFLOW_REPO` env var 注入（用户可控） |
| 兼容性 | 全部向后兼容：CI baseline、env 变量、worktree 模式均不变 |
| 测试策略 | TDD: 先加 `test_doctor_main_categories_sync_with_skills_md` 锁定 SKILL.md ↔ _CHECKERS 不再 divergence（红 → 绿 → 提交）|
| Out of scope 硬性 | 历史 archive 目录 hardcode 不改 |

## 范围

**In Scope**:

**A. SKILL.md 同步** (`skills/rdd-doctor/SKILL.md` 修改 ~30 行)
- 把第 26 行 `--category state|plan-tdd|roadmap-meta|proposal-table|tasks-checkbox|arch-audit` 改为 `... |roadmap-refs|roadmap-feature|...` 完整列表
- 把第 51-62 行「5 类检查概览」表扩展为「18 类检查概览」表
- 在「类别与 .rddf/roadmap/ 文档的对应关系」段加交叉表，回答原查询意图

**B. `_PROJECT_ROOT` 修复** (4 个 check 文件各改 1 行)
- `skills/rdd-doctor/scripts/checks/objective_lifecycle_check.py:24`
- `skills/rdd-doctor/scripts/checks/objective_structure_check.py:24`
- `skills/rdd-doctor/scripts/checks/roadmap_feature_check.py:25`
- `skills/rdd-doctor/scripts/checks/roadmap_refs_check.py:17`
- 每处：`parent.parent.parent.parent` → `parent.parent.parent.parent.parent`（多 1 层）

**C. Hardcode 路径替换** (30+ 文件)
- `tests/conftest.py`：修 docstring 第 8 行（代码已正确）
- `tests/unit/*.py` (12 文件)：用 `Path(__file__).resolve().parents[3]` 或删除冗余 import
- `tests/integration/*.bats` (8 文件)：`cd /workspace/...` → `cd "$(git rev-parse --show-toplevel)"` 或使用既有 `$REPO_ROOT` / `$DOCTOR` 变量
- `tests/e2e/run_external_testbed.sh`：保留 `RDD_E2E_DIR` / `RDD_WORKFLOW_REPO` 默认值但加 fallback 到 `$(git rev-parse --show-toplevel)`
- `skills/guide/SKILL.md`：snippet 示例改用 `${BASH_SOURCE[0]}` 解析

**D. `tests/integration/test_rdd_doctor.bats` 同步**
- 第 68 行 `doctor: --help mentions all 6 categories` 测试名 + 断言更新为 18 个类别
- 同步修 `test_rdd_doctor.bats` 中可能新失败的 helper assertions

**E. 测试 / 文档** (~80 LOC)
- `tests/integration/test_rdd_doctor_skills_md_sync.bats`（新增 ~30 行）：锁定 SKILL.md 第 51-62 行表格行数 == 18 + 表格内 category 名 ⊆ `_CHECKERS.keys()`
- `tests/unit/test_no_hardcoded_workspace_paths.py`（新增 ~30 行）：扫描活跃代码 `*.py` / `*.sh` / `*.bats`，断言无 `/workspace/project/rdd-workflow` 残留（白名单：`openspec/changes/archive/` / `docs/superpowers/plans/` / `.rddf/state/` / `.rddf/wt/`)
- 跑全套 bats + pytest 确认无新增失败

**Out Scope**:
- 改 `_lib/objective.py` 模块本身（已有，bug 不在那）
- 改 `KNOWN_FAILURES.txt`（按 README 由 `refresh_known_failures.sh` 处理，本提案自然清零"2 doctor_main"条目，但 refresh 由后续 commit 单独跑）
- 重写 doctor.py / doctor.sh / doctor_main.py（已有架构 OK）
- 历史归档目录 `openspec/changes/archive/**` 里的 hardcode 改全（保留作"historical snapshot"）
- `docs/superpowers/plans/*.md` 历史 plan 文档改全
- `.rddf/state/trace/` 运行 trace 改全
- `.rddf/wt/<name>/` worktree 副本改全（git worktree 内容，PR 不应碰）
- 添加新的 doctor category
- 改 `rdd-quick` / `rdd-builder` 等 skill 内部逻辑
- 升级 `openspec` CLI 版本

## 验收标准

| AC | 描述 |
|----|------|
| AC-1 | `bash skills/rdd-doctor/scripts/doctor.sh --help` exit 0，无 `ModuleNotFoundError` |
| AC-2 | `bash skills/rdd-doctor/scripts/doctor.sh --version` 输出 `rdd-doctor 0.1.0` |
| AC-3 | `bash skills/rdd-doctor/scripts/doctor.sh --category objective-lifecycle` exit ≤ 1（无 CRITICAL）|
| AC-4 | `bash skills/rdd-doctor/scripts/doctor.sh --category roadmap-feature` exit 0（项目 master 同步）|
| AC-5 | `bash skills/rdd-doctor/scripts/doctor.sh --category roadmap-refs` exit ≤ 1 |
| AC-6 | `SKILL.md` 第 51-62 行表格行数 == 18（grep + count 断言）|
| AC-7 | `SKILL.md` 表格内 category 名集合 ⊆ `doctor_main._CHECKERS.keys()` |
| AC-8 | `bats tests/integration/test_rdd_doctor_skills_md_sync.bats` 全绿（新测试）|
| AC-9 | `bats tests/integration/test_rdd_doctor.bats` 全绿或仅 KNOWN_FAILURES 标注项失败 |
| AC-10 | `bats tests/integration/test_rdd_doctor_readonly_roadmap.bats` 全绿（修 `/workspace/project/` 路径后）|
| AC-11 | `pytest tests/unit/test_doctor_main.py` 全绿（18 已锁）|
| AC-12 | `pytest tests/unit/test_no_hardcoded_workspace_paths.py` 全绿（新测试，白名单外 0 处残留）|
| AC-13 | `./test.sh --quick` 通过，无新增失败（对比 KNOWN_FAILURES baseline）|
| AC-14 | `git diff --stat` 显示本次改动文件数 ≤ 50、净增 LOC ≤ 500（保守阈值，超出拆 commit）|

## 关键场景

### 场景 1: 用户用 `bash doctor.sh --category roadmap-feature` 排查 `.rddf/roadmap/features/`

```bash
# 旧（崩溃）
$ bash skills/rdd-doctor/scripts/doctor.sh --category roadmap-feature
ModuleNotFoundError: No module named '_lib.objective'

# 新（通过）
$ bash skills/rdd-doctor/scripts/doctor.sh --category roadmap-feature
✅ All checks passed
```

### 场景 2: 项目迁移后 CI 在新机器跑 bats 集成测试

```bash
# 旧（127 file-not-found）
$ bats tests/integration/test_rdd_doctor_readonly_roadmap.bats
not ok 1 rdd-doctor --category roadmap-refs: reports R1 violation, exit 2 (CRITICAL), no file modifications
BW01: ... exited with code 127, indicating 'Command not found'.

# 新（exit 0/2 + 真检查）
$ bats tests/integration/test_rdd_doctor_readonly_roadmap.bats
ok 1 rdd-doctor --category roadmap-refs: reports R1 violation, exit 2 (CRITICAL), no file modifications
```

### 场景 3: 用户读 SKILL.md 选 `--category`

```bash
# 旧（用户只看文档，不知道 objective-lifecycle 存在）
$ grep -c "^| \`" skills/rdd-doctor/SKILL.md   # 输出 8

# 新（文档=实现=18 一致）
$ grep -c "^| \`" skills/rdd-doctor/SKILL.md   # 输出 18
$ python3 -c "from skills._lib.rdd_doctor.scripts.doctor_main import _CHECKERS; print(len(_CHECKERS))"  # 18
```

## 技术约束

| 约束 | 说明 |
|---|---|
| 路径解析 | `git rev-parse --show-toplevel` 是 bats 默认；Python 用 `Path(__file__).resolve().parents[N]` 或 `resolve_project_root()`（已有 `skills._lib._python_resolve_project_root.resolve_project_root()`）|
| 不引入新依赖 | 不安装新 Python / bash 包；只用 stdlib + 已安装 |
| 现有测试 | 全部 pytest + bats 测试期望保持绿色；`KNOWN_FAILURES.txt` 中标注项允许失败但需 refresh |
| 文档一致性 | SKILL.md 类别表 == `doctor_main._CHECKERS.keys()` == `--help` argparse 自动输出 |
| Module-parse 行为 | 4 个 check 文件 `_lib.objective` 等 import 必须 work |
| Worktree 兼容 | 修复后 bats + .py 在 main repo / linked worktree / 其他位置都跑得通（不依赖绝对路径）|
| 性能 | 单 check file `_PROJECT_ROOT` 计算 < 1ms（Path 解析），可忽略 |
| 不破坏 env 注入 | `RDDF_PROJECT_ROOT` / `RDD_E2E_DIR` / `RDD_WORKFLOW_REPO` env 仍按既有优先级 |
| 历史保留 | `openspec/changes/archive/**` hardcode 全部保留（"respect user data"）|
| 测试覆盖 | 至少 happy path + SKILL.md sync invariant + hardcode 残留扫描 + bats/python 全绿 |

## Lifecycle

### 1. Proposal creation

本文件 `.rddf/improvements/fix-rdd-doctor-hardcoded-paths-and-skills-md-drift.md`。
注册到 `improvement-suggestions.md` 表格（`rdd-roadmap` 自动）。

### 2. Design review (`rdd-planner`)

按 v4 流程审查。

### 3. Plan (`rdd-builder` P1)

生成 `.rddf/plans/<name>.md`，包含 TDD 5 步结构（write test → verify fail → implement → verify pass → commit）。

### 4. Ship (`rdd-builder` P2)

执行 change。完成所有 task 后跑 `./test.sh --full --regression`（MANDATORY gate per `add-full-regression-gate`）。

### 5. Archive

archive → `openspec/changes/archive/2026-10-XX-fix-rdd-doctor-hardcoded-paths-and-skills-md-drift/`。

## 风险与回滚

| 风险 | 概率 | 影响 | 缓解 | 回滚 |
|------|------|------|------|------|
| Path.parents 算错层级 | 低 | conftest 不救场时 import 失败 | 优先用 `resolve_project_root()`（已有 helper）；加 test_no_hardcoded_workspace_paths 锁住；bats 测试覆盖 | `git revert` 单 commit |
| SKILL.md 表格行数 == 18 强约束 | 自验 | reviewer 一眼看错 | 表格行数 + 表格内容 name set 双断言；测试名显式 | 单 commit revert |
| `**/checks/_PROJECT_ROOT` 修复方向漂移 | 极低 | 仍 ModuleNotFoundError | 跑 `python3 -c "from skills._lib._python_resolve_project_root import resolve_project_root"` 验证 | 单 commit revert |
| `e2e/run_external_testbed.sh` 默认值变更 | 低 | CI 默认 repo 路径变 | 保留 `RDD_WORKFLOW_REPO` env var 注入能力，加 git fallback | 单 commit revert |
| `_CHECKERS` 字典新增条目后 SKILL.md 表未同步 | 中 | 回归 | 新增 `test_rdd_doctor_skills_md_sync` 锁住 | 修 SKILL.md 表 + commit |
| 历史 archive 目录 hardcode 未清理 | 接受 | accept by design | "respect user data" 白名单 | N/A |
| 大批文件改动 review 难 | 中 | PR 难读 | 拆 4 commit: (a) SKILL.md (b) `_PROJECT_ROOT` (c) bats hardcode (d) py hardcode | 拆 commit 单独 revert |

**回滚方案**（4 commit 各自 revert 即可）：

```bash
git revert <commit-sha-skills-md>
git revert <commit-sha-project-root-bug>
git revert <commit-sha-bats-hardcode>
git revert <commit-sha-py-hardcode>
```

## 实施计划 (估算)

| Task | 内容 | LOC |
|------|------|-----|
| T1 | `_PROJECT_ROOT` 4-层 → 5-层（4 check files × 1 行） | 4 |
| T2 | SKILL.md 类别表扩展 8 → 18 + 加 .rddf/roadmap 交叉表 | +30 |
| T3 | `tests/integration/test_rdd_doctor.bats` "all 6 categories" → 18 categories 断言 | +20 |
| T4 | 新增 `tests/integration/test_rdd_doctor_skills_md_sync.bats` | +30 |
| T5 | 新增 `tests/unit/test_no_hardcoded_workspace_paths.py` | +30 |
| T6 | `tests/conftest.py` docstring 修 | 1 |
| T7 | `tests/unit/*.py` sys.path.insert 替换（10 文件）| -10 |
| T8 | `tests/unit/test_*_project_root*.py` hardcode 替换（4 文件，PROJECT_ROOT 用 resolve_project_root）| -5 |
| T9 | `tests/integration/*.bats` `cd /workspace/...` 替换（6 文件）| +5 |
| T10 | `tests/integration/test_*_roadmap.bats` `bash /workspace/.../scripts/...` 替换（3 文件）| +5 |
| T11 | `tests/e2e/run_external_testbed.sh` 默认值兜底 | +3 |
| T12 | `skills/guide/SKILL.md` snippet 改用 `${BASH_SOURCE[0]}` | +3 |
| T13 | `./test.sh --quick` 跑全，验证无新增失败 | — |
| **Total** | 13 tasks | **~110 LOC 净增** |

**预估工期**: 1-2 小时（含 TDD 5 步 + bats 集成 + pytest + 文档同步）。

## 相关 ADR

- ADR-0033 submodule-aware-project-root — `resolve_project_root()` 已 worktree + submodule-safe
- ADR-0046 rdd-arch v2.1.0 + arch-audit category — 与本次 `arch-audit` 类别同步相关
- ADR-0052 Layer 0 progressive context — SKILL.md 是 Layer 0 元数据入口，文档一致性是 P1
- ADR-0054 objective 工件 — `objective-lifecycle` / `objective-structure` category 落点
- 与 `add-full-regression-gate`（P0, 2026-07-28）相关 — ship 前必跑 `./test.sh --full --regression`