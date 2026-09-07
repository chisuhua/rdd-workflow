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
- **删除 `rddf ac-verify` 友好报错**：`rddf ac-verify` 命令改为发出清晰迁移提示并 exit 4（"removed per ADR-0045; use `rddf rdd-verify`"），不静默失败
- **清理测试文件 deprecation banner**：6 个标记 deprecated 的 ac-verifier 测试文件（`tests/unit/test_ac_verifier*.py`、`tests/integration/test_ac_verifier_*.bats`）删除
- **更新文档**：移除 `ac-verifier` 在 AGENTS.md、README.md、CHANGELOG.md、相关 spec 文档的所有引用

## Capabilities

### New Capabilities

（无新增能力）

### Modified Capabilities

- **`ac-verifier` skill**：完全移除（was deprecated per ADR-0045）。
- **`ac-verify` CLI subcommand**：移除；用户改用 `rddf rdd-verify`（自 ADR-0045 起等价）。
- **`_lib/cli/rdd_verify_cmd.py::_default_runner` 别名**：移除（v2.0 内部已统一使用 `_stage_context_runner`）。

## Impact

- **In Scope**：
  - `skills/ac-verifier/`（全删）
  - `_lib/cli/ac_verify_cmd.py`（删除 + `_lib/cli/__init__.py` 移除 `"ac-verify"` route）
  - `_lib/cli/rdd_verify_cmd.py`（移除 `_default_runner` 别名）
  - `tests/unit/test_ac_verifier*.py`、`tests/integration/test_ac_verifier_*.bats`（删除）
  - `AGENTS.md`、`README.md`、`CHANGELOG.md`（移除 ac-verifier 提及）
- **Out Scope**：
  - 不改 rdd-verifier v2.0 协议本身
  - 不改 SHA cache schema
  - 不改 `_lib/verifier/{cache, classify, protocol}.py` 核心契约
  - 不重写 `rddf rdd-verify`（已经在 v2.0）

## Acceptance Criteria

- [ ] `skills/ac-verifier/` 目录已从 `skills/` 移除
- [ ] `rddf ac-verify --help` exit 4 + 输出迁移提示（"removed per ADR-0045; use `rddf rdd-verify`"）
- [ ] `_lib/cli/ac_verify_cmd.py` 不再存在
- [ ] `_lib/cli/__init__.py` 不再有 `"ac-verify"` route
- [ ] `_lib/cli/rdd_verify_cmd.py` 不再有 `_default_runner = _stage_context_runner` 别名
- [ ] 6 个 ac-verifier 测试文件已删除
- [ ] `AGENTS.md`、`README.md`、`CHANGELOG.md` 不再有 ac-verifier 引用
- [ ] `./test.sh --full --regression` 0 新增失败
- [ ] `openspec validate remove-ac-verifier-completely --strict` 通过

## Reference

- 上游 change：`openspec/changes/archive/2026-09-07-inline-ac-verifier-into-rdd-verifier/`（ADR-0045）
- 上游 change：`openspec/changes/verifier-v2-hardening/`（v2.0 closure + scheduler）
- Oracle review session：`ses_f8610cbf6ffeVLcEjlRw3s2COt`