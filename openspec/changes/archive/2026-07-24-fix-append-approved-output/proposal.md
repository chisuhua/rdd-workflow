# Proposal: fix-append-approved-output

## Why

`state.sh::append_approved` 函数内部 `echo "✅ $name added to approved list"`，外部调用循环也有 `echo "  ✅ $name"`，导致每次批准都输出两行重复信息。

来源: 会话复盘 2026-07-23

## What Changes

- 移除 `append_approved` 内部的成功 echo（函数应返回状态码，由调用方决定输出格式）
- 或者：将内部 echo 改为 `>&2` 输出到 stderr，保持调用方输出干净
- 不修改 `list_approved` / `list_improvements` 等其他函数

## Capabilities

### New Capabilities: fix-append-approved-output

修复 `append_approved` 函数的双重 echo 问题：移除内部成功 echo 或重定向到 stderr。保持函数返回值语义不变（0=成功，1=失败），调用方可自行控制输出格式。

## Impact

**受影响文件:**
- `skills/_lib/state.sh` — `append_approved` 函数

**不受影响:**
- `list_approved` / `list_improvements` 等其他函数
