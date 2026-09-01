# fix-cli-all-subcommands-dynamic-sync

**优先级**: P1 | **来源**: 2026-08-31 ship 阶段回归门发现 — `test_cli_all_subcommands.py::ALL_SUBCOMMANDS` tuple 未包含新加的子命令 `hub` / `scheduler`
**阶段**: v2.2 | **分类**: infra-setup / 测试基建
**类型**: bug fix

> **症状**：添加新 CLI 子命令后，`tests/unit/test_cli_all_subcommands.py` 的 `ALL_SUBCOMMANDS` tuple 未同步更新，导致 2 个 pytest 失败（`test_list_commands_returns_canonical_subcommand_set` / `test_routes_keys_match_canonical_subcommand_set`），回归门 fail。
> **根因**：`ALL_SUBCOMMANDS` 是手写 tuple（L60），与 `_lib/cli/` 目录实际子命令数各自独立演化，无自动同步机制。
> **临时绕过**：本次会话手工往 tuple 加 `hub` + `scheduler` 2 行。

## 架构依据

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

## 范围

### In Scope

**A. 动态生成 ALL_SUBCOMMANDS（推荐方案）**:

- 在 `tests/unit/test_cli_all_subcommands.py` 中，将 `ALL_SUBCOMMANDS` 从手写 tuple 改为运行时发现：
  ```python
  from _lib.cli import discover_commands  # 或等价 API
  ALL_SUBCOMMANDS = tuple(sorted(discover_commands()))
  ```
- 若 CLI 有官方发现机制（`_lib/cli/__init__.py` 的 `list_commands()`），直接复用
- 保留测试的「canonical set」语义：`list_commands() == list(ALL_SUBCOMMANDS)` 是同一来源，永远 self-consistent
- 但这样会**削弱**测试价值（不再检测"意外命令"）→ 需引入**白名单校验**兜底
- **白名单方案**（无良配置漂移的平衡）：
  - `ALL_SUBCOMMANDS` 仍动态生成自 `_lib/cli/`
  - 另加 1 个 `test_all_subcommands_in_whitelist`（白名单 = 已知合法命令集）
  - 新增 `_cmd.py` 且不在白名单 → fail（提示开发者显式批准新命令）

**B. PRE-COMMIT HOOK（备选方案）**:

- 在 `scripts/pre-commit-hooks/check_cli_subcommands.sh` 加逻辑
- `git diff --name-only HEAD` 检测新增 `_lib/cli/*_cmd.py`
- 同步 检查 `test_cli_all_subcommands.py` 是否已更新
- 未更新则退出 1，提示 `新增 CLI 命令请同步 ALL_SUBCOMMANDS tuple`

**C. 清理现存 drift**:

- 检查 `_lib/cli/` 全部 30 个 `_cmd.py` vs ALL_SUBCOMMANDS，补齐缺失命令（含 `iteration_strict`？`regression_diff`？——需要确认别名关系）
- 确认 `hub_retry_cmd.py` → 命令名 `hub`（不是 `hub_retry`），`scheduler_cmd.py` → `scheduler`
- 确认 `iteration_strict_cmd.py` → `iteration` / `iteration_strict` 二选一
- 最终 ALL_SUBCOMMANDS 与实际 `list_commands()` 完全一致

### Out Scope

- **不修改** CLI 本身（`_lib/cli/*_cmd.py` 注册逻辑）
- **不修改** `list_commands()` / `_ROUTES` 的行为
- **不重写** `_lib/cli/` 的模块结构
- **不实现** 完全自动的白名单生成（需人工评审新增命令是否合法）

## 关键场景

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

## 技术约束

- **MUST NOT**: 破坏 `list_commands()` / `_ROUTES` 的现有行为
- **MUST NOT**: 引入新依赖（Python stdlib + 现有 `_lib/cli` 即可）
- **MUST NOT**: 删除测试文件（`test_cli_all_subcommands.py` 保留，只是改生成逻辑）
- **MUST**: 动态发现优先复用现有 CLI discovery API（`_ROUTES` / `list_commands()`）
- **SHOULD**: 白名单机制不用第三方库（纯 set / tuple 即可）
- **SHOULD**: 与 `tests/unit/test_skill_meta.py`（类似 canonical set 校验）风格一致

## 验收标准

