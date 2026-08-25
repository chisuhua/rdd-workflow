# fix-skill-count-and-table-schema — Design

## Context

Wave 完成后审计发现 2 项 rdd-doctor WARNING 预存债务。本提案清理两者,降低 CI 基线噪音。

**Architectural basis**: ADR-0018 (arch-quality-gate) + ADR-0025 (proposal-suggestions format)

## Goals / Non-Goals

**Goals:**
- 修复 `test_doc_contracts.py` 3 个失败(test counter 逻辑)
- 修复 `proposal-approved.md` schema 漂移(补 `状态` 列)
- 添加 1 个回归测试防止 proposal 表回退

**Non-Goals:**
- 改 INSTALL.md/package.json 声称的 skill 数(它们正确)
- 改 rdd-doctor schema 定义(4 列是正确的)
- 改 `.rddf/state/` 残留文件
- 改其他 doc_contracts 测试(general/spec, ADR index 等)

## Decisions

### 1. Test counter 修复:仅计 sub-skill SKILL.md

**Decision**: `_count_skill_files()` 改为仅返回 `len(sub)`(仅 SKILL.md 数量),inlined comment 说明 INSTALL.md 是 installer 不算 sub-skill。

**Rationale**: INSTALL.md 是全局安装入口,不是 sub-skill;测试意图是验证"声称的 sub-skill 数 == 实际 sub-skill 数",INSTALL.md 不应参与计数。

### 2. Proposal 表 修复:补 `状态` 列,值统一 `已批准`

**Decision**: lines 108-116 9 行已批准未实施条目补 `| 已批准 |` 第 4 列。

**Rationale**: Schema 已定义为 4 列;已批准但未实施的条目状态为 `已批准`(与 `已实施` 区分)。

## Affected Components

| Component | Type | Reason |
|-----------|------|--------|
| `tests/unit/test_doc_contracts.py` | test | Fix `_count_skill_files()` |
| `proposal-approved.md` | docs | Add `状态` column to lines 108-116 |
| `tests/unit/test_proposal_table_schema.py` | test | NEW — regression for table schema |

## Risks / Trade-offs

- **Risk**: 修改 `_count_skill_files()` 可能让"INSTALL.md 真实存在"检查失效
  **Mitigation**: 3 个 test 中的 assert 都断言 sub-skill 数(24),不依赖 INSTALL.md 计数
- **Risk**: 添加 `状态` 列需要决定值(已批准/已实施/待实施?)
  **Mitigation**: 统一用 `已批准`(对应"完成时间"已填但尚未归档的状态)

## Implementation Notes

### 场景 A 验证

```bash
python3 -m pytest tests/unit/test_doc_contracts.py -v
```

Expected: 10/10 pass (7 already + 3 fixed).

### 场景 B 验证

```bash
bash skills/rdd-doctor/scripts/doctor.sh 2>&1 | grep "proposal-table"
```

Expected: no proposal-table findings.

### 场景 C 验证

```bash
grep -c "^| 24 \|^| 全部.*24" skills/INSTALL.md package.json
```

Expected: 24 still claimed (not modified).