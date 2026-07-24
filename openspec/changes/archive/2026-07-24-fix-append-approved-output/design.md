# Design: fix-append-approved-output

## Context

`state.sh::append_approved` 函数内部 `echo "✅ $name added to approved list"`，外部调用循环也有 `echo "  ✅ $name"`，导致每次批准输出两行重复信息。函数应返回状态码，由调用方决定输出格式。

## Goals / Non-Goals

### Goals

- 移除 `append_approved` 内部的成功 echo，或重定向到 stderr
- 保持函数返回值语义不变（0=成功，1=失败）
- 调用方可自行控制输出格式
- 批量批准时每个提案只占一行输出

### Non-Goals

- 不修改 `list_approved` / `list_improvements` 等其他函数

## Decisions

移除 `append_approved` 内部的 `echo "✅ $name added to approved list"` 行。函数仅负责状态变更 + 返回码，输出格式由调用方决定。

```bash
# Before:
append_approved() {
  ...
  echo "✅ $name added to approved list"  # 移除此行
  return 0
}

# After:
append_approved() {
  ...
  return 0
}
```

备选方案（重定向到 stderr）不采用，因为调用方通常不需要这些信息。

## Implementation

**关键修改文件:**

- `skills/_lib/state.sh` — `append_approved` 函数移除内部 echo
