# Filter guide-ship when no active changes — 技术设计

## 设计目标

在 `guide` 入口生成菜单选项时，根据 `FS_ACTIVE_COUNT` 动态决定是否包含 `guide-ship` 选项。当无活跃 change 时，避免用户进入无意义的 `guide-ship` 流程。

## 实现方案

### 方案 A（首选）：在 `all_options` 中条件过滤

在 `workflow_synthesizer.py` 的 `all_options` 生成逻辑中，新增条件判断：

```python
def all_options(state):
    options = []
    # ... existing options ...
    
    # 仅在 FS_ACTIVE_COUNT > 0 时添加 guide-ship
    if state.get("FS_ACTIVE_COUNT", 0) > 0:
        options.append({
            "id": "guide-ship",
            "group": "stages",
            "description": "执行已提交的 change",
            "command": "skill_use(\"guide-ship\")"
        })
    else:
        options.append({
            "id": "guide-ship",
            "group": "disabled",
            "description": "执行已提交的 change (无活跃 change，请先创建 change)",
            "command": None  # 不可选
        })
    # ...
```

### 方案 B（备选）：在 `scan_state()` 决策树中调整

`scan_state()` 的 13-path 决策树中，path 7+ 包含 `guide-ship` 推荐。在 FS_ACTIVE_COUNT == 0 时，将所有 path 中的 `guide-ship` 推荐替换为 `guide-arch` 或 `guide-plan`。

### 选择：方案 A

方案 A 更优雅，因为：
1. 集中式过滤逻辑，所有选项生成统一入口
2. 保持 `guide-ship` 在菜单中可见（作为 disabled），用户知道有这一步但当前不可用
3. 不影响 scan_state() 的决策树逻辑

## 文件变更清单

| 文件 | 操作 | 说明 |
|------|------|------|
| `skills/_lib/workflow_synthesizer.py` | 修改 | `all_options()` 中新增 `FS_ACTIVE_COUNT` 条件过滤 |
| `skills/guide/scan-state.sh` | 修改 | 在 FS_ACTIVE_COUNT == 0 的路径中不推荐 guide-ship |

## 技术约束

- MUST 保持阶段命令按实际可用性动态过滤
- MUST 与其他 `all_options` 过滤逻辑一致
- FS_ACTIVE_COUNT 已在 scan-state.sh 中计算，可从状态中读取