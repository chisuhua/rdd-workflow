# fix-plan-intake-stale-pre-created-changes — Design

## 目标

让 `plan_intake.sh` 第一屏真实反映"哪些 change 待处理"，不再因「`## 已实施` 分区被算进 pending」和「`changes_pre_created` 永不过期」误导 AI agent 决策。

## 实现方案

### 改动 1: `run_plan_intake` 修正 `PENDING_PROPOSALS`

**位置**：`skills/guide-plan/scripts/plan_intake.sh` 第 200-204 行

**当前代码**：
```bash
PENDING_PROPOSALS=$(grep -c '| \[' "$PROJECT_ROOT/proposal-approved.md" 2>/dev/null || echo 0)
if [ "$PENDING_PROPOSALS" -gt 0 ] && [ "$ACTIVE_CHANGES" -eq 0 ]; then
    echo "⚠️  proposal-approved.md 中有 $PENDING_PROPOSALS 个已批准提案但无活跃 change（可能需运行 propose）"
fi
```

**改为**：用 Python 一次性计算 `pending_proposals`（排除已实施 + 排除已创建/已归档），输出更精准的状态行。

```python
# 在 proposal-approved.md 中:
#   - 取 ## 已实施 之前的章节（已批准提案区）
#   - 对每行抽取 name
#   - 排除 openspec/changes/<name>/ 已存在的
#   - 排除 openspec/changes/archive/*-<name> 已存在的
#   - 返回剩余 name 列表
```

输出格式改为：
```
📋 待创建 proposal: N (已排除 M 个已归档 + K 个已批准待设计)
```

### 改动 2: `check_design_handoff` 分类展示 `changes_pre_created`

**位置**：`plan_intake.sh` 第 134-146 行 + 149-153 行

**当前代码**：原样读入 `CHANGES_PRE_CREATED`，统一报告 "K 个预建 changes"。

**改为**：读入后用 Python 做一次性分类：
- `pending`: 名字在数组且 `openspec/changes/<name>` 不存在且 `openspec/changes/archive/*-<name>` 不存在
- `active`: 名字在数组且 `openspec/changes/<name>` 存在
- `archived`: 名字在数组且 `openspec/changes/archive/*-<name>` 存在

输出新格式：
```
✅ design-done handoff 已验证 (v2 schema, 19 个预建 changes: 0 待处理, 19 已归档)
```

内部数组 `CHANGES_PRE_CREATED` 保留全部 19 个名字（不删，审计 + 下游 `is_design_pre_created` helper 兼容）。

### 改动 3: 新增 `is_design_pre_created_pending` helper

**位置**：`plan_intake.sh`（`is_design_pre_created` 旁边新增）

```bash
is_design_pre_created_pending() {
  local name="$1"
  is_design_pre_created "$name" || return 1
  local pr="$PROJECT_ROOT"
  [ -d "$pr/openspec/changes/$name" ] && return 1
  # Check archive (glob for date prefix)
  compgen -G "$pr/openspec/changes/archive/*-$name" >/dev/null && return 1
  return 0
}
```

`is_design_pre_created` 既有 helper 保持不变（向后兼容）。

### 改动 4: 导出 env vars 供下游展示层

```bash
export CHANGES_PENDING_COUNT="$pending_count"
export CHANGES_ACTIVE_COUNT="$active_count"
export CHANGES_ARCHIVED_COUNT="$archived_count"
```

guide-plan SKILL.md Phase 2 的展示层（`已批准提案列表`）可直接消费。

## 文件改动清单

| 文件 | 类型 | 说明 |
|------|------|------|
| `skills/guide-plan/scripts/plan_intake.sh` | 修改 | 4 处改动（PENDING 计数 + check_design_handoff 分类 + 新 helper + env vars） |
| `tests/integration/test_plan_intake_archived_filtering.bats` | 新增 | 4 个 bats 测试 |
| `tests/integration/test_plan_intake_design_pre_created.bats` | 修改 | 扩展 2 个测试 |
| `skills/guide-plan/SKILL.md` | 修改 | Phase 1 段补充归档过滤说明 |
| `docs/adr/ADR-0036-design-handoff-runtime-filter.md` | 新增 | 设计选择记录 |

## 兼容性矩阵

| 场景 | 行为 |
|------|------|
| v1 schema handoff（无 `changes_pre_created`） | 行为不变（K=0 → 旧格式输出） |
| v2 + 空 `changes_pre_created: []` | 行为不变（K=0 → 旧格式输出） |
| `SKIP_DESIGN_HANDOFF=yes` | 跳过新逻辑，行为不变 |
| v2 + 部分预建已归档 | 新格式输出（K 待处理 + M 已归档） |
| v2 + 全部预建已归档 | 新格式输出（0 待处理 + K 已归档） |

## 测试策略

- **单元**：bash bats 测新 helper + plan_intake 分类逻辑（4 个新增 + 2 个扩展）
- **端到端**：本仓库实际跑 `run_plan_intake` 验证误导警告消失
- **回归**：`./test.sh --quick` 验证既有测试全绿
