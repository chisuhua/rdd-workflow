# fix-cli-all-subcommands-dynamic-sync

## Context

**症状 (2026-08-31 ship 阶段, 2 个 P1 change 触发)**:

- `_lib/cli/` 已含 `hub_retry_cmd.py`（alias `hub`）和 `scheduler_cmd.py` 子命令
- 但 `tests/unit/test_cli_all_subcommands.py` L60 的 `ALL_SUBCOMMANDS` tuple 仍是 2026-08-26 的版本（不含两者）
- pytest 报 2 个失败：
  ```
  FAILED test_cli_all_subcommands.py::test_list_commands_returns_canonical_subcommand_set
  FAILED test_cli_all_subcommands.py::test_routes_keys_match_canonical_subcommand_set
  ```
  错误：`list_commands()` returns ['ac-verify', ..., 'hub', ..., 'scheduler', ...] diverges from ALL_SUBCOMMANDS=(...)
- 修复：手工加 `hub`（L60 插入 `"hub",`）+ `scheduler`（`"scheduler",`）到 tuple，170 pytest PASS

**根因分析**:

`test_cli_all_subcommands.py` 的设计目标是通过 ALL_SUBCOMMANDS 校验「CLI 注册的命令集合与预期一致」。但：

1. `ALL_SUBCOMMANDS` 是**手写 tuple**，与 `_lib/cli/` 目录（实际命令）各自独立演化
2. 添加新子命令时（如 `rddf scheduler` alias、`rddf hub`），开发者容易忘记同步测试 tuple
3. 无「自动发现」机制：测试不检查目录中新增的 `*_cmd.py` 是否已被列入 ALL_SUBCOMMANDS

**影响范围**:

- 每次新增 CLI 子命令触发 2 个 pytest fail（回归门 fail）
- 触发时需人工排查（本会话约 10 分钟：识别 2 个缺失命令 + 定位 tuple + 插入）
- 现有 `_lib/cli/` 有 30 个 `_cmd.py`，ALL_SUBCOMMANDS 仅 28 个（还有 `iteration_strict`/`regression_diff` 等其他 drift 待清理）

## Goals

**In Scope**:

- 在 `tests/unit/test_cli_all_subcommands.py` 中，将 `ALL_SUBCOMMANDS` 从手写 tuple 改为运行时发现：
- 若 CLI 有官方发现机制（`_lib/cli/__init__.py` 的 `list_commands()`），直接复用
- 保留测试的「canonical set」语义：`list_commands() == list(ALL_SUBCOMMANDS)` 是同一来源，永远 self-consistent
- 但这样会**削弱**测试价值（不再检测"意外命令"）→ 需引入**白名单校验**兜底
- **白名单方案**（无良配置漂移的平衡）：
- `ALL_SUBCOMMANDS` 仍动态生成自 `_lib/cli/`
- 另加 1 个 `test_all_subcommands_in_whitelist`（白名单 = 已知合法命令集）
- 新增 `_cmd.py` 且不在白名单 → fail（提示开发者显式批准新命令）
- 在 `scripts/pre-commit-hooks/check_cli_subcommands.sh` 加逻辑
- `git diff --name-only HEAD` 检测新增 `_lib/cli/*_cmd.py`
- 同步 检查 `test_cli_all_subcommands.py` 是否已更新
- 未更新则退出 1，提示 `新增 CLI 命令请同步 ALL_SUBCOMMANDS tuple`
- 检查 `_lib/cli/` 全部 30 个 `_cmd.py` vs ALL_SUBCOMMANDS，补齐缺失命令（含 `iteration_strict`？`regression_diff`？——需要确认别名关系）
- 确认 `hub_retry_cmd.py` → 命令名 `hub`（不是 `hub_retry`），`scheduler_cmd.py` → `scheduler`
- 确认 `iteration_strict_cmd.py` → `iteration` / `iteration_strict` 二选一
- 最终 ALL_SUBCOMMANDS 与实际 `list_commands()` 完全一致
- **不修改** CLI 本身（`_lib/cli/*_cmd.py` 注册逻辑）
- **不修改** `list_commands()` / `_ROUTES` 的行为
- **不重写** `_lib/cli/` 的模块结构
- **不实现** 完全自动的白名单生成（需人工评审新增命令是否合法）

### 关键场景

### 场景 1: 新增 CLI 子命令（正常路径）

- **GIVEN** 开发者新增 `_lib/cli/foo_cmd.py` 注册 `foo` 命令
- **WHEN** 跑 pytest unit
- **THEN**
  - 动态 ALL_SUBCOMMANDS 自动含 `foo`
  - `test_list_commands_returns_canonical_subcommand_set` PASS（self-consistent）
  - 若 `foo` 不在白名单，`test_all_subcommands_in_whitelist` FAIL（提示显式确认）

### 场景 2: 白名单校验（新增命令需要显式批准）

- **GIVEN** `_lib/cli/foo_cmd.py` 新增，`foo` 不在白名单列表
- **WHEN** 跑 pytest
- **THEN** `test_all_subcommands_in_whitelist` FAIL，提示 `新增 CLI 子命令 foo 需加入白名单`
- **AND** 开发者加 `foo` 到白名单 → PASS

### 场景 3: 现有 drift 清理

- **GIVEN** `_lib/cli/` 有 30 个 `_cmd.py`，ALL_SUBCOMMANDS 只有 28 个
- **WHEN** 本提案 ship 后首次跑 pytest
- **THEN** 动态发现让两者一致，无 fail（白名单缺失命令需人工加白名单）

### 场景 4: `hub_retry` alias vs `hub`

- **GIVEN** `hub_retry_cmd.py` 注册命令名是 `hub`（alias）
- **WHEN** 动态 ALL_SUBCOMMANDS 发现
- **THEN** 命令集合含 `hub`（不是 `hub_retry`），与 `list_commands()` 一致

**Out of Scope**:

- (no items specified)

## Decisions

- **MUST NOT**: 破坏 `list_commands()` / `_ROUTES` 的现有行为
- **MUST NOT**: 引入新依赖（Python stdlib + 现有 `_lib/cli` 即可）
- **MUST NOT**: 删除测试文件（`test_cli_all_subcommands.py` 保留，只是改生成逻辑）
- **MUST**: 动态发现优先复用现有 CLI discovery API（`_ROUTES` / `list_commands()`）
- **SHOULD**: 白名单机制不用第三方库（纯 set / tuple 即可）
- **SHOULD**: 与 `tests/unit/test_skill_meta.py`（类似 canonical set 校验）风格一致

## Risks

- (no items specified)
