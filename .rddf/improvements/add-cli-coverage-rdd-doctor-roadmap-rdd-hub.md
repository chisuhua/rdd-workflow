# add-cli-coverage-rdd-doctor-roadmap-rdd-hub

**优先级**: P1 | **来源**: 用户体验反馈（`rddf <skill>` 命名空间不完整，3 个核心 skill 缺 CLI 入口）
**阶段**: v2.2 | **分类**: core-impl
**类型**: feature
**特性**: __ungrouped__

> **范围定位**：本提案为 `rdd-doctor` / `roadmap` / `rdd-hub-bootstrap` 3 个 skill 各补一个薄 CLI wrapper，让 `rddf <cmd>` 命名空间与 `skills/` 目录保持一致。**不修改 skill 内部逻辑**，仅在 `_lib/cli/` 注册新 subcommand。
>
> **不重复** `add-cli-coverage-guide-orchestrator` 等其他 skill 的 CLI 暴露（按用户选择仅覆盖 3 个目标）。
>
> **不破坏** 现有 `rddf <cmd>` 行为（保留所有现有 subcommand）。

## 架构依据

### 动机（用户调研）

| 当前状况 | 用户痛点 |
|---------|---------|
| 28 个 skill 目录存在 | 但仅 10 个有 CLI 暴露 |
| `rdd-doctor` / `roadmap` / `rdd-hub-bootstrap` 无 CLI | 必须 `bash skills/<x>/scripts/<script>.sh [--args]` 才能用 |
| `sync-hub` / `watch-hub` 已有 CLI（hub 相关） | 但 `rdd-hub-bootstrap`（仓库初始化）反而没有 |

**实证证据**（2026-08-20 调研）：

```
skills/rdd-doctor/scripts/doctor.sh        ← bash 直调  ← 缺 rddf doctor
skills/roadmap/scripts/roadmap_migrate.sh  ← bash 直调  ← 缺 rddf roadmap
skills/roadmap/scripts/roadmap_validate_fragments.sh  ← bash 直调  ← 缺 rddf roadmap
skills/rdd-hub-bootstrap/scripts/*.sh      ← bash 直调  ← 缺 rddf rdd-hub-bootstrap
```

### 设计决策（已批准）

| 决策点 | 选择 |
|--------|------|
| 范围 | 仅 3 个目标（用户选定） |
| 优先级 | P1（中等紧急度，影响日常 onboarding） |
| 实现方案 | 统一薄包装（用户选定） |
| 入口命名 | `rddf doctor` / `rddf roadmap` / `rddf rdd-hub-bootstrap` |
| 实现深度 | 仅 thin wrapper：转发到原 bash scripts + 显式 `skill_use()` 提示 |
| 兼容性 | 保留所有现有 subcommand；新 cmd 全部 additive |
| 退出码 | 透传底层脚本（与 `rdd-doctor` / `openspec` 已对齐 0/1/2/3） |

### 为什么不直接重写为 Python？

- `rdd-doctor` 18-line wrapper + 复杂 Python dispatcher (`doctor_main.py`)，重写成本高
- `roadmap` skill 9 步 migrate 脚本含 awk + bash 特性，重写需小心 dual-format 处理
- `rdd-hub-bootstrap` 含 gh CLI 调用 + idempotency，重写测试面广
- 薄包装让 change 风险最小化（5-30 行/cmd），便于 review

## 范围

**In Scope**:

**A. `_lib/cli/doctor_cmd.py`** (新建，~25 行)
- 暴露 `rddf doctor [--json] [--category <name>] [--quiet] [--version]`
- 转发到 `bash skills/rdd-doctor/scripts/doctor.sh "$@"`
- 透传 exit code
- `--help` 文本参考 `doctor.sh --help` 同步

**B. `_lib/cli/roadmap_cmd.py`** (新建，~30 行)
- 暴露 `rddf roadmap <sub> [--args]`
- 支持 subcommand: `init` / `status` / `edit` / `validate` (skill 原生) + `migrate` / `validate-fragments` (本次新增)
- 子命令分发表，映射到对应 bash scripts 或 `skill_use()`
- `--help` 文本聚合所有 subcommand

