# rdd-workflow v2.1 改进执行计划

> 对应 ADR: [ADR-0014: Add execute-review phase and debt-reflow mechanism](../docs/adr/ADR-0014-review-phase-and-debt-reflow.md)
> 基于: 22 个流程缺陷分析 + 5 个检查项归属判定 + 债务回流需求

## 一、总览

| 改进 | 文件 | 操作 | 优先级 | 预估行数 |
|------|------|------|--------|---------|
| 新增 Phase 2.5 review | `skills/guide-ship.md` | INSERT @ L590 | P0 | +120 |
| 加 `type` 字段 | `docs/proposal-suggestions-format.md` | MODIFY @ L44 | P1 | +3 |
| | `skills/propose.md` | MODIFY @ L301 | P1 | +25 |
| ship_done 新增 gate check | `skills/_lib/gate.py` | MODIFY @ L128 | P1 | +15 |
| iteration.py 加 review status | `skills/_lib/iteration.py` | MODIFY @ L46 | P2 | +3 |
| | `skills/_lib/schemas/iteration_schema.json` | MODIFY | P2 | +2 |
| 集成测试 | `tests/integration/test_review_phase.bats` | CREATE | P2 | +60 |
| **合计** | **7 文件** | | | **~228 行** |

---

## 二、逐项详述

### 改进 1：新增 Phase 2.5 review（P0，~120 行）

**文件**: `skills/guide-ship.md`
**插入点**: 第 590 行（`## Phase 3: archive` 之前）

**原因**: 当前 execute 完成后、archive 前没有审查阶段。execute 中发现的债务（新 TODO、测试回归、未提交清理文件）无回流路径——用户要么丢失这些债务，要么手动跑回 guide-plan 全量重建 deps。

**流程**:

```
execute 完成 (tasks.md 全部 [x])
    ↓
Phase 2.5: review
    ├── 采集债务 (git diff + TODO/FIXME + ctest 回归)
    ├── 展示结果 → 用户交互
    │   ├── 选项 1: 范围內债务 → 追加 tasks.md → 返回 execute
    │   ├── 选项 2: 旁效应债务 → 创建新 change (type=debt) → proposal-suggestions.md
    │   │                     → 检查文件冲突 → 有冲突则 offer re-deps
    │   ├── 选项 3: 架构漂移 → 回注 guide-arch (生成 drift-analysis.md)
    │   ├── 选项 4: 跳过 (默认) → 直接进入 archive
    │   └── 选项 5: 查看详细 diff
    └── 进入 Phase 3: archive
```

**关键设计决策**:
- 旁效应债务的 deps 重新分析由**文件冲突**驱动（`comm -12` 检查新 change 的文件是否与已归档 change 的文件重叠），而非按 change type 判断
- 默认选项是"跳过"——不强制 review，用户按回车即可继续
- 架构漂移只生成 drift-analysis.md，不自动修正 ADR（需要人工判断）

**具体内容**: 见 ADR-0014 §Decision 1 + §Decision 3 的交互流程和 bash 实现。

---

### 改进 2：proposal-suggestions 加 `type` 字段（P1，~28 行）

**文件 1**: `docs/proposal-suggestions-format.md` @ L44 后

新增一行字段表：

```
| `type`  | string | no  | `"functional"` (default), `"debt"`, or `"refactor"`. Reviews and sprint planning filter on this field. |
```

**文件 2**: `skills/propose.md` @ L301 后（Phase 2 分类逻辑）

新增 `infer_type()` 函数 + 在 JSON 构建时追加 `type` 字段：

```bash
infer_type() {
    local source=$1 description=$2 priority=$3
    python3 -c "
s, d, p = '$source', '''$description''', '$priority'
if any(k in (s+d).lower() for k in ['debt','债务','清理','legacy']):
    print('debt')
elif any(k in d.lower() for k in ['重构','refactor']):
    print('refactor')
else:
    print('functional')
"
}
```

**向后兼容**: 所有 consumer 使用 `.get('type', 'functional')` 默认值。无 schema 版本变更。

---

### 改进 3：gate.py ship_done 新增 review check（P1，~15 行）

**文件**: `skills/_lib/gate.py`

**位置**: 在第 128 行 `_DEFAULT_CHECKS["ship_done"]` 数组末尾新增。

```python
Check("review_debt_recorded", _check_review_debt_recorded,
      "execute 后债务未记录", "运行 Phase 2.5 review 或选择跳过", "warning"),
```

**检查函数**: `_check_review_debt_recorded(ctx)` —— 检查 proposal-suggestions.md 中是否有 `type=debt` 条目与新产生的 TODO 标记一一对应。

**级别**: warning（不阻断 archive，因为 debt 可 deferred）。

---

### 改进 4：iteration.py 加 review status（P2，~5 行）

**文件 1**: `skills/_lib/iteration.py` @ L46

```python
_VALID_STATUSES = ("proposed", "in_worktree", "review", "completed", "archived")
```

**文件 2**: `skills/_lib/schemas/iteration_schema.json`

在 status enum 中加 `"review"`。需要 bump schema version 从 v1 到 v2。

---

### 改进 5：集成测试（P2，~60 行）

**文件**: `tests/integration/test_review_phase.bats`（新建）

5 个测试覆盖：
- Phase 2.5 节在 guide-ship.md 中存在
- 菜单有 5 个选项
- proposal-suggestions-format.md 有 `type` 字段
- iteration.py status 包含 "review"
- gate.py 包含 `review_debt_recorded` check

---

## 三、执行顺序

| 天 | 内容 | 文件 |
|----|------|------|
| **Day 1** | Phase 2.5 review (P0) | `skills/guide-ship.md` + 测试 |
| **Day 2** | type 字段 + gate check (P1) | `proposal-suggestions-format.md`, `propose.md`, `gate.py` |
| **Day 3** | status + schema + 测试补全 (P2) | `iteration.py`, schema, bats |

---

## 四、不在此计划中的项

| 不在本计划 | 原因 | 后续 |
|-----------|------|------|
| 架构漂移自动检测 (mend-adr 模式) | 属于 guide-arch 阶段，需独立 ADR | 未来 ADR |
| 全面基线快照 | 属于 CI 工具，非 rdd-workflow 职责 | 外部 |
| debt-count 驱动的 scan-state 推荐分支 | 需先有 debt 数据积累 | v2.2 |
| deps subagent 实现 | 需独立架构决策 | 未来 ADR |
| execute pre-commit 安全快照 | 与 review 独立，可分开发 | 独立 change |