## Why

`ac-verifier` 子技能在 `inline-ac-verifier-into-rdd-verifier`（ADR-0045，已归档于 `openspec/changes/archive/2026-09-07-inline-ac-verifier-into-rdd-verifier/`）中被标记为 deprecated：

- `skills/ac-verifier/SKILL.md` 顶部带 ⚠️ DEPRECATED 横幅
- `user-invocable: false`
- `metadata.deprecated.reason` / `removal_target: "next minor release after 2.0"`
- `ac-verifier/scripts/{ac_verifier.sh, ac_verifier.py, llm_providers/*, ac_verifier_mocks.py}` 加 deprecation 头部注释
- `_lib/cli/ac_verify_cmd.py` 改为 thin shim
- `_lib/cli/__init__.py` 的 `"ac-verify"` route 加 deprecation 注释
- `_lib/archive.sh::archive_gate_check` 移除 ac-verifier subprocess fallback

`verifier-v2-hardening`（独立 change）做了 v2.0 闭环修复并显式调度："把 ac-verifier 移除排入下个 minor 的独立 change"（proposal.md Phase 7 / oracle Q3）。本 change 即该执行动作。

## What Changes

- **删除整套 ac-verifier 实现**：`skills/ac-verifier/` 全部（SKILL.md、scripts/{ac_verifier.sh, ac_verifier.py}、llm_providers/{base, openai, anthropic, ollama, minimax}.py、ac_verifier_mocks.py）
- **删除 ac-verify CLI route**：`_lib/cli/ac_verify_cmd.py` 与 `_lib/cli/__init__.py` 中的 `"ac-verify"` 路由
- **删除 `_default_runner` 别名**：`_lib/cli/rdd_verify_cmd.py` 中 `_default_runner = _stage_context_runner` 别名（shim 期间保留用于测试）
- **`rddf ac-verify` 友好报错**：用户调用时输出清晰迁移提示并 exit 4（"removed per ADR-0045; use `rddf rdd-verify`"），不静默失败
- **清理 6 个标记 deprecated 的 ac-verifier 测试文件**（`tests/unit/test_ac_verifier*.py`、`tests/integration/test_ac_verifier_*.bats` 中以 `ac-verifier` 为测试对象的）
  - 保留：`test_ac_verdict_cache_schema.py`（rdd-verifier cache schema，已迁移）
  - 保留：`test_rdd_verifier_*.{py,bats}`（rdd-verifier 测试）
  - 保留：`test_ac_verifier_archive_gate.bats` / `test_rdd_verifier_archive_compat.bats`（archive gate 集成测试，验证 rdd-verifier cache 路径）
- **更新文档**：移除 `ac-verifier` 在 AGENTS.md、README.md、CHANGELOG.md、USAGE.md、所有 plan/superpowers spec 的引用
- **保留历史**：ADR-0045、ADR-0034、ADR-0035 仅添加 "as of remove-ac-verifier-completely (2026-XX-XX) this skill has been removed" 1 行 note，不删正文

## Capabilities

### New Capabilities

（无新增能力）

### Modified Capabilities

- **`ac-verifier` skill**：完全移除（was deprecated per ADR-0045）。
- **`ac-verify` CLI subcommand**：移除实现；保留为友好报错 shim（exit 4 + migration hint），用户改用 `rddf rdd-verify`（自 ADR-0045 起等价）。
- **`_lib/cli/rdd_verify_cmd.py::_default_runner` 别名**：移除（v2.0 内部已统一使用 `_stage_context_runner`，且只在 deprecation shim 期间被引用）。

## Impact

- **In Scope**：
  - `skills/ac-verifier/`（全删，17 .py + 3 .md + pycache）
  - `_lib/cli/ac_verify_cmd.py`（替换为友好报错；不删除以保留 `rddf ac-verify` 命令路径）
  - `_lib/cli/__init__.py`（移除 `"ac-verify"` route 注册）
  - `_lib/cli/rdd_verify_cmd.py`（移除 `_default_runner` 别名）
  - `tests/unit/test_ac_verifier.py`、`tests/unit/test_ac_verifier_providers.py`（删除）
  - `tests/integration/test_ac_verifier_e2e.bats`、`tests/integration/test_ac_verifier_http_live.bats`、`tests/integration/test_ac_verifier_skill.bats`（删除）
  - `tests/integration/test_ac_verifier_archive_gate.bats`（保留但修改 ac-verifier 引用为 rdd-verifier，因为 archive gate 已迁移）
  - `tests/integration/test_rdd_verifier_archive_compat.bats`（保留，已在 verifier-v2-hardening 中迁移到 v2 schema）
  - `AGENTS.md`、`README.md`、`CHANGELOG.md`、`USAGE.md`（移除 ac-verifier 提及）
  - `install.sh`（移除 ac-verifier 在 symlink 列表）
  - `docs/adr/ADR-0045-inline-ac-verifier-into-rdd-verifier.md`（添加 removal status line）
  - `docs/adr/ADR-0034-rdd-verifier-verify-phase-architecture.md`（添加 removal status line）
  - `docs/adr/ADR-0035-verifier-archive-gate-boundary.md`（添加 removal status line）
- **Out Scope**：
  - 不改 rdd-verifier v2.0 协议本身
  - 不改 SHA cache schema（v2 已在 verifier-v2-hardening 中实装）
  - 不重写 `rddf rdd-verify`（已经在 v2.0）
  - 不删除 ADR（历史记录）
  - 不改 rdd-builder / rdd-arch / rdd-planner / rdd-verifier 主流程

## Acceptance Criteria

- [ ] `skills/ac-verifier/` 目录已从 `skills/` 移除
- [ ] `rddf ac-verify --help` exit 4 + 输出迁移提示（"removed per ADR-0045; use `rddf rdd-verify`"）
- [ ] `_lib/cli/ac_verify_cmd.py` 改为友好报错实现（不删文件，因为 `rddf ac-verify` 命令路径仍需存在以引导用户）
- [ ] `_lib/cli/__init__.py` 不再有 `"ac-verify"` route 注册（route 表移除）
- [ ] `_lib/cli/rdd_verify_cmd.py` 不再有 `_default_runner = _stage_context_runner` 别名
- [ ] 5 个 ac-verifier 测试文件已删除（`test_ac_verifier.py` / `test_ac_verifier_providers.py` / `test_ac_verifier_e2e.bats` / `test_ac_verifier_http_live.bats` / `test_ac_verifier_skill.bats`）
- [ ] `AGENTS.md`、`README.md`、`CHANGELOG.md`、`USAGE.md`、`install.sh` 不再有 ac-verifier 引用
- [ ] 3 个 ADR 文件（0045/0034/0035）添加 1 行 removal status note
- [ ] `openspec validate remove-ac-verifier-completely --strict` 通过
- [ ] `./test.sh --full --regression` 0 bats 新增失败（pytest 11 unit + 1 integration collection error 已知预先存在）
- [ ] `git grep ac-verifier skills/ _lib/ docs/adr/ tests/ install.sh` 在排除历史 ADR + archive 后无命中

## Reference

- 上游 change：`openspec/changes/archive/2026-09-07-inline-ac-verifier-into-rdd-verifier/`（ADR-0045）
- 上游 change：`openspec/changes/archive/2026-09-07-verifier-v2-hardening/`（v2.0 closure + scheduler）
- Oracle review session：`ses_f8610cbf6ffeVLcEjlRw3s2COt`
- 移除调度：`openspec/changes/verifier-v2-hardening/proposal.md` Phase 7 / oracle Q3