**C. `_lib/cli/rdd_hub_bootstrap_cmd.py`** (新建，~25 行)
- 暴露 `rddf rdd-hub-bootstrap [init|status|...] [--dry-run|--yes|--org|--repo]`
- 转发到 `bash skills/rdd-hub-bootstrap/scripts/*.sh`
- `--help` 显示所有可用的 bootstrap subcommand

**D. `_lib/cli/__init__.py` 注册** (3 行修改)
- `from _lib.cli import doctor_cmd` 等 3 个 import
- 路由表添加 3 行：`"doctor": cmd_doctor, "roadmap": cmd_roadmap, "rdd-hub-bootstrap": cmd_rdd_hub_bootstrap`

**E. 测试** (新增 ~80 行 bats)
- `tests/integration/test_cli_coverage.bats` (5 tests)
- 验证 `rddf doctor --help` / `rddf roadmap --help` / `rddf rdd-hub-bootstrap --help` exit 0 + 含正确 subcommand 列表
- 验证 `rddf doctor --version` 输出 `rdd-doctor 0.1.0`
- 验证 exit code 透传（`--category bogus` → exit 2）

**Out Scope**:

- 修改 `rdd-doctor` / `roadmap` / `rdd-hub-bootstrap` skill 内部 Python/Bash 逻辑
- 重新设计 `_lib/cli/` dispatcher（保持现有 `cmd_<name>(args)` 契约）
- 把其他 15 个 skill（`execute` / `propose` / `guide-*` / `add-improve` 等）也暴露 CLI — 后续 proposal
- 异步 / sub-process 编排（`orchestrate` 已有，不重复）
- Python-only 重写（本次仅薄包装）

## 验收标准

| AC | 描述 |
|----|------|
| AC-1 | `rddf doctor --help` exit 0，stdout 含 8 个 `--category` 选项 |
| AC-2 | `rddf doctor --version` 输出 `rdd-doctor 0.1.0` |
| AC-3 | `rddf doctor --category roadmap-refs` exit 0（透传 doctor.sh 退出码） |
| AC-4 | `rddf roadmap --help` exit 0，stdout 含 `migrate` / `validate-fragments` subcommand 列表 |
| AC-5 | `rddf roadmap migrate --dry-run` exit 0（透传 roadmap_migrate.sh 退出码） |
| AC-6 | `rddf rdd-hub-bootstrap --help` exit 0，stdout 含 `init` 等 bootstrap subcommand |
| AC-7 | `rddf --help` 新增 `doctor` / `roadmap` / `rdd-hub-bootstrap` 三行（其他 19 行不变） |
| AC-8 | `tests/integration/test_cli_coverage.bats` 7-8 个测试全绿 |
| AC-9 | `./test.sh --quick` 全绿，零回归（所有现有测试不变） |
| AC-10 | SKILL.md frontmatter 不动（不修改 skill 内部） |

## 关键场景

### 场景 1: 用户日常使用 rdd-doctor

```bash
# 旧 (bash 直调)
bash skills/rdd-doctor/scripts/doctor.sh --category roadmap-refs

# 新 (CLI 一致)
rddf doctor --category roadmap-refs
```

### 场景 2: 用户初始化 rdd-hub

```bash
# 旧
bash skills/rdd-hub-bootstrap/scripts/bootstrap.sh init --org foo --repo bar

# 新
rddf rdd-hub-bootstrap init --org foo --repo bar
```

### 场景 3: 用户升级 roadmap 到 v2 hierarchical

```bash
# 旧
bash skills/roadmap/scripts/roadmap_migrate.sh --dry-run

# 新
rddf roadmap migrate --dry-run
```

### 场景 4: CI 自动化（scripting 友好）

```bash
# 旧: 必须硬编码 skills/<x>/scripts/<script>.sh 路径
# 新: 统一 rddf <cmd>, 路径无关
if ! rddf doctor --quiet --category state; then
  echo "state drift detected, run guide-plan to migrate"
fi
```

## 技术约束

