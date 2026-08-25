# cleanup-pre-existing-debt — Design

## Context

Wave 完成后审计在 `rdd-doctor` 巡检中发现 1 项真架构债务 + 1 项 rdd-doctor 误报。本提案清理两者,消除后续维护者的歧义。

**Architectural basis**: ADR-0018 (arch-quality-gate) + ADR-0028 (role-model)

## Goals / Non-Goals

**Goals:**
- 删除 orphan `check_rfc_draft()` 函数
- 修复 rdd-doctor JSONL 解析逻辑
- 添加 2 个回归测试防止回退

**Non-Goals:**
- 重新设计 RFC draft 跟踪机制(如需,作为独立 change)
- 触碰 `.rddf/state/` 文件
- 修改 `check_hub_pending` / `check_cross_repo_approvals`(由其他 PR 覆盖)

## Decisions

### 1. 删除策略:删函数 + 删辅助函数 + 删 dict 条目

**Decision**: 完整删除 `check_rfc_draft()` + `_is_cross_repo_federation()` + `_validate_rfc_draft()` + `_COMMANDS["check-rfc-draft"]` 条目。**不**留 shim——orphan gate 的本质就是死代码,留 shim 反而延长 false promise。

**Rationale**: rdd-doctor 标记 orphan 的目的就是提醒清理,留 shim 违反清理初衷。

### 2. JSONL 解析:逐行 `json.loads()` 而非整文件 `json.load()`

**Decision**: `state_schema_check.py` 中 `.jsonl` 文件走 `for line in f: json.loads(line)`,整 `.json` 文件走原 `json.load()`。

**Rationale**: `.jsonl` (JSON Lines) 是 line-delimited JSON 标准 (jsonlines.org),每行独立 parse;整文件 parse 必失败于多行文件。

## Affected Components

| Component | Type | Reason |
|-----------|------|--------|
| `skills/guide-design/scripts/design_done_gate.py` | module | Delete orphan functions |
| `skills/rdd-doctor/scripts/checks/state_schema_check.py` | module | Fix JSONL parsing |
| `tests/unit/test_design_done_gate.py` | test | Add regression |
| `tests/unit/test_state_schema_check.py` | test | Add regression |

## Risks / Trade-offs

- **Risk**: 删 `check_rfc_draft` 后,若有文档提到此功能 → 文档漂移
  **Mitigation**: grep 全文检查 `check_rfc_draft` / `check-rfc-draft` 引用,删除对应文档引用
- **Risk**: JSONL 解析修复可能引入副作用(若某文件不是纯 JSONL,会被漏过)
  **Mitigation**: 测试覆盖空行 / 非 JSON 行 / 多行 JSON 三种边界

## Implementation Notes

### 场景 A 验证

```bash
bash skills/rdd-doctor/scripts/doctor.sh --category orphan-gates,state
```

Expected: CRITICAL 列表从 6 项降至 ≤3 项(仅 `.mcp-trace.jsonl` 仍误报,需后续 JSONL 修复 PR 跟进)。

### 场景 B 验证

```bash
python3 skills/guide-design/scripts/design_done_gate.py check-rfc-draft
echo "exit: $?"  # expect 2
```

### 文件清理检查

```bash
grep -rn "check_rfc_draft\|check-rfc-draft\|rfc_draft" skills/ tests/ docs/ 2>/dev/null
```

Expected: no matches (除 changelog/历史 archive)。