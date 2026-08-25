# cleanup-pre-existing-debt

## Why

Wave 完成后审计发现 1 项架构债务 + 2 项 rdd-doctor 残留误报:

1. **G1 (架构债务)**: `check_rfc_draft()` 函数定义于 `skills/guide-design/scripts/design_done_gate.py:115`,注册到 `_COMMANDS` dict (line149),但 `check_design_done_gate()` in `skills/guide-design/SKILL.md:319` **从不调用它**。rdd-doctor 正确标记为 orphan gate — false promise,后续维护者会误以为该闸门在生效。

2. **G2 (rdd-doctor 误报)**: `.rddf/state/.mcp-trace.jsonl` 是有效 JSONL(每行独立 JSON object),但 rdd-doctor 的 `state_schema_check.py` 用 `json.load()`(整文件单文档解析)而非 `json.loads(行)`(JSONL 解析),导致误判 "Line 2: invalid JSON: Extra data"。

## What Changes

**In Scope**:

- **删除** `check_rfc_draft()` 函数 + 移除 `_COMMANDS["check-rfc-draft"]` 条目 + 删除关联的 `_is_cross_repo_federation()` 和 `_validate_rfc_draft()` 辅助函数(若无其他调用方)
- **修复** rdd-doctor 的 JSONL 解析 — 改用按行 `json.loads()`
- **不**新增 `check_rfc_draft` 的 wire-up(若该闸门有价值,应作为独立 change 处理 RFC draft 跟踪机制,而不是仓促接线)
- **不**改 `check_hub_pending` / `check_cross_repo_approvals`(由 `fix-orphan-hub-gates-wiring` PR 覆盖)
- **不**碰 `.rddf/state/` 残留文件(`.lock` / `.cross-repo-deps-cache.json` 已由 orchestrator 手动清理)

### 关键场景

### 场景 A:rdd-doctor 巡检通过

**GIVEN** `bash skills/rdd-doctor/scripts/doctor.sh --category orphan-gates`
**WHEN** 执行
**THEN**
- 不再报告 `check_rfc_draft()` orphan
- 不再报告 `.mcp-trace.jsonl` invalid JSON (该文件不在此 change scope,但解析修复使所有 JSONL 文件的验证更健壮)

### 场景 B:CLI 直接调用 `check-rfc-draft` 不再可用

**GIVEN** 运维人员执行 `python3 design_done_gate.py check-rfc-draft`
**WHEN** 运行
**THEN**
- 退出码 2 (usage error)
- stderr: `usage: design_done_gate.py <check-hub-pending|check-cross-repo-approvals>`

**Out of Scope**:

- (no items specified)

## Acceptance

### 功能验收

- [ ] **AC-1**:`check_rfc_draft()` 函数从 `design_done_gate.py` 删除
- [ ] **AC-2**:`_COMMANDS` dict 仅含 `check-hub-pending` + `check-cross-repo-approvals` 两条目
- [ ] **AC-3**:`_is_cross_repo_federation()` / `_validate_rfc_draft()` 辅助函数删除(若无外部调用方)
- [ ] **AC-4**:`skills/rdd-doctor/scripts/checks/state_schema_check.py` 改用按行 JSONL 解析
- [ ] **AC-5**:rdd-doctor CRITICAL 列表从 6 项降至 ≤4 项(剩余 `.mcp-trace.jsonl` Line 2 为误报,修复后归零)
- [ ] **AC-6**:`openspec validate cleanup-pre-existing-debt` → valid

### 测试

- [ ] 1 unit 测试 (orphan-gate 消失)
  - `tests/unit/test_design_done_gate.py` 新增 case 验证 `_COMMANDS` 仅 2 条目
- [ ] 1 regression 测试 (rdd-doctor JSONL 解析)
  - `tests/unit/test_state_schema_check.py` 新增 case 验证 JSONL 文件不被误报

### 不变量

- `check_hub_pending` / `check_cross_repo_approvals` 函数签名不变
- `design_done_gate.py` 模块导出 API 仍为 `main(argv)` → int
- `_COMMANDS` dict 至少含 1 个条目