# Fix plan-done gate zero stale count — 技术设计

## 设计目标

修复 `plan_done_gate.sh` Gate 0 的计数数据源，使其从文件系统直接读取（与 Gate 1 一致），消除 `iteration.json` stale 数据导致的错误计数。

## 根因分析

`plan_done_gate.sh` 第 69-79 行使用 Python 调用 `iteration.list_ready_for_ship()` 从 `.rddf/state/iteration.json` 读取计数：

```python
from skills._lib import iteration as it
d = it.load(os.environ.get("PY_PROJECT_ROOT", "."))
ready = it.list_ready_for_ship(d)
print(len(ready))
```

`iteration.json` 是派生视图，由多个 hook 写入。archive 后，归档的 change 条目**未被清理**，导致 `list_ready_for_ship()` 返回过时数据。例如：

- 实际活跃 change：1 个
- `iteration.json` 中 proposed 状态条目：5 个（含 4 个已归档）
- Gate 0 输出：`ready-for-ship: 5` → ✅ 错误通过
- 用户困惑：为什么 5 个 ready-for-ship 但只有 1 个 change？

Gate 1（第 91 行）直接读文件系统，始终返回准确计数：

```bash
CHANGE_COUNT=$(ls -d "$PROJECT_ROOT"/openspec/changes/*/ 2>/dev/null | grep -v archive/ | wc -l)
```

## 修复策略

### 方案 A（推荐）：Gate 0 改用文件系统扫描

将 Gate 0 的计数改为与 Gate 1 相同的文件系统扫描方式，替换 Python 调用：

```bash
# 修复前（Python 调用 iteration.json）
PROPOSED_COUNT=$(PY_PROJECT_ROOT="$PROJECT_ROOT" python3 <<'PYEOF' ...)

# 修复后（文件系统扫描，与 Gate 1 一致）
PROPOSED_COUNT=$(ls -d "$PROJECT_ROOT"/openspec/changes/*/ 2>/dev/null | grep -v archive/ | wc -l)
```

**优点**：
- 直接消除 stale 数据源，不依赖其他模块修复
- 与 Gate 1 完全一致，降低维护成本
- 无需修改 `iteration.json` 清理逻辑
- 不会破坏 `iteration.list_ready_for_ship()` 的其他 consumer

### 方案 B（备选）：合并 Gate 0 到 Gate 1

移除 Gate 0 独立计数，只保留 Gate 1。因为 Gate 0 和 Gate 1 的语义高度重叠（"至少 1 个 ready-for-ship change" ≈ "至少 1 个 active change"）。

**优点**：更简洁
**缺点**：改变了 Gate 0 的 failed 提示信息；用户习惯 "ready-for-ship" 特定提示

### 选择：方案 A

文件系统扫描的改动最小，保留 Gate 0 独立提示信息，且不需要修改现有门控流程文档。

## 修改文件清单

| 文件 | 修改内容 |
|------|---------|
| `skills/guide-plan/scripts/plan_done_gate.sh` | L69-L79: 替换 Python 调用为 `ls ... \| grep -v archive/ \| wc -l` |

## 受影响测试

| 测试文件 | 影响 | 操作 |
|---------|------|------|
| `tests/integration/test_plan_done_gate_extraction.bats` | 现有 Gate 0 测试需调整预期 | 验证新计数仍正确 |
| 新增 | `tests/integration/test_plan_done_gate_zero_stale_count.bats` | 新测试：归档后计数正确 |

## 回归风险

### 风险 1：Gate 0 和 Gate 1 计数等价 ≠ 完全相同

`iteration.list_ready_for_ship()` 不止计数，还过滤掉了有明显 blocker 的 change。文件系统扫描只计数所有非 archive 目录。

**缓解**：在 plan-done 阶段，blocker 分析已在 deps 阶段完成。如果 deps 分析发现 blocker，应在 plan 阶段处理而非 gate 阶段。因此 Gate 0 只做简单计数是合理的。Gate 0 的语义从 "ready-for-ship（proposed + 无 blocker）" 变为 "活跃 change 数量"，与 Gate 1 一致。

### 风险 2：`iteration.list_ready_for_ship()` 的其他 consumer 被影响

`list_ready_for_ship()` 函数本身不会被删除，其他 consumer 不受影响。

### 风险 3：SPEC_WORKFLOW_* 环境变量覆盖

Gate 1 已使用 `$PROJECT_ROOT` 路径，文件系统扫描会正确识别自定义路径。

## 验收标准

1. 归档所有 change 后，Gate 0 计数降为 0
2. 1 个活跃 change 时，Gate 0 计数为 1
3. 现有 plan_done_gate 测试全部通过
4. 新 bats 测试验证归档后计数正确性