### 单元与集成测试

- [ ] `tests/unit/test_cli_all_subcommands.py` 重构为动态 ALL_SUBCOMMANDS
- [ ] 5 个单元测试 PASS（含白名单 / alias / 新增命令检测）
- [ ] `tests/integration/test_cli_all_subcommands.bats`（如存在）适配新逻辑

### 端到端验证

- [ ] 复现 2026-08-31 场景：临时删掉 ALL_SUBCOMMANDS 中 `hub` → pytest 不再 fail（动态发现自动含）
- [ ] 模拟新增 `_cmd.py` → 白名单测试正确 fail（提示显式批准）
- [ ] 与 `fix-report-regression-sed-double-hash-strip` (P0-2) 无交互：report_regression 逻辑不变

### 文档化

- [ ] `docs/change-quality-guide.md` 加"CLI 子命令白名单"段（新增命令流程）
- [ ] `tests/unit/test_cli_all_subcommands.py` 头注释更新说明动态发现机制

### 兼容性验证

- [ ] 复测 30 个现有 `_cmd.py` 全部正确发现（无遗漏无多余）
- [ ] `rddf --help` 命令列表与 ALL_SUBCOMMANDS 一致
- [ ] 与 `hub` / `scheduler` 子命令（2026-08-31 手工加过 tuple）不冲突：动态发现后无需手工维护

### 副作用监测

- [ ] ship 后 30 天观察期：`test_cli_all_subcommands` 无新增失败（历史：添加新命令后必 fail 1 次）
- [ ] 不引入新的 KNOWN_FAILURES 条目

## Why

- **现状痛点**：手写 ALL_SUBCOMMANDS 与 CLI 实现各自演化，每次新增子命令触发 pytest fail，回归门 fail。成本虽低（10 分钟人工），但 RDD-Workflow 自身 dogfood 频繁新增命令（本次 hub/scheduler），累积摩擦。
- **修复价值**：动态发现消除"忘同步 tuple" 的系统性 bug，把人力从「调 tuple」转向「评审新命令是否合法」。白名单保留安全网。
- **Why now**: 2026-08-31 session 触发，且 `scheduler` / `hub` 是近期新增（2026-08-28 +），未来仍会加命令。P1 而非 P0 因为它可 workaround（手工加 2 行 / KNOWN_FAILURES 标记），不影响核心 flow 的通过。

## What Changes

- `tests/unit/test_cli_all_subcommands.py`: ALL_SUBCOMMANDS 改动态发现 + 白名单校验（~30 行重构）
- `scripts/pre-commit-hooks/check_cli_subcommands.sh`: 可选 PRE-COMMIT hook（备选方案 B）
- `docs/change-quality-guide.md`: 新增"CLI 子命令白名单"段
- 对照 `_lib/cli/` 30 个 `_cmd.py` 补全白名单（含 hub/scheduler/其余 alias）

## Capabilities

- MUST: `ALL_SUBCOMMANDS` 与 `list_commands()` 永远 self-consistent（同源）
- MUST: 新增 CLI 命令被显式批准（白名单 fail 提示）
- MUST NOT: 破坏现有 `_ROUTES` / `list_commands()` 行为

## Impact

- MUST: pytest unit 时间不显著增加（动态发现 < 1ms）
- MUST: 与 `_lib/cli/__init__.py` 的 discovery API 复用（不重复实现）
- SHOULD: 与 `hub` / `scheduler` 2026-08-31 手工修复兼容（当前 tuple 已含两者，动态化后自动一致）
- MUST NOT: 添加新 subcommand 时静默通过（白名单强制评审）

## Acceptance

- [ ] `ALL_SUBCOMMANDS` 从手写 tuple 改为动态发现（复用 `list_commands()` / `_ROUTES`）
- [ ] 新增 `test_all_subcommands_in_whitelist` 白名单校验 PASS
- [ ] `test_list_commands_returns_canonical_subcommand_set` / `test_routes_keys_match_canonical_subcommand_set` 对当前 30 命令 PASS
- [ ] 模拟新增 `foo_cmd.py` → 白名单 fail 提示显式批准
- [ ] `python3 -m pytest tests/unit/test_cli_all_subcommands.py` 全部 PASS
- [ ] 文档同步更新（新增命令流程 + 白名单说明）