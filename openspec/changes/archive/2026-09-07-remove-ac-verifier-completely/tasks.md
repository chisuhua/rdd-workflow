# remove-ac-verifier-completely — Tasks

## Phase 0 — Setup
- [x] T01: 建 branch `openspec/remove-ac-verifier-completely` (master base)
- [x] T02: 写 design.md (实现策略 + impact + acceptance 11 条)
- [x] T03: 写 specs/remove-ac-verifier-completely/spec.md (10 Requirement + Scenario)
- [x] T04: 写 tasks.md (本文)
- [x] T05: `openspec validate remove-ac-verifier-completely --strict` 绿
- [x] T06: commit artifacts (`feat(remove-ac-verifier-completely): propose`)

## Phase 1 — `rddf ac-verify` 友好报错
- [ ] T07: 重写 `_lib/cli/ac_verify_cmd.py` 为 friendly-error 实现（exit 4 + stderr migration hint）
- [ ] T08: 单测：`rddf ac-verify --help` exit 4 + 包含 "removed per ADR-0045" 与 "rddf rdd-verify" 字样
- [ ] T09: `tests/integration/test_ac_verify_removed.bats` (新) — 验证 T08

## Phase 2 — Route / Alias 清理
- [ ] T10: `_lib/cli/__init__.py` 移除 `"ac-verify"` route 注册
- [ ] T11: `_lib/cli/rdd_verify_cmd.py` 移除 `_default_runner = _stage_context_runner` 别名
- [ ] T12: `_lib/cli/rdd_verify_cmd.py` 检查所有 `_default_runner` 引用已迁移到 `_stage_context_runner` 或 `_default_run` (无残留)

## Phase 3 — 删除 ac-verifier 实现
- [ ] T13: `rm -rf skills/ac-verifier/` (含 17 .py + 3 .md + pycache)
- [ ] T14: `git rm skills/ac-verifier/` 确认
- [ ] T15: `git grep -n "from skills.ac_verifier\|from skills.ac-verifier" -- "*.py"` 无残留
- [ ] T16: `git grep -n "import skills.ac_verifier\|import skills.ac-verifier" -- "*.py"` 无残留

## Phase 4 — 删除 ac-verifier 测试
- [ ] T17: `rm tests/unit/test_ac_verifier.py`
- [ ] T18: `rm tests/unit/test_ac_verifier_providers.py`
- [ ] T19: `rm tests/integration/test_ac_verifier_e2e.bats`
- [ ] T20: `rm tests/integration/test_ac_verifier_http_live.bats`
- [ ] T21: `rm tests/integration/test_ac_verifier_skill.bats`
- [ ] T22: 保留 `tests/integration/test_ac_verifier_archive_gate.bats` (已迁移到 v2 schema) — 但修改内部 ac-verifier 字面引用为 rdd-verifier
- [ ] T23: 保留 `tests/integration/test_rdd_verifier_archive_compat.bats` (v2.0 closure 已修)

## Phase 5 — 文档清理
- [ ] T24: `AGENTS.md` 移除所有 `ac-verifier` 行（含 ARCHITECTURE / Common Pitfalls / install.sh ref）
- [ ] T25: `README.md` 移除 `ac-verifier/SKILL.md` 行 + 27 个子技能计数改 26
- [ ] T26: `CHANGELOG.md` `[Unreleased]` 加 remove-ac-verifier-completely entry
- [ ] T27: `USAGE.md`（如存在 ac-verifier 提及）移除
- [ ] T28: `install.sh` 移除 ac-verifier 在 symlink 列表

## Phase 6 — ADR 历史保留
- [ ] T29: `docs/adr/ADR-0045-inline-ac-verifier-into-rdd-verifier.md` 顶部加 "Status: Removed (2026-XX-XX)" + removal note
- [ ] T30: `docs/adr/ADR-0034-rdd-verifier-verify-phase-architecture.md` 添加 1 行 note
- [ ] T31: `docs/adr/ADR-0035-verifier-archive-gate-boundary.md` 添加 1 行 note

## Phase 7 — 回归验证
- [ ] T32: `./test.sh --full --regression` → 0 bats 新增失败
- [ ] T33: `git grep "ac-verifier" -- ':!docs/adr/ADR-0045*' ':!docs/adr/ADR-0034*' ':!docs/adr/ADR-0035*' ':!openspec/changes/archive/*' ':!CHANGELOG.md'` 仅命中 archive-history 段
- [ ] T34: `git grep "ac_verifier" -- '_lib/ skills/ tests/ install.sh README.md AGENTS.md USAGE.md'` 无命中（除 archive-history）

## Phase 8 — Archive
- [ ] T35: `git add -A && git commit -m "feat(remove-ac-verifier-completely): delete ac-verifier skill + ac-verify CLI"`

## Phase 10 — Final Regression + Archive
- [ ] T36: 跑 `./test.sh --full --regression` 验证 0 新增失败
- [ ] T37: `openspec archive remove-ac-verifier-completely --yes` → 应用 spec → 自动 commit
- [ ] T38: `git checkout master && git merge --no-ff openspec/remove-ac-verifier-completely`
- [ ] T39: `git branch -d openspec/remove-ac-verifier-completely`
- [ ] T40: 验证 branch cleanup + 最终 git log