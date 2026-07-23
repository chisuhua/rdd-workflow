# Design: fix-mark-approved-completed

## Context

`skills/_lib/state.sh` 的 `mark_approved_completed` 函数在移动条目到 `## 已实施` 表格时，Python 逻辑产生了重复的 `| 提案 | 优先级 | 实施时间 |` 表头行。函数缺少幂等性检查，已实施条目再次调用会重复插入。

## Goals / Non-Goals

### Goals

- 修复 `content.replace` 逻辑，确保新行插入在 `## 已实施` 表头下方而非重复表头
- 增加幂等性检查：条目已在 `## 已实施` 表格中时直接返回成功
- 使用 Python 标准库 `re` 模块，不引入新依赖
- 保持与 `append_approved` / `list_approved` 的调用约定一致
- 测试覆盖：正常路径 + 重复调用幂等 + 已实施条目跳过

### Non-Goals

- 不修改 `append_approved` 函数
- 不修改 proposal-approved.md 格式

## Decisions

使用 `re` 模块定位 `## 已实施` 表头行，在其下方插入新行，而非使用 `content.replace` 替换整个表头块：

```python
# 定位 ## 已实施 表头行
header_pattern = r'(## 已实施\s*\n\| 提案 \| 优先级 \| 实施时间 \|\s*\n\|[-\s|]+\|\s*\n)'
match = re.search(header_pattern, content)
if match:
    # 在表头 + 分隔行之后插入新行
    insert_pos = match.end()
    content = content[:insert_pos] + new_row + '\n' + content[insert_pos:]
```

幂等性检查：在插入前先搜索 `## 已实施` 表格中是否已包含该提案名，若存在则直接返回 0。

## Implementation

**关键修改文件:**

- `skills/_lib/state.sh` — `mark_approved_completed` 函数
  - 修复 `content.replace` 为 `re` 模式匹配插入
  - 增加幂等性检查（搜索已实施表格中是否已有该条目）
- `tests/unit/test_mark_approved_completed.py` — 新增 3 个单元测试（正常路径 + 幂等 + 跳过）