| 约束 | 说明 |
|------|------|
| 现有 dispatcher 契约 | `cmd_<name>(args: list[str]) -> int` 必须保持 |
| 退出码透传 | 薄包装必须 `exec` 或 `return $?` 透传 exit code |
| `--help` 一致性 | 由各 skill 自有脚本生成（不硬编码，避免漂移） |
| Skill 内部不动 | frontmatter / `scripts/*` / Python 实现 全部冻结 |
| Performance | 薄包装加 1 个 bash 子进程调用，可接受（< 100ms 启动开销） |
| 测试覆盖 | 至少 happy path + exit code 透传 + --help 完整性 |
| 不破坏现有 | 现有 22 个 CLI subcommand 行为不变（回归测试） |

## Lifecycle

### 1. Proposal creation

提案创建在 `.rddf/improvements/add-cli-coverage-rdd-doctor-roadmap-rdd-hub.md`（本文件）。
注册到 `proposal-suggestions.md` 表格。

### 2. Design review (`guide-design`)

按 `guide-design` Phase 3 流程审查。批准后移至 `proposal-approved.md` 并创建 `openspec/changes/add-cli-coverage-rdd-doctor-roadmap-rdd-hub/`。

### 3. Plan (`guide-plan`)

生成 `.rddf/plans/add-cli-coverage-rdd-doctor-roadmap-rdd-hub.md`，包含 TDD 5 步结构（write test → verify fail → implement → verify pass → commit）。

### 4. Ship (`guide-ship`)

执行 change。完成所有 task 后跑 `./test.sh --full --regression`（MANDATORY gate）。

### 5. Archive

archive change → `openspec/changes/archive/2026-08-XX-add-cli-coverage-.../`，spec 同步到 `openspec/specs/cli-coverage/`，branch 删除。

## 风险与回滚

| 风险 | 概率 | 影响 | 缓解 | 回滚 |
|------|------|------|------|------|
| 路由表 import 错误 | 低 | 现有 CLI 启动崩溃 | 复用 `_lib/cli/__init__.py` 现有 `cmd_*` import pattern；加 unit test 验证所有现有 22 个 subcommand 不变 | `git revert` 单 commit |
| exit code 透传漏 | 中 | CI 误判 pass | `cmd_doctor()` 必须 `return subprocess.run(...).returncode`；加 bats 验证 | 同上 |
| `--help` 文本漂移 | 低 | 用户认知不一致 | thin wrapper 不硬编码 help，由底层脚本生成；bats 验证文本包含子命令名 | 同上 |
| Skill 内部被无意修改 | 极低 | skill 行为变化 | 严格 scope：`scripts/` / `__init__.py` / Python 实现全部不动；PR review 强制 check | `git checkout master -- skills/<x>/` |
| bash PATH 找不到 skill scripts | 中 | 转发失败 | 用 `${BASH_SOURCE[0]}` 解析 repo root，不依赖 `PWD` | 显式报错提示 install.sh --global |
| Performance 开销 | 极低 | < 100ms 启动 | 文档化"subprocess overhead" 注释；提供 `PYTHONPATH=... python3 -m _lib.cli doctor ...` 作为 fast path | 无需回滚 |

**回滚方案**（单 commit revert）：

```bash
git revert <commit-sha>  # 移除 3 个 _cmd.py + 3 行路由表
```

薄包装无副作用，回滚成本 < 5 分钟。

## 实施计划 (估算)

| Task | 内容 | LOC |
|------|------|-----|
| T1 | `_lib/cli/doctor_cmd.py` (thin wrapper) | ~25 |
| T2 | `_lib/cli/roadmap_cmd.py` (subcommand dispatch) | ~30 |
| T3 | `_lib/cli/rdd_hub_bootstrap_cmd.py` (thin wrapper) | ~25 |
| T4 | `_lib/cli/__init__.py` 注册 3 行 | +6 |
| T5 | `tests/integration/test_cli_coverage.bats` (7 tests) | ~80 |
| T6 | SKILL.md cross-link (可选, 指向新 CLI 入口) | ~10 |
| **Total** | 6 tasks | **~175 LOC** |

**预估工期**：1-2 小时（含 TDD 5 步 + bats 集成测试 + 文档）。

## 相关 ADR

- 无（本次不引入新架构决策）
- 与 ADR-0030（Hub-and-Spoke）相关：`sync-hub` / `watch-hub` 已有 CLI，本次补 `rdd-hub-bootstrap` 形成完整 hub 工具链
- 与 ADR-0032（Hub Federation Deepening）相关：`rdd-hub-bootstrap` 暴露便于 hub deepening 场景