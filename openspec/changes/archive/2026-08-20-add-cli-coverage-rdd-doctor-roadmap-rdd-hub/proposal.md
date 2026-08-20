# add-cli-coverage-rdd-doctor-roadmap-rdd-hub

## Why

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

## What Changes

**In Scope**:

- 暴露 `rddf doctor [--json] [--category <name>] [--quiet] [--version]`
- 转发到 `bash skills/rdd-doctor/scripts/doctor.sh "$@"`
- 透传 exit code
- `--help` 文本参考 `doctor.sh --help` 同步
- 暴露 `rddf roadmap <sub> [--args]`
- 支持 subcommand: `init` / `status` / `edit` / `validate` (skill 原生) + `migrate` / `validate-fragments` (本次新增)
- 子命令分发表，映射到对应 bash scripts 或 `skill_use()`
- `--help` 文本聚合所有 subcommand
- 暴露 `rddf rdd-hub-bootstrap [init|status|...] [--dry-run|--yes|--org|--repo]`
- 转发到 `bash skills/rdd-hub-bootstrap/scripts/*.sh`
- `--help` 显示所有可用的 bootstrap subcommand
- `from _lib.cli import doctor_cmd` 等 3 个 import
- 路由表添加 3 行：`"doctor": cmd_doctor, "roadmap": cmd_roadmap, "rdd-hub-bootstrap": cmd_rdd_hub_bootstrap`
- `tests/integration/test_cli_coverage.bats` (5 tests)
- 验证 `rddf doctor --help` / `rddf roadmap --help` / `rddf rdd-hub-bootstrap --help` exit 0 + 含正确 subcommand 列表
- 验证 `rddf doctor --version` 输出 `rdd-doctor 0.1.0`
- 验证 exit code 透传（`--category bogus` → exit 2）

### 关键场景

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

**Out of Scope**:

- 修改 `rdd-doctor` / `roadmap` / `rdd-hub-bootstrap` skill 内部 Python/Bash 逻辑
- 重新设计 `_lib/cli/` dispatcher（保持现有 `cmd_<name>(args)` 契约）
- 把其他 15 个 skill（`execute` / `propose` / `guide-*` / `add-improve` 等）也暴露 CLI — 后续 proposal
- 异步 / sub-process 编排（`orchestrate` 已有，不重复）
- Python-only 重写（本次仅薄包装）

## Capabilities

- (no items specified)

## Impact

- (no items specified)

## Acceptance

